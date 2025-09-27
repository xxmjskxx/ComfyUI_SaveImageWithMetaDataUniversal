"""Test helper utilities for parsing scanner diff reports.

The scanner emits a semicolon-separated summary string, e.g.:
    "Mode=all; MissingLens=on; New nodes=1; ...; BaselineCache=hit:1|miss:1; Force metafields=None"

This helper normalizes that into a dictionary for easier assertions.
"""
from __future__ import annotations

from typing import Any


def parse_diff_report(diff: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if not isinstance(diff, str):  # defensive
        return result
    parts = [p.strip() for p in diff.split(";") if p.strip()]
    for raw in parts:
        if "=" not in raw:
            continue
        key, val = raw.split("=", 1)
        key = key.strip()
        val = val.strip()
        if key == "MissingLens":
            result["missing_lens"] = val.lower() in {"on", "true", "1"}
        elif key == "Mode":
            result["mode"] = val
        elif key == "New nodes":
            result["new_nodes"] = _to_int(val)
        elif key.startswith("Existing nodes"):
            result["existing_nodes_with_new_fields"] = _to_int(val)
        elif key == "New fields":
            result["new_fields"] = _to_int(val)
        elif key == "Existing fields included":
            result["existing_fields_included"] = _to_int(val)
        elif key == "Skipped fields":
            result["skipped_fields"] = _to_int(val)
        elif key == "Force metafields":
            result["force_metafields"] = [] if val == "None" else [v for v in val.split(",") if v]
        elif key == "Forced node classes":  # only present when forced list non-empty
            result["forced_node_classes"] = [] if val == "None" else [v for v in val.split(",") if v]
        elif key == "BaselineCache":
            hit, miss = None, None
            if "|" in val:
                segs = val.split("|")
                for seg in segs:
                    if seg.startswith("hit:"):
                        hit = _to_int(seg[4:])
                    elif seg.startswith("miss:"):
                        miss = _to_int(seg[5:])
            result["baseline_cache"] = {"hit": hit, "miss": miss}
        else:
            # Fallback: store raw
            result[key.lower().replace(" ", "_")] = val
    return result


def _to_int(val: str) -> int:
    try:
        return int(val)
    except Exception:  # pragma: no cover - defensive
        return 0


__all__ = ["parse_diff_report"]
