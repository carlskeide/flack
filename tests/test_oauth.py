# coding=utf-8
from unittest.mock import patch, Mock

import pytest
from flask import Flask
from requests import HTTPError

from flack.oauth import (
    render_button,
    callback,
    _oauth_callback_response,
    OAuthError,
    OAuthConfigError,
    DEFAULT_OAUTH_SCOPE
)


def test_render_button() -> str:
    app = Flask(__name__, template_folder='../flack/templates')
    with pytest.raises(OAuthConfigError):
        with app.app_context():
            render_button()

    app.config["FLACK_CLIENT_ID"] = "abc123"
    with app.app_context():
        html = render_button()
    assert "client_id=abc123" in html
    assert "scope={}".format(DEFAULT_OAUTH_SCOPE) in html

    app.config["FLACK_SCOPE"] = "admin"
    with app.app_context():
        html = render_button()
    assert "scope=admin" in html


@patch("flack.oauth._oauth_callback_response")
def test_callback(mock_callback):
    app = Flask(__name__)
    with app.app_context():
        with pytest.raises(OAuthConfigError):
            @callback
            def foo(credentials):
                pass

        app.config["FLACK_CLIENT_ID"] = "abc123"
        app.config["FLACK_CLIENT_SECRET"] = "def456"

        @app.route("/oauth")
        @callback
        def foo(credentials):
            assert credentials == ("super", "secret")

        with app.test_request_context('/oauth'):
            with pytest.raises(OAuthError):
                foo()
            mock_callback.assert_not_called()

        mock_callback.return_value = ("super", "secret")
        with app.test_request_context('/oauth?code=secret'):
            foo()
            mock_callback.assert_called_with("secret")


@patch("flack.oauth.post")
def test__oauth_callback_response(mock_post):
    app = Flask(__name__)
    app.config["FLACK_CLIENT_ID"] = "abc123"
    app.config["FLACK_CLIENT_SECRET"] = "def456"

    mock_response = Mock()
    mock_post.return_value = mock_response
    mock_response.json.return_value = {
        "access_token": "foo",
        "scope": "bar",
        "team_id": "baz"
    }

    with app.app_context():
        credentials = _oauth_callback_response("foo")
    assert credentials.access_token == "foo"
    assert credentials.scope == "bar"
    assert credentials.team_id == "baz"

    mock_response.raise_for_status.side_effect = HTTPError("some-error")
    with pytest.raises(OAuthError):
        with app.app_context():
            _oauth_callback_response("foo")

    mock_response.json.side_effect = ValueError("bad")
    with pytest.raises(OAuthError):
        with app.app_context():
            _oauth_callback_response("foo")
