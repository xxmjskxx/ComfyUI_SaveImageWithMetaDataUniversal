"""Tests for :mod:`saveimage_unimeta.utils.pathsafety`."""

from __future__ import annotations

from saveimage_unimeta.utils.pathsafety import (
    MAX_COMPONENT_LENGTH,
    sanitize_component,
    sanitize_filename,
)


def test_component_replaces_invalid_characters() -> None:
    assert sanitize_component('a<b>c:"d"|e?f*g') == "a_b_c__d__e_f_g"


def test_component_replaces_separators() -> None:
    assert sanitize_component("a/b\\c") == "a_b_c"


def test_component_strips_trailing_dots_and_spaces() -> None:
    assert sanitize_component("name... ") == "name"


def test_component_reserved_windows_names() -> None:
    assert sanitize_component("CON") == "_CON"
    assert sanitize_component("con.txt") == "_con.txt"
    assert sanitize_component("COM1") == "_COM1"
    assert sanitize_component("LPT9") == "_LPT9"


def test_component_empty_falls_back() -> None:
    assert sanitize_component("") == "image"
    assert sanitize_component("... ") == "image"


def test_component_clamps_length() -> None:
    assert len(sanitize_component("x" * 500)) == MAX_COMPONENT_LENGTH


def test_filename_normalizes_backslashes() -> None:
    assert sanitize_filename("folder\\sub\\name") == "folder/sub/name"


def test_filename_strips_drive_letter() -> None:
    assert sanitize_filename("C:\\Users\\alice\\out") == "Users/alice/out"


def test_filename_strips_leading_slashes() -> None:
    assert sanitize_filename("/abs/path") == "abs/path"
    assert sanitize_filename("//unc/path") == "unc/path"


def test_filename_drops_traversal_components() -> None:
    assert sanitize_filename("../../etc/passwd") == "etc/passwd"
    assert sanitize_filename("a/../b") == "a/b"


def test_filename_falls_back_for_empty() -> None:
    assert sanitize_filename("") == "image"
    assert sanitize_filename("../../..") == "image"


def test_filename_preserves_valid_subfolder() -> None:
    assert sanitize_filename("batch/portrait-%seed%") == "batch/portrait-%seed%"


def test_filename_preserves_percent_sign() -> None:
    assert sanitize_filename("50% off") == "50% off"


def test_filename_clamps_total_length() -> None:
    long_path = "/".join("x" * 100 for _ in range(10))
    assert len(sanitize_filename(long_path)) <= 512
