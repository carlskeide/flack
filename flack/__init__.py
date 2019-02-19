# coding=utf-8
import logging
import re
import time
import json
from functools import wraps
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor

from requests import post
from flask import Blueprint, request, jsonify

from .message import Attachment, PrivateResponse, IndirectResponse
from .exceptions import SlackTokenError

__all__ = ["Flack", ]

logger = logging.getLogger(__name__)

SLACK_TRIGGER = namedtuple("trigger", ("callback", "user"))

CALLER = namedtuple("caller", ("id", "name", "team"))
CHANNEL = namedtuple("channel", ("id", "name", "team"))

thread_executor = ThreadPoolExecutor(1)


def _send_message(self, url, message):
    logger.debug("Sending message to: {}, contents: {}".format(url, message))

    # This should prevent out-of-order issues, which slack really doesn't like
    time.sleep(1)
    response = post(url, json=message)

    if response.status_code == 404:
        logger.error("Slack url has expired, aborting.")
        return False

    else:
        return True

def get_form_data(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        data = request.form.to_dict()
        return fn(data, *args, **kwargs)

    return inner


def get_json_data(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        data = json.loads(request.form["payload"])
        return fn(data, *args, **kwargs)

    return inner


class Flack(object):
    triggers = {}
    commands = {}
    actions = {}

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app

        if not self.app.config.get("FLACK_TOKEN"):
            raise SlackTokenError("A token must be defined")

        self.app.config.setdefault("FLACK_URL_PREFIX", "/flack")
        self.app.config.setdefault("FLACK_DEFAULT_NAME", "flack")

        blueprint = Blueprint('slack_flask',
                              __name__,
                              template_folder="templates")

        blueprint.add_url_rule("/webhook", methods=['POST'],
                               view_func=self.dispath_webhook)
        blueprint.add_url_rule("/command", methods=['POST'],
                               view_func=self.dispath_command)
        blueprint.add_url_rule("/action", methods=['POST'],
                               view_func=self.dispath_action)

        app.register_blueprint(blueprint,
                               url_prefix=self.app.config["FLACK_URL_PREFIX"])

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
            "username": user or self.app.config["FLACK_DEFAULT_NAME"],
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

    def validate_token(self, fn):
        @wraps(fn)
        def inner(data, *args, **kwargs):
            if data.get("token") != self.app.config["FLACK_TOKEN"]:
                # No response if the caller isn't valid.
                logger.error("Invalid Token")
                return ""
            else:
                return fn(data, *args, **kwargs)

        return inner

    def wrap_errors(self, fn):
        @wraps(fn)
        def inner(data, *args, **kwargs):
            try:
                return fn(data, *args, **kwargs)

            except Exception as e:
                logger.exception(
                    "Caught: {!s}, returning failure.".format(e))

                return self._response(re.sub(r"[\<\>]", "", str(e))
                                      private=True, replace=False)

        return inner

    @get_form_data
    @self.validate_token
    @self.wrap_errors
    def dispath_webhook(self, data):
        if not data["trigger_word"]:
            raise AttributeError("No trigger word supplied")

        prefix = len(data["trigger_word"])
        data["text"] = data["text"][prefix:].strip()

        try:
            callback, user = self.triggers[data["trigger_word"]]

        except KeyError as e:
            raise AttributeError("Unregistered trigger: {}".format(e))

        logger.info("Running trigger: '{}' with: '{}'".format(
            data["trigger_word"], data["text"]))

        req_user = CALLER(data["user_id"], data["user_name"], data["team_id"])
        response = callback(text=data["text"], user=req_user)
        return self._response(response, user=user)

    @get_form_data
    @self.validate_token
    @self.wrap_errors
    def _dispath_command(self, data):
        if not data["command"]:
            raise AttributeError("No trigger word supplied")

        try:
            callback = self.commands[data["command"]]

        except KeyError as e:
            raise AttributeError("Unregistered command: {}".format(e))

        logger.info("Running command: '{}' with: '{}'".format(
            data["command"], data["text"]))

        response = callback(text=data["text"],
                            user=CALLER(data["user_id"],
                                        data["user_name"],
                                        data["team_id"]),
                            channel=CHANNEL(data["channel_id"],
                                            data["channel_name"],
                                            data["team_id"]))

        return self._response(response, response_url=data["response_url"])

    @get_json_data
    @self.validate_token
    @self.wrap_errors
    def _dispath_action(self, data):
        if not len(data["actions"]):
            raise AttributeError("No action supplied")

        try:
            # Slack will only send one action per request.
            action = req["actions"][0]
            callback = self.actions[action["name"]]

        except KeyError as e:
            raise AttributeError("Unregistered action: {}".format(e))

        logger.info("Running action, data: {!r}".format(req))

        user = req["user"]
        channel = req["channel"]
        team = req["team"]
        response = callback(value=action["value"],
                            ts=req["message_ts"],
                            callback=req["callback_id"],
                            user=CALLER(user["id"],
                                        user["name"],
                                        team["id"]),
                            channel=CHANNEL(channel["id"],
                                            channel["name"],
                                            team["id"]))

        return self._response(response, response_url=req["response_url"])

    def trigger(self, trigger_word, **kwargs):
        if not trigger_word:
            raise AttributeError("invalid invocation")

        kwargs.setdefault("as_user", self.app.config["FLACK_DEFAULT_NAME"])

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
