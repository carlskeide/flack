# coding=utf-8
from flack.message import Attachment, Action


def test_attachment():
    obj = Attachment(color="red", flower="rose", image_url="some-rose.jpg")
    assert obj.as_dict == {"color": "red", "image_url": "some-rose.jpg"}


def test_action():
    obj = Action(name="bob", style="button", color="red")
    assert obj.as_dict == {"name": "bob", "style": "button"}
