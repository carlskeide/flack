# coding=utf-8
from unittest.mock import Mock
from pytest import fixture

from flask import Flask
from flack import Flack

from . import WEBHOOK_DATA, COMMAND_DATA, BLOCK_ACTION_DATA


@fixture
def flack():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["FLACK_TOKEN"] = "test-token"
    app.config["FLACK_URL_PREFIX"] = "/test"

    return Flack(app)


def test_url_prefix(flack):
    mock_trigger = Mock()

    @flack.trigger("!test")
    def foo(*args, **kwargs):
        return mock_trigger(*args, **kwargs)

    client = flack.app.test_client()

    # No prefix
    client.post('/webhook', data=WEBHOOK_DATA)
    mock_trigger.assert_not_called()

    # Default prefix
    client.post('/flack/webhook', data=WEBHOOK_DATA)
    mock_trigger.assert_not_called()

    # Configured prefix
    client.post('/test/webhook', data=WEBHOOK_DATA)
    mock_trigger.assert_called()


def test_trigger(flack):
    mock_handler = Mock()
    mock_handler.return_value = "foo"

    @flack.trigger("!test")
    def trigger(*args, **kwargs):
        return mock_handler(*args, **kwargs)

    client = flack.app.test_client()
    response = client.post('/test/webhook', data=WEBHOOK_DATA)
    assert response.status_code == 200
    assert "foo" in str(response.data)

    # Flack shouldn't hadd positional args
    args, kwargs = mock_handler.call_args
    assert args == ()

    # See WEBHOOK_DATA
    assert set(kwargs.keys()) == {"text", "user"}

    assert kwargs["text"] == "Testing"

    assert kwargs["user"].id == "U2147483697"
    assert kwargs["user"].name == "Steve"
    assert kwargs["user"].team == "T0001"


def test_command(flack):
    mock_handler = Mock()
    mock_handler.return_value = "foo"

    @flack.command("/test")
    def foo(*args, **kwargs):
        return mock_handler(*args, **kwargs)

    client = flack.app.test_client()
    response = client.post('/test/command', data=COMMAND_DATA)
    assert response.status_code == 200
    assert "foo" in str(response.data)

    # Flack shouldn't hadd positional args
    args, kwargs = mock_handler.call_args
    assert args == ()

    # See COMMAND_DATA
    assert set(kwargs.keys()) == {"text", "trigger", "user", "channel"}

    assert kwargs["text"] == "Testing"
    assert kwargs["trigger"] == "1234.5678.abc123"

    assert kwargs["user"].id == "U2147483697"
    assert kwargs["user"].name == "Steve"
    assert kwargs["user"].team == "T0001"

    assert kwargs["channel"].id == "C2147483705"
    assert kwargs["channel"].name == "test"
    assert kwargs["channel"].team == "T0001"


def test_action(flack):
    mock_handler = Mock()
    mock_handler.return_value = "foo"

    @flack.action("test")
    def foo(*args, **kwargs):
        return mock_handler(*args, **kwargs)

    client = flack.app.test_client()
    response = client.post('/test/action', data=BLOCK_ACTION_DATA)
    assert response.status_code == 200
    assert "foo" in str(response.data)

    # Flack shouldn't hadd positional args
    args, kwargs = mock_handler.call_args
    assert args == ()

    # See BLOCK_ACTION_DATA
    assert set(kwargs.keys()) == {"value", "trigger", "message_ts", "user", "channel"}

    assert kwargs["value"] == "Testing"
    assert kwargs["trigger"] == "1234.5678.abc123"
    assert kwargs["message_ts"] == "1548261231.000200"

    assert kwargs["user"].id == "U2147483697"
    assert kwargs["user"].name == "Steve"
    assert kwargs["user"].team == "T0001"

    assert kwargs["channel"].id == "C2147483705"
    assert kwargs["channel"].name == "test"
    assert kwargs["channel"].team == "T0001"
