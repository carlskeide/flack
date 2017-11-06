# coding=utf-8
from collections import namedtuple

__all__ = ["Attachment", "PrivateResponse", "IndirectResponse", ]

PrivateResponse = namedtuple("PrivateResponse", ("feedback"))
IndirectResponse = namedtuple("IndirectResponse", ("feedback", "indirect"))


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