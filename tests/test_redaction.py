"""Tests for :mod:`saveimage_unimeta.utils.redaction`."""

from __future__ import annotations

import pytest

from saveimage_unimeta.utils import redaction
from saveimage_unimeta.utils.redaction import (
    REDACTED_PATH,
    REDACTED_SECRET,
    MetadataSanitizationError,
    sanitize_metadata_json,
)


def test_redacts_sensitive_keys() -> None:
    value = {"api_key": "sk-live-1234", "keep": "visible"}
    sanitized, count = sanitize_metadata_json(value)
    assert sanitized == {"api_key": REDACTED_SECRET, "keep": "visible"}
    assert count == 1


def test_redacts_nested_sensitive_keys() -> None:
    value = {"nodes": {"3": {"inputs": {"token": "abc", "text": "hi"}}}}
    sanitized, count = sanitize_metadata_json(value)
    assert sanitized["nodes"]["3"]["inputs"]["token"] == REDACTED_SECRET
    assert sanitized["nodes"]["3"]["inputs"]["text"] == "hi"
    assert count == 1


def test_sensitive_key_matching_is_alphanumeric() -> None:
    assert sanitize_metadata_json({"API_KEY": "x"}) == ({"API_KEY": REDACTED_SECRET}, 1)
    assert sanitize_metadata_json({"my_api_key_suffix": "x"}) == ({"my_api_key_suffix": "x"}, 0)


def test_redacts_bearer_token() -> None:
    sanitized, count = sanitize_metadata_json({"text": "Call Bearer abcdefghijklmnop now"})
    assert "abcdefghijklmnop" not in sanitized["text"]
    assert "Bearer " + REDACTED_SECRET in sanitized["text"]
    assert count == 1


def test_redacts_absolute_paths() -> None:
    cases = [
        "C:\\Users\\alice\\secret.txt",
        "C:/Users/alice/secret.txt",
        "\\\\server\\share\\file",
        "/home/alice/file",
        "/Users/alice/file",
    ]
    for case in cases:
        sanitized, count = sanitize_metadata_json({"path": case})
        assert sanitized["path"] == REDACTED_PATH, case
        assert count == 1


def test_keeps_relative_paths() -> None:
    sanitized, count = sanitize_metadata_json({"path": "outputs/my-image.png"})
    assert sanitized["path"] == "outputs/my-image.png"
    assert count == 0


def test_strips_control_characters_but_keeps_newlines() -> None:
    sanitized, _ = sanitize_metadata_json({"text": "a\x00b\x1bc\nd"})
    assert sanitized["text"] == "a b c\nd"


def test_preserves_primitives() -> None:
    value = {"none": None, "bool": True, "int": 7, "float": 1.5, "list": [1, "a"]}
    sanitized, count = sanitize_metadata_json(value)
    assert sanitized == value
    assert count == 0


def test_does_not_mutate_input() -> None:
    original = {"api_key": "sk-live-1234", "keep": "visible"}
    sanitize_metadata_json(original)
    assert original == {"api_key": "sk-live-1234", "keep": "visible"}


def test_depth_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(redaction, "MAX_METADATA_DEPTH", 3)
    with pytest.raises(MetadataSanitizationError):
        sanitize_metadata_json({"a": {"b": {"c": {"d": 1}}}})


def test_item_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(redaction, "MAX_METADATA_ITEMS", 3)
    with pytest.raises(MetadataSanitizationError):
        sanitize_metadata_json([1, 2, 3, 4])


def test_string_length_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(redaction, "MAX_METADATA_STRING_CHARS", 10)
    with pytest.raises(MetadataSanitizationError):
        sanitize_metadata_json({"text": "x" * 11})


def test_rejects_nonfinite_float() -> None:
    with pytest.raises(MetadataSanitizationError):
        sanitize_metadata_json({"x": float("nan")})


def test_rejects_unsupported_type() -> None:
    with pytest.raises(MetadataSanitizationError):
        sanitize_metadata_json({"x": b"bytes"})
