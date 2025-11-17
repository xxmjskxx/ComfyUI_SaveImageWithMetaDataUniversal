"""Ad-hoc benchmark to compare legacy inline merge logic vs helper functions.

Relocated under tests/ so it is clearly a developer utility and not part of
runtime distribution. Still runnable directly:

    python -m tests.bench.bench_merge_performance

Outputs JSON summary to tests/_test_outputs/merge_bench.json (consistent with other
test artifacts) and prints a human-readable verdict.
"""

from __future__ import annotations

import json
import random
import statistics
import time
from collections.abc import Callable, Mapping, MutableMapping
from pathlib import Path
from typing import Any

SAMPLES = 2_000  # number of keys
MERGE_ITERS = 200  # merge operations per run
REPEAT = 5  # repetitions for timing stability

random.seed(42)
BASE = {f"Node{i}": {"a": i, "b": i * 2} for i in range(SAMPLES)}
USER_OK = {f"Node{i}": {"c": i + 1} for i in range(0, SAMPLES, 2)}
USER_BAD = {f"Bad{i}": [1, 2, 3] for i in range(0, SAMPLES, 10)}
USER_MIX = USER_OK | USER_BAD  # Python 3.9+ dict union


def legacy_merge(base: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    target = {k: (v.copy() if isinstance(v, dict) else v) for k, v in base.items()}
    for key, val in user.items():
        if isinstance(val, Mapping):
            existing = target.get(key)
            if not isinstance(existing, MutableMapping):
                target[key] = dict(val)
            else:
                existing.update(val)
        else:
            pass  # simulate skip
    return target


def helper_merge(base: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    target = {k: (v.copy() if isinstance(v, dict) else v) for k, v in base.items()}

    def _merge_user_sampler_entry(key: str, val):
        if not isinstance(val, Mapping):
            return
        existing = target.get(key)
        if not isinstance(existing, MutableMapping):
            target[key] = dict(val)
        else:
            existing.update(val)

    for key, val in user.items():
        _merge_user_sampler_entry(key, val)
    return target


def time_fn(fn: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]], label: str) -> float:
    timings = []
    for _ in range(REPEAT):
        start = time.perf_counter()
        for _ in range(MERGE_ITERS):
            fn(BASE, USER_MIX)
        end = time.perf_counter()
        timings.append(end - start)
    avg = statistics.mean(timings)
    stdev = statistics.pstdev(timings)
    print(f"{label}: avg={avg:.6f}s stdev={stdev:.6f}s over {REPEAT} runs")
    return avg


def main():
    print("Benchmark merge strategies (synthetic)")
    legacy_avg = time_fn(legacy_merge, "legacy-inline")
    helper_avg = time_fn(helper_merge, "helper-func")
    diff = helper_avg - legacy_avg
    pct = (diff / legacy_avg * 100.0) if legacy_avg else 0.0
    verdict = "OK (<=5% overhead)" if pct <= 5 else "Check: >5% overhead"
    result = {
        "legacy_avg_s": legacy_avg,
        "helper_avg_s": helper_avg,
        "delta_s": diff,
        "delta_pct": pct,
        "verdict": verdict,
        "config": {
            "SAMPLES": SAMPLES,
            "MERGE_ITERS": MERGE_ITERS,
            "REPEAT": REPEAT,
        },
    }
    print(f"Delta: {diff:.6f}s ({pct:.2f}%) -> {verdict}")
    repo_root = Path(__file__).resolve().parents[2]
    out_dir = repo_root / "tests" / "_test_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "merge_bench.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Wrote {out_file}")


if __name__ == "__main__":  # pragma: no cover - manual utility
    main()
