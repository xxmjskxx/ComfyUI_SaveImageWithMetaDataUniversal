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
    if isinstance(raw, (int, float)):
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
    """Return list of (name, model_strength, clip_strength) respecting toggles and None entries."""
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
        v[0]
        for k, v in input_data[0].items()
        if k.startswith(prefix)
        and v
        and isinstance(v, list)
        and v[0] != "None"
    ]


# This dictionary holds all our pre-defined, safe selector functions.
SELECTORS = {
    "select_by_prefix": select_by_prefix,
    "collect_lora_stack": collect_lora_stack,
    "select_lora_names": select_lora_names,
    "select_lora_model_strengths": select_lora_model_strengths,
    "select_lora_clip_strengths": select_lora_clip_strengths,
}


def select_stack_by_prefix(input_data, prefix: str, counter_key: str | None = None, filter_none: bool = True):
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
            First elements from values whose keys start with prefix, possibly
            limited by counter_key and filtered for "None".

    Notes:
        - Always coerce list-like values to the first element (v[0]).
    """
    if not input_data or not isinstance(input_data, list) or not input_data[0]:
        return []

    items = []
    for k, v in input_data[0].items():
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
        items.append(first)

    if counter_key and counter_key in input_data[0] and isinstance(input_data[0][counter_key], list):
        try:
            max_n = int(input_data[0][counter_key][0])
            return items[:max_n]
        except Exception:
            return items
    return items

