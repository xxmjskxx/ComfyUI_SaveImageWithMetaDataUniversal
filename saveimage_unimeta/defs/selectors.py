from __future__ import annotations

import math


def _coerce_first(value):
    if isinstance(value, list | tuple):  # noqa: UP038
        return value[0] if value else None
    return value


def _normalize_key(key: str) -> str:
    return key.lower().replace(" ", "_")


def _build_normalized_map(input_data):
    if not input_data or not isinstance(input_data, list):
        return {}
    first = input_data[0]
    if not isinstance(first, dict):
        return {}
    normalized = {}
    for key, value in first.items():
        if not isinstance(key, str):
            continue
        normalized[_normalize_key(key)] = (key, value)
    return normalized


def _extract_index(key: str, prefix: str) -> int | None:
    if not key.startswith(prefix):
        return None
    suffix = key[len(prefix) :]
    if suffix.startswith("_"):
        suffix = suffix[1:]
    if not suffix:
        return None
    digits = []
    for ch in suffix:
        if ch.isdigit():
            digits.append(ch)
        else:
            break
    if not digits:
        return None
    try:
        return int("".join(digits))
    except ValueError:
        return None


def _gather_indices(normalized_map, prefixes):
    indices = set()
    for key in normalized_map.keys():
        for prefix in prefixes:
            idx = _extract_index(key, prefix)
            if idx is not None:
                indices.add(idx)
                break
    return indices


def _value_for_index(normalized_map, prefixes, idx):
    idx_options = {str(idx), f"{idx:02d}"}
    for prefix in prefixes:
        for candidate_idx in idx_options:
            for sep in ("_", ""):
                lookup = f"{prefix}{sep}{candidate_idx}"
                if lookup in normalized_map:
                    return _coerce_first(normalized_map[lookup][1])
    return None


def _toggle_truthy(raw) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, int | float):
        return not math.isclose(float(raw), 0.0, abs_tol=1e-9)
    try:
        text = str(raw).strip().lower()
    except Exception:
        return True
    if text == "":
        return False
    if text in {"off", "false", "0", "disable", "disabled", "no"}:
        return False
    if text in {"on", "true", "1", "enable", "enabled", "yes"}:
        return True
    return True


_LORA_NAME_PREFIXES = ("lora_name", "lora")
_LORA_TOGGLE_PREFIXES = ("switch", "toggle", "enabled", "enable", "active")
_LORA_MODEL_STRENGTH_PREFIXES = (
    "model_str",
    "model_strength",
    "model_weight",
    "strength_model",
    "lora_wt",
    "lora_strength",
)
_LORA_CLIP_STRENGTH_PREFIXES = (
    "clip_str",
    "clip_strength",
    "clip_weight",
    "strength_clip",
    "lora_wt",
    "lora_strength",
)
_LORA_COUNTER_KEYS = (
    "lora_count",
    "num_loras",
    "lora_total",
    "lora_len",
    "lora_length",
)


def _resolve_counter(normalized_map) -> int | None:
    for key in _LORA_COUNTER_KEYS:
        if key in normalized_map:
            raw = _coerce_first(normalized_map[key][1])
            try:
                return int(float(raw))
            except Exception:
                continue
    return None


def collect_lora_stack(input_data):
    """
    Collect LoRA stack from input data.

    Args:
        input_data (list[dict[str, list]]): List containing a dictionary with string keys and list values.

    Returns:
        list[tuple[str, Any, Any]]: List of tuples (name, model_strength, clip_strength).

    Filtering behavior:
        - Entries with a toggle switch set to 'Off' (case-insensitive) are excluded.
        - Entries with name set to 'None' (case-insensitive) or an empty string are excluded.
        - Only entries with a valid name and enabled toggle are included in the result.
    """
    normalized = _build_normalized_map(input_data)
    if not normalized:
        return []

    counter = _resolve_counter(normalized)
    indices = _gather_indices(normalized, _LORA_NAME_PREFIXES)
    if counter is None and not indices:
        indices = _gather_indices(normalized, _LORA_TOGGLE_PREFIXES)

    if counter is not None and counter > 0:
        candidate_indices = range(1, counter + 1)
    else:
        candidate_indices = sorted(indices)

    stack = []
    for idx in candidate_indices:
        try:
            index_int = int(idx)
        except Exception:
            continue
        if index_int <= 0:
            continue
        name = _value_for_index(normalized, _LORA_NAME_PREFIXES, index_int)
        if name is None:
            continue
        name_str = str(name).strip()
        if name_str == "" or name_str.lower() == "none":
            continue
        toggle_val = _value_for_index(normalized, _LORA_TOGGLE_PREFIXES, index_int)
        if toggle_val is not None and not _toggle_truthy(toggle_val):
            continue
        model_strength = _value_for_index(normalized, _LORA_MODEL_STRENGTH_PREFIXES, index_int)
        clip_strength = _value_for_index(normalized, _LORA_CLIP_STRENGTH_PREFIXES, index_int)
        if clip_strength is None:
            clip_strength = model_strength
        stack.append((name, model_strength, clip_strength))
    return stack


def select_lora_names(input_data):
    return [entry[0] for entry in collect_lora_stack(input_data)]


def select_lora_model_strengths(input_data):
    return [entry[1] for entry in collect_lora_stack(input_data)]


def select_lora_clip_strengths(input_data):
    return [entry[2] for entry in collect_lora_stack(input_data)]


def select_by_prefix(input_data, prefix):
    """
    A robust selector that finds all values from inputs whose keys start with a given prefix.
    """
    if not prefix:
        return []
    return [
        v[0] for k, v in input_data[0].items() if k.startswith(prefix) and v and isinstance(v, list) and v[0] != "None"
    ]


# This dictionary holds all our pre-defined, safe selector functions.
SELECTORS = {
    "select_by_prefix": select_by_prefix,
    "collect_lora_stack": collect_lora_stack,
    "select_lora_names": select_lora_names,
    "select_lora_model_strengths": select_lora_model_strengths,
    "select_lora_clip_strengths": select_lora_clip_strengths,
}


def select_stack_by_prefix(
    input_data,
    prefix: str,
    counter_key: str | None = None,
    filter_none: bool = True,
    include_indices: bool = False,
):
    """
    Return a list of input values for keys starting with a prefix.

    Args:
        input_data (list):
            List of dictionaries to search for keys.
        prefix (str):
            The prefix to match keys against.
        counter_key (str | None, optional):
            If provided and present in input_data[0], limits the number of
            returned items to the integer value at
            input_data[0][counter_key][0]. Defaults to None.
        filter_none (bool, optional):
            If True, entries with value "None" are skipped. Defaults to True.

    Returns:
        list:
            When `include_indices` is False (default), returns the first
            elements from values whose keys start with prefix. When True,
            returns ``(index, value)`` tuples so callers can keep the numeric
            suffix alongside the captured value. Both modes respect
            ``counter_key`` trimming and "None" filtering.

    Notes:
        - Always coerce list-like values to the first element (v[0]).
    """
    if not input_data or not isinstance(input_data, list) or not input_data[0]:
        return []

    items = []
    for order_idx, (k, v) in enumerate(input_data[0].items()):
        if not isinstance(k, str) or not k.startswith(prefix):
            continue
        # Do not include the counter_key itself in the returned items
        # because it contains the count value, not a stack item to return
        if counter_key and k == counter_key:
            continue
        if not v or not isinstance(v, list):
            continue
        first = v[0]
        if filter_none and first == "None":
            continue
        idx = _extract_index(k, prefix)
        items.append((idx, order_idx, first))

    has_index = any(entry[0] is not None for entry in items)
    if has_index:
        items.sort(key=lambda entry: (entry[0] is None, entry[0] if entry[0] is not None else entry[1]))

    if include_indices:
        ordered_values = [(entry[0], entry[2]) for entry in items]
    else:
        ordered_values = [entry[2] for entry in items]

    if counter_key and counter_key in input_data[0] and isinstance(input_data[0][counter_key], list):
        try:
            max_n = int(input_data[0][counter_key][0])
            return ordered_values[:max_n]
        except Exception:
            return ordered_values
    return ordered_values


def _aligned_strengths_for_prefix(input_data, strength_prefix: str):
    """Return strengths matched to populated LoRA name indices.

    When advanced stacker modes expose more strength fields than active
    ``lora_name_*`` slots (for example, stray ``model_str_50`` values that
    remain at defaults), we only want the entries that correspond to real
    names. This helper mirrors the fallback traversal used by
    ``get_lora_model_name_stack`` and filters the strength list so it stays in
    lock-step with the resolved names.
    """

    name_entries = select_stack_by_prefix(
        input_data,
        "lora_name",
        counter_key="lora_count",
        include_indices=True,
    )
    if not name_entries:
        return select_stack_by_prefix(
            input_data,
            strength_prefix,
            counter_key="lora_count",
        )
    strength_entries = list(
        select_stack_by_prefix(
            input_data,
            strength_prefix,
            counter_key="lora_count",
            include_indices=True,
        )
    )
    matched: list = []
    for idx, _name in name_entries:
        chosen = None
        if idx is not None:
            for pos, (s_idx, sval) in enumerate(strength_entries):
                if s_idx == idx:
                    chosen = sval
                    strength_entries.pop(pos)
                    break
        if chosen is None and strength_entries:
            chosen = strength_entries.pop(0)[1]
        matched.append(chosen)
    return matched
