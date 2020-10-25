# coding=utf-8
__all__ = ["SlackTokenError", "OAuthConfigError", "OAuthError"]


class SlackTokenError(Exception):
    pass


class OAuthConfigError(Exception):
    pass


class OAuthError(Exception):
    pass
