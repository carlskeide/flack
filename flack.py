# coding=utf-8
import logging
import re
import time
import json

from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor

from requests import post
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

__all__ = ["Flack", "Attachment", "PrivateResponse", "IndirectResponse", "SlackTokenError"]

DEFAULT_OAUTH_SCOPE = "commands,users:read,channels:read,chat:write:bot"
OAUTH_CREDENTIALS = namedtuple("oauth_credentials", ("team_id", "access_token", "scope"))

SLACK_TRIGGER = namedtuple("trigger", ("callback", "user"))

CALLER = namedtuple("caller", ("id", "name", "team"))
CHANNEL = namedtuple("channel", ("id", "name", "team"))

PrivateResponse = namedtuple("PrivateResponse", ("feedback"))
IndirectResponse = namedtuple("IndirectResponse", ("feedback", "indirect"))

thread_executor = ThreadPoolExecutor(1)


def _send_message(self, url, message):
    logger.debug("Attempting to send message to: {}\nContents: {}".format(url, message))

    time.sleep(1)  # This should prevent out-of-order issues, which slack really doesn't like
    response = post(url, json=message)

    if response.status_code == 404:
        logger.error("Slack url has expired, aborting. response was: {}".format(response.text))
        return False

    elif not response.status_code == 200:
        logger.warn("Slack responded with a non-200 status, will retry.")
        raise self.retry()

    return True


class SlackTokenError(Exception):
    pass


class Attachment(object):
    keys = {
        "fallback",
        "color",
        "pretext",
        "author_name",
        "author_link",
        "author_icon",
        "title",
        "title_link",
        "text",
        "fields",
        "image_url",
        "thumb_url",
        "callback_id",
        "actions"
    }

    def __init__(self, **kwargs):
        self._struct = {k: v for k, v in kwargs.items() if k in self.keys}

    @property
    def as_dict(self):
        return self._struct


class Action(Attachment):
    keys = {
        "name",
        "text",
        "type",
        "style",
        "value",
        "confirm"
    }


class Flack(object):
    triggers = {}
    commands = {}
    actions = {}

    oauth_config = None
    oauth_callback = None

    def __init__(self, flask_app, token, url_prefix='/flack', default_name="flack"):
        self.token = token
        self.default_name = default_name

        blueprint = Blueprint('slack_flask', __name__)

        blueprint.add_url_rule("/",
                               methods=['GET'],
                               view_func=self._dispath_index)
        blueprint.add_url_rule("/oauth",
                               methods=['GET', 'POST'],
                               view_func=self._dispath_oauth)

        blueprint.add_url_rule("/webhook",
                               methods=['POST'],
                               view_func=self._dispath_webhook)
        blueprint.add_url_rule("/command",
                               methods=['POST'],
                               view_func=self._dispath_command)
        blueprint.add_url_rule("/action",
                               methods=['POST'],
                               view_func=self._dispath_action)

        flask_app.register_blueprint(blueprint, url_prefix)

    def _indirect_response(self, message, url):
        indirect_response = {
            "text": "",
            "attachments": [],
            "response_type": "in_channel"
        }

        _, indirect = message

        if isinstance(indirect, Attachment):
            indirect_response["attachments"].append(indirect.as_dict)

        else:
            indirect_response["text"] = indirect

        logger.debug("Generated indirect response: {!r}".format(
            indirect_response))

        thread_executor.submit(_send_message, url, indirect_response)

    def _response(self, message, response_url=None, user=None,
                  private=False, replace=False):
        response = {
            "username": user or self.default_name,
            "text": "",
            "attachments": [],
            "response_type": "ephemeral" if private else "in_channel",
            "replace_original": replace
        }

        if message is None:
            # No feedback
            return ""

        elif isinstance(message, Attachment):
            response["attachments"].append(message.as_dict)

        elif isinstance(message, IndirectResponse):
            self._indirect_response(message, response_url)

            if not message.feedback:
                # This suppresses any feedback.
                return ""

            elif message.feedback is True:
                # This echoes the users input to the channel
                return jsonify({"response_type": "in_channel"})

            else:
                response["text"] = message.feedback
                response["response_type"] = "ephemeral"

        elif isinstance(message, PrivateResponse):
            response["text"] = message.feedback
            response["response_type"] = "ephemeral"

        else:
            response["text"] = message

        logger.debug("Generated response: {!r}".format(response))
        return jsonify(response)

    def _parse_webhook_req(self):
        data = request.form.to_dict()

        self._validate_request(data)
        if not data["trigger_word"]:
            raise AttributeError("No trigger word supplied")

        prefix = len(data["trigger_word"])
        data["text"] = data["text"][prefix:].strip()

        return data

    def _parse_command_req(self):
        data = request.form.to_dict()

        self._validate_request(data)
        if not data["command"]:
            raise AttributeError("No trigger word supplied")

        return data

    def _parse_action_req(self):
        data = json.loads(request.form["payload"])

        self._validate_request(data)
        if not len(data["actions"]):
            raise AttributeError("No action supplied")

        return data

    def _validate_request(self, data):
        if data.get("token") != self.token:
            raise SlackTokenError("Invalid token: {}".format(data.get("token")))

    def _dispath_index(self):
        if not self.oauth_config:
            return ""

        return render_template("index.tpl", **oauth_config)

    def _dispath_pauth(self):
        if not self.oauth_config:
            return ""

        code = request.args["code"]
        logger.info(u"OAuth request called with code: {!r}".format(code))

        try:
            oauth_request = {
                "code": code,
                "client_id": self.oauth_config["client_id"],
                "client_secret": self.oauth_config["client_secret"]
            }

            logger.debug(u"Requesting OAuth Credentials: {!r}".format(oauth_request))
            response = post("https://slack.com/api/oauth.access",
                            data=oauth_request)

            logger.debug(u"Slack response: {!r}".format(response.text))

        except Exception:
            return u"Sorry, something went wrong."

        if not response.ok:
            return u"Slack rejected the request."

        oauth_response = response.json()
        logger.info(u"Received new OAuth credentials: {!r}".format(oauth_response))

        credentials = OAUTH_CREDENTIALS(
            team_id=oauth_response["team_id"],
            access_token=oauth_response["access_token"],
            scope=oauth_response["scope"]
        )

        self.oauth_callback(credentials)

    def _dispath_webhook(self):
        try:
            req = self._parse_webhook_req()

            try:
                callback, user = self.triggers[req["trigger_word"]]

            except KeyError as e:
                raise AttributeError("Unregistered trigger: {}".format(e))

            logger.info("Running trigger: '{}' with: '{}'".format(
                req["trigger_word"], req["text"]))

            req_user = CALLER(req["user_id"], req["user_name"], req["team_id"])
            response = callback(req["text"], user=req_user)
            return self._response(response, user=user)

        except SlackTokenError as e:
            # No response if the caller isn't valid.
            logger.exception("Invalid Token")
            return ""

        except Exception as e:
            logger.error("Caught: {!r}, returning failure.".format(e))

            exception_msg = re.sub(r"[\<\>]", "", e)
            return self._response(exception_msg, private=True)

    def _dispath_command(self):
        try:
            req = self._parse_command_req()

            try:
                callback = self.commands[req["command"]]

            except KeyError as e:
                raise AttributeError("Unregistered command: {}".format(e))

            logger.info("Running command: '{}' with: '{}'".format(
                req["command"], req["text"]))

            req_user = CALLER(req["user_id"], req["user_name"], req["team_id"])
            req_channel = CHANNEL(req["channel_id"], req["channel_name"], req["team_id"])

            response = callback(req["text"],
                                user=req_user,
                                channel=req_channel)

            return self._response(response, response_url=req["response_url"])

        except SlackTokenError as e:
            # No response if the caller isn't valid.
            logger.exception("Invalid Token")
            return ""

        except Exception as e:
            logger.error("Caught: {!r}, returning failure.".format(e))

            exception_msg = re.sub(r"[\<\>]", "", e)
            return self._response(exception_msg, private=True)

    def _dispath_action(self):
        try:
            req = self._parse_action_req()

            try:
                action = req["actions"][0]  # Slack will only send one action per request.
                callback = self.actions[action["name"]]

            except KeyError as e:
                raise AttributeError("Unregistered action: {}".format(e))

            logger.info("Running action, data: {!r}".format(req))

            user = req["user"]
            channel = req["channel"]
            team = req["team"]
            ts = req["message_ts"]

            req_user = CALLER(user["id"], user["name"], team["id"])
            req_channel = CHANNEL(channel["id"], channel["name"], team["id"])

            response = callback(action["value"],
                                instance=req["callback_id"],
                                user=req_user,
                                channel=req_channel,
                                ts=ts)

            return self._response(response, response_url=req["response_url"])

        except SlackTokenError as e:
            # No response if the caller isn't valid.
            logger.exception("Invalid Token")
            return ""

        except Exception as e:
            logger.error("Caught: {!r}, returning failure.".format(e))

            exception_msg = re.sub(r"[\<\>]", "", e)
            return self._response(exception_msg, private=True, replace=False)

    def oauth(self, name, client_id, client_secret, scope=None):
        self.oauth_config = {
            "app_title": name,
            "client_id":client_id,
            "client_secret":client_secret,
            "auth_scope": scope or DEFAULT_OAUTH_SCOPE
        }

        def decorator(fn):
            logger.debug("Register oauth: {}".format(name))
            self.oauth_callback = fn
            return fn

        return decorator

    def trigger(self, trigger_word, **kwargs):
        if not trigger_word:
            raise AttributeError("invalid invocation")

        kwargs.setdefauult("as_user", self.default_name)

        def decorator(fn):
            logger.debug("Register trigger: {}".format(trigger_word))

            self.triggers[trigger_word] = SLACK_TRIGGER(
                callback=fn,
                user=kwargs["as_user"])

            return fn

        return decorator

    def command(self, name):
        if not name:
            raise AttributeError("invalid invocation")

        def decorator(fn):
            logger.debug("Register command: {}".format(name))
            self.commands[name] = fn
            return fn

        return decorator

    def action(self, name):
        if not name:
            raise AttributeError("invalid invocation")

        def decorator(fn):
            logger.debug("Register action: {}".format(name))
            self.actions[name] = fn
            return fn

        return decorator
