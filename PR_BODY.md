## Test & CI Hardening Post-1.1.0

### Scope
This PR includes only changes introduced after the `v1.1.0` tag (`7b37693`). Node modularization and the `suppress_missing_class_log` flag shipped in 1.1.0 and are not attributed here.

### Additions Since 1.1.0
1. CI Corrections & Activation
   - Fixed incorrect `working-directory` paths in `unimeta-ci.yml`.
   - Ensured the `tests/` directory is included so tests actually run in CI.
2. Test Enhancements
   - Added/updated tests for:
     * JPEG fallback → comment marker path when EXIF is oversized.
     * Fallback stage markers & hash-detail toggle behavior.
     * Parameter string core ordering + snapshot note (future improvements documented).
   - Introduced lazy optional import for `PyYAML` in `test_bake_project.py` to avoid hard dependency.
3. Lint Hardening
   - Import ordering, variable naming, and long-line adjustments for Ruff compliance.
4. PR Metadata
   - Added this `PR_BODY.md` file (version-controlled PR description).

### Commits (Newest First)
```
d22db56 chore: add PR_BODY.md for branch PR description
1eabb89 tests: add future-improvements note to parameter string snapshot test
e6b0ab5 Tests: refine fallback & hash-detail tests; add JPEG comment fallback verification
f1652cf test: ruff lint fixes (imports, long lines, variable names)
d9de37f ci: include tests directory (remove ignore)
4614bfa ci: fix working-directory paths in unimeta-ci workflow
```

### Diff Context
Large historical deletions (e.g. `nodes/node.py`) predate this scope (were part of release 1.1.0). Current diff impact is predominantly test addition/refinement plus minor CI and config tweaks.

### Validation
* Tests: 64 passed, 1 skipped
* Ruff: clean
* Coverage: ~37% (≥ fail_under=35)

### Rationale
Makes previously prepared quality scaffolding effective by ensuring tests execute in CI and by explicitly covering nuanced fallback and hash-detail logic.

### Out of Scope (Already Released in 1.1.0)
* Node file modular split
* Log suppression runtime option
* Updated screenshots & example workflow assets

### Follow-Up Ideas
* Raise coverage threshold progressively (target 45% next).
* Expand sampler heuristic branch coverage.
* Optional: introduce partial allowlist snapshot testing for parameter formatting.

### Merge Strategy
No version bump (infrastructure / test enablement only). Merge once CI green. Rollback = single revert (no user-facing behavior changes introduced here).

---
If you need a 3–5 line executive summary header for reviewers, I can add it—just ask.
