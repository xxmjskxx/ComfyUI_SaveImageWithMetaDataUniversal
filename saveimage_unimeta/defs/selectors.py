def select_by_prefix(input_data, prefix):
    """
    A robust selector that finds all values from inputs whose keys start with a given prefix.
    """
    if not prefix:
        return []
    return [v[0] for k, v in input_data[0].items() if k.startswith(prefix) and v and isinstance(v, list) and v[0] != "None"]


# This dictionary holds all our pre-defined, safe selector functions.
SELECTORS = {
    "select_by_prefix": select_by_prefix,
}
