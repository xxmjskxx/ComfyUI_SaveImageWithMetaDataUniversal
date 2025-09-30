"""Small misc utilities shared across nodes.

Keep this file lightweight: no heavy imports.
"""
from __future__ import annotations
from typing import Any

def unwrap_singleton(value: Any) -> Any:
    """Return the sole element of a 1-length list/tuple, else original value.

    This normalises captured metadata where some inputs are wrapped by
    graph execution layers but semantically scalar. Non-sequences or
    longer sequences are returned unchanged.
    """
    try:
        if isinstance(value, list | tuple) and len(value) == 1:  # noqa: UP038 explicit union
            return value[0]
    except Exception:
        return value
    return value
