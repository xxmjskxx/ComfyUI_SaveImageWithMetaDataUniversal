import pytest

from saveimage_unimeta.defs.selectors import (
    select_by_prefix,
    select_stack_by_prefix,
)


def _mk_input(d):
    """Helper to wrap a dict into the input_data structure used by selectors."""
    return [d]


def test_select_stack_by_prefix_basic_and_filtering():
    data = _mk_input(
        {
            "lora_1": ["a"],
            "lora_2": ["b"],
            "lora_3": ["None"],  # should be filtered by default
            "other": ["x"],
        }
    )
    out = select_stack_by_prefix(data, "lora_")
    assert out == ["a", "b"]


def test_select_stack_by_prefix_filter_none_false():
    data = _mk_input({"lora_1": ["a"], "lora_2": ["None"]})
    out = select_stack_by_prefix(data, "lora_", filter_none=False)
    assert out == ["a", "None"]


def test_select_stack_by_prefix_counter_key_limits_results():
    data = _mk_input(
        {
            "lora_1": ["a"],
            "lora_2": ["b"],
            "lora_count": [1],
        }
    )
    out = select_stack_by_prefix(data, "lora_", counter_key="lora_count")
    assert out == ["a"]


def test_select_stack_by_prefix_counter_key_too_large_returns_all():
    data = _mk_input(
        {
            "lora_1": ["a"],
            "lora_2": ["b"],
            "lora_count": [99],
        }
    )
    out = select_stack_by_prefix(data, "lora_", counter_key="lora_count")
    assert out == ["a", "b"]


def test_select_stack_by_prefix_counter_key_invalid_ignored():
    data = _mk_input(
        {
            "lora_1": ["a"],
            "lora_2": ["b"],
            "lora_count": ["notint"],
        }
    )
    out = select_stack_by_prefix(data, "lora_", counter_key="lora_count")
    assert out == ["a", "b"]


def test_select_stack_by_prefix_skips_nonlist_and_nonstring_keys():
    data = _mk_input(
        {
            "lora_1": ["a"],
            5: ["z"],  # non-string key, should be ignored
            "lora_2": "b",  # non-list value, should be ignored
        }
    )
    out = select_stack_by_prefix(data, "lora_")
    assert out == ["a"]


def test_select_stack_by_prefix_empty_and_none_inputs():
    assert select_stack_by_prefix([], "lora_") == []
    assert select_stack_by_prefix(None, "lora_") == []  # type: ignore[arg-type]


def test_select_by_prefix_basic_behavior():
    data = _mk_input({"x_1": ["A"], "x_2": ["B"], "x_3": ["None"], "y": ["C"]})
    out = select_by_prefix(data, "x_")
    assert out == ["A", "B"]
