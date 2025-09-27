# Release 1.2.0

Tag: v1.2.0  
Date: 2025-09-26

## Highlights
- Missing-only lens semantics clearly defined (`include_existing=False`), default remains False (reverted experimental toggle before release).
- Unified test artifact isolation (`_test_outputs/user_rules`) across writer, loader, scanner.
- Loader runtime test-mode path detection fixes CI merge behavior.
- Coverage stability via placeholder `generated_user_rules.py` + configured omit.
- Timestamp suffix validation now accepts `YYYYMMDD-HHMMSS-N` forms.
- Baseline scanner cache with hit/miss accounting in diff report.
- Backup restore dropdown and metrics summary for custom rules writer.

## Added
- Baseline cache (`BaselineCache=hit:X|miss:Y`) in scanner diff.
- Coverage threshold (fail-under 35%) & matrix (3.10–3.12, test-mode variants).
- Backup set restore selector (`restore_backup_set`).
- Diff parsing helper (`tests/diff_utils.parse_diff_report`).
- New tests: missing-only lens, forced sampler role retention, cache parity.
- Benchmark relocated to `tests/bench/bench_merge_performance.py`.

## Changed
- Consolidated CI into single workflow (`unimeta-ci.yml`).
- Clarified tooltips (include_existing, rules JSON schema) & wrapped long lines.
- Path parity & mtime cache logic for user rule JSON under isolation.
- Moved `MIGRATIONS.md` to `docs/`.

## Fixed
- Loader merge under coverage (late env flag evaluation).
- Coverage error: 'No source for code' by ensuring placeholder & omit.
- Timestamp suffix validation for backup pruning.
- Append test path mismatch after isolation.
- Potential stale scanner baseline cache under isolated path.
- Overly broad exception catches narrowed to `OSError` in migration fallback.
- Duplicate sampler role registration in tests removed.

## Internal / Quality
- Refined `_looks_like_timestamp` suffix handling.
- Improved resilience & explicitness of test scaffolding.

## Upgrade Notes
No breaking defaults changed relative to 1.1.x (temporary experimental default for `include_existing` rolled back before release). Users relying on missing-only lens behavior should explicitly set `include_existing=False` (still the default).

## Contributors
- Automated assistant + maintainers.

---
Checksum of tag commit: a3cde8c (verify with `git show v1.2.0 --no-patch`).
