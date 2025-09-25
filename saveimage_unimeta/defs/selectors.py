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
}


def select_stack_by_prefix(input_data, prefix: str, counter_key: str | None = None, filter_none: bool = True):
    """Return a list of input values for keys starting with prefix.

    - If counter_key is provided and exists as an int in input_data[0][counter_key][0], limit the length.
    - When filter_none is True, entries with value "None" are skipped.
    - Always coerce list-like values to the first element (v[0]).
    """
    if not input_data or not isinstance(input_data, list) or not input_data[0]:
        return []

    items = []
    for k, v in input_data[0].items():
        if not isinstance(k, str) or not k.startswith(prefix):
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

