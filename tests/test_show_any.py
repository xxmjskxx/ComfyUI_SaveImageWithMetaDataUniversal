import json
from typing import Any

import pytest

from saveimage_unimeta.nodes.show_any import ShowAnyToString, _safe_to_str


class DummyArray:
    def __init__(self, shape=(2, 3), dtype="float32"):
        self.shape = shape
        self.dtype = dtype


class DummyImage:
    def __init__(self, size=(512, 512), mode="RGB"):
        self.size = size
        self.mode = mode


def test_safe_to_str_basic_types():
    assert _safe_to_str("hello") == "hello"
    assert _safe_to_str(123) == "123"
    assert _safe_to_str(3.14) == "3.14"
    assert _safe_to_str(True) == "True"
    assert _safe_to_str(None) == ""
    assert _safe_to_str(b"bytes") == "bytes"


def test_safe_to_str_summaries():
    arr = DummyArray((1, 2, 3), "float16")
    s = _safe_to_str(arr)
    assert "DummyArray" in s and "shape=(1, 2, 3)" in s and "dtype=float16" in s

    img = DummyImage((256, 128), "L")
    s2 = _safe_to_str(img)
    assert "DummyImage" in s2 and "size=(256, 128)" in s2 and "mode=L" in s2


def test_safe_to_str_json_fallback_and_truncation():
    # JSON default=str fallback
    class Unserializable:
        def __repr__(self) -> str:  # fallback path
            return "<Unserializable>"

    assert _safe_to_str({"x": Unserializable()}).startswith("{")

    # Truncation
    long_text = "x" * 2100
    s = _safe_to_str(long_text, max_len=2000)
    # Expected length is max_len + len(" …(+{extra} chars)") where extra=100 -> +14
    assert len(s) <= 2014 and s.endswith(" chars)")


def test_notify_ui_and_result_shapes():
    node = ShowAnyToString()
    values = [123, "abc"]
    out = node.notify(values, display=None, unique_id=None, extra_pnginfo=None)
    assert "ui" in out and "text" in out["ui"]
    assert out["ui"]["text"] == ["123", "abc"]
    assert out["result"] == (["123", "abc"],)


def test_notify_persists_widgets_values_into_workflow():
    node = ShowAnyToString()
    # Simulate Comfy's unique_id as list
    unique_id = [42]
    workflow = {"nodes": [{"id": 42}]}
    extra = [{"workflow": workflow}]

    out = node.notify(["alpha", "beta"], display=None, unique_id=unique_id, extra_pnginfo=extra)
    assert out["ui"]["text"] == ["alpha", "beta"]
    # Should join into a single display string in widgets_values
    node_obj = workflow["nodes"][0]
    assert "widgets_values" in node_obj
    assert node_obj["widgets_values"] == ["alpha\nbeta"]


def test_anytype_wildcard_accepts_all_kinds():
    # Ensure the wildcard type behaves as a string token and equals any kind
    from saveimage_unimeta.nodes.show_any import AnyType, any_type, ShowAnyToString  # noqa: WPS433

    assert isinstance(any_type, str)
    assert isinstance(any_type, AnyType)

    for kind in [
        "STRING",
        "IMAGE",
        "LATENT",
        "MASK",
        "MODEL",
        "CONDITIONING",
        "VAE",
        "CLIP",
        "*",
        "CUSTOM_TOKEN",
    ]:
        assert any_type == kind
        assert not (any_type != kind)

    # INPUT_TYPES returns the wildcard type for required 'value'
    it = ShowAnyToString.INPUT_TYPES()
    assert it["required"]["value"][0] == any_type
