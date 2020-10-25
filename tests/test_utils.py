# coding=utf-8
from flack.utils import slack_username


def test_slack_username():
    assert slack_username("some_user") == "<@some_user>"
