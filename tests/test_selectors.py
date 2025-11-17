import pytest

from saveimage_unimeta.defs.selectors import (
    collect_lora_stack,
    select_by_prefix,
    select_lora_clip_strengths,
    select_lora_model_strengths,
    select_lora_names,
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


def test_select_stack_by_prefix_orders_by_numeric_suffix():
    data = _mk_input(
        {
            "lora_10": ["ten"],
            "lora_2": ["two"],
            "lora_1": ["one"],
            "lora_11": ["eleven"],
            "lora_count": [3],
        }
    )
    out = select_stack_by_prefix(data, "lora_", counter_key="lora_count")
    assert out == ["one", "two", "ten"]


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
    assert select_stack_by_prefix(None, "lora_") == []


def test_select_by_prefix_basic_behavior():
    data = _mk_input({"x_1": ["A"], "x_2": ["B"], "x_3": ["None"], "y": ["C"]})
    out = select_by_prefix(data, "x_")
    assert out == ["A", "B"]


def test_collect_lora_stack_respects_toggles_and_none():
    data = _mk_input(
        {
            "lora_count": [3],
            "lora_name_1": ["foo.safetensors"],
            "model_weight_1": ["0.0"],
            "clip_weight_1": ["0.0"],
            "switch_1": ["On"],
            "lora_name_2": ["bar.safetensors"],
            "model_weight_2": [0.75],
            "clip_weight_2": [0.33],
            "switch_2": ["Off"],
            "lora_name_3": ["None"],
            "model_weight_3": [1.0],
            "clip_weight_3": [1.0],
            "switch_3": ["On"],
        }
    )

    stack = collect_lora_stack(data)
    assert stack == [("foo.safetensors", "0.0", "0.0")]
    assert select_lora_names(data) == ["foo.safetensors"]
    assert select_lora_model_strengths(data) == ["0.0"]
    assert select_lora_clip_strengths(data) == ["0.0"]


def test_collect_lora_stack_falls_back_to_model_strength_for_clip():
    data = _mk_input(
        {
            "lora_count": [2],
            "lora_name_1": ["alpha.safetensors"],
            "lora_wt_1": [0.5],
            "switch_1": ["On"],
            "lora_name_2": ["beta.safetensors"],
            "lora_wt_2": [1.25],
            "switch_2": ["On"],
        }
    )

    stack = collect_lora_stack(data)
    assert stack == [
        ("alpha.safetensors", 0.5, 0.5),
        ("beta.safetensors", 1.25, 1.25),
    ]
