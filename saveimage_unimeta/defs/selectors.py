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
    """
    Return a list of input values for keys starting with prefix.

    Args:
        input_data (list): List of dictionaries to search for keys.
        prefix (str): The prefix to match keys against.
        counter_key (str | None, optional): If provided and present in input_data[0], limits the number of returned items to the integer value at input_data[0][counter_key][0]. Defaults to None.
        filter_none (bool, optional): If True, entries with value "None" are skipped. Defaults to True.

    Returns:
        list: List of first elements from values whose keys start with prefix, possibly limited by counter_key and filtered for "None".

    Notes:
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

