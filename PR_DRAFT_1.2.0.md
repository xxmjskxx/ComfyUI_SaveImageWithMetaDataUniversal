# PR: Release 1.2.0 – Scanner Lens Clarification, Isolation & Coverage Stability

## Summary
This PR merges `feature/scanner-mode-cleanup` into main, delivering clarified scanner lens semantics, isolated test artifact handling, loader & coverage robustness, and assorted quality refinements ahead of publishing tag `v1.2.0`.

## Key Changes
- Missing-only lens clarified (`include_existing=False`) with explicit tooltip guidance.
- Runtime test-mode path detection in loader prevents skipped user JSON merges under coverage.
- Unified `_test_outputs/user_rules` isolation across writer/loader/scanner + scanner mtime parity.
- Coverage reliability: placeholder `generated_user_rules.py` + omit entry removes transient source errors.
- Baseline scanner cache introduces diff hit/miss metrics.
- Timestamp suffix validation for backups now supports `-N` suffix forms.
- Backup restore dropdown & metrics summary from rules writer.

## Developer Experience
- Single CI workflow (matrix + lint autofix + coverage enforcement) simplifies maintenance.
- Narrowed exception scopes prevents accidental swallowing of logical errors in migration fallback.
- Tests expanded for lens filtering, sampler role retention, cache behavior.

## Risk / Mitigation
| Area | Risk | Mitigation |
|------|------|------------|
| Loader path logic | Missed user JSON merge | Runtime env re-eval + tests |
| Scanner default semantics | User confusion if default flipped | Reverted experimental change, documented final state |
| Coverage placeholder | Potential accidental inclusion at runtime | Omitted from coverage, harmless empty dict exports |

## Validation
- Test suite: 88 passed / 5 skipped (multi-Python via CI matrix).
- Coverage run stable (placeholder prevents missing source error).
- Manual targeted tests for loader merge & lens filtering pass.

## Changelog Extract
See `CHANGELOG.md` 1.2.0 section (mirrors `RELEASE_NOTES_1.2.0.md`).

## Follow Ups (Post-Merge)
- Consider raising coverage threshold after additional sampler/capture tests.
- Potential readability refactor for complex boolean generator in rules writer (low priority).
- Optional README snippet on coverage placeholder rationale (transparency).

## Checklist
- [x] Changelog updated & consolidated
- [x] Tag `v1.2.0` retagged to latest commit (a3cde8c)
- [x] Tests green locally & in CI
- [x] Coverage stable
- [x] No unintended default changes

Ready for review & merge.
