## Test suite & CI consolidation: coverage gating, JPEG fallback validation, lint hardening

### Summary
This PR adds a comprehensive test suite, enforces coverage gating, consolidates CI into a single workflow, validates staged EXIF→comment JPEG fallback logic, and introduces a log suppression flag for cleaner metadata rule loading output. It also modularizes the previously monolithic `nodes/node.py` into discrete, maintainable node modules (work already performed on this branch but not yet on `master`).

### Key Changes
1. CI / Quality
   - Single workflow: `unimeta-ci.yml` (matrix tests 3.10–3.12, coverage report, strict Ruff lint, auto-fix lint job).
   - Coverage gating via `.coveragerc` (`fail_under=35`, current ~37%).
   - Restored `tests/` to CI (was effectively ignored before).
   - Fixed incorrect `working-directory` paths in CI.

2. Code & Features
   - Modularization: Split large `nodes/node.py` into `save_image.py`, `scanner.py`, `rules_save.py`, `rules_writer.py`, `rules_view.py`, `extra_metadata.py`.
   - Added `suppress_missing_class_log` parameter to silence benign missing-class info logs.
   - Robust staged JPEG metadata fallback (full → reduced-exif → minimal → com-marker) fully tested.
   - Ensures single `, Metadata Fallback: <stage>` marker (no duplication).

3. Testing (new >50 tests)
   - Fallback stages & JPEG comment embedding when EXIF overflows.
   - Parameter ordering determinism & trimming allowlist logic.
   - LoRA aggregation, inline variants, summary toggle.
   - Embedding and model/vae hash detail & suppression env flag.
   - Forced include rule class injection & scanner logic.
   - Multi-image EXIF / parameter concatenation.
   - Civitai sampler + scheduler mapping.
   - Optional PyYAML usage made lazy (no hard dependency for CI) in cookiecutter bake test.

4. Documentation & Assets
   - Updated `README.md` & `README.jp.md` (log suppression option, refreshed screenshots, example workflow assets).
   - Added images: `img/save-image.png`, `img/metadata-create-and-save.png`.
   - Updated example workflow JSON & rule scan artifacts.

5. Tooling / Internals
   - Added `piexif_alias.py` for safe import + stubbing.
   - Environment flag handling remains runtime-evaluated (no restart required):
     `METADATA_NO_HASH_DETAIL`, `METADATA_NO_LORA_SUMMARY`, `METADATA_TEST_MODE`, `METADATA_DEBUG_PROMPTS`.

### Commits Ahead of master
```
e6b0ab5 Tests: refine fallback & hash-detail tests; add JPEG comment fallback verification
f1652cf test: ruff lint fixes (imports, long lines, variable names)
d9de37f ci: include tests directory (remove ignore)
4614bfa ci: fix working-directory paths in unimeta-ci workflow
1eabb89 tests: add future-improvements note to parameter string snapshot test (includes optional PyYAML gate)
```

### Diff Stat (summary)
`5195 insertions(+), 2514 deletions(-) across 54 files` (bulk = new tests + node modularization + assets)

### Rationale
Establishes a maintainable, quality-gated baseline after 1.1.0: deterministic output verified, fallback behavior enforced, and reduced future merge risk by splitting monolith.

### Validation
Local & CI (expected):
* Ruff: clean (strict profile)
* Pytest: 64 passed, 1 skipped
* Coverage: ~37% (>= 35 threshold)

### Risk / Mitigation
| Area | Risk | Mitigation |
|------|------|------------|
| Modularization | Missed import path | Test suite covers primary flows |
| EXIF fallback | Marker duplication regression | Explicit tests for each stage & comment fallback |
| Log suppression | Masking real errors | Only suppresses known benign missing-class message |

### Follow-Up (Deferred)
* Incrementally raise coverage threshold (targets: 45% → 55% → 65%).
* Additional sampler heuristic branch coverage.
* Potential workflow JSON compression (placeholder only in docs).

### No Version Bump
Intentionally no bump (post-1.1.0 hardening). Can tag later if distribution channels need the expanded test infra recognized.

### How to Review
1. Skim new node files for structural clarity (behavior unchanged vs prior logic).
2. Review fallback tests (`test_metadata_fallback.py`, `test_metadata_fallback_stages.py`, `test_metadata_jpeg_comment.py`).
3. Validate log suppression parameter docs in README / JP README.
4. Confirm CI workflow strategy (single matrix + lint separation) fits project direction.

### How to Merge Safely
CI should be green first. If any environment-specific failures (e.g., optional deps) arise, they can be skipped gracefully (PyYAML now optional). Merge normally once checks pass.

### Rollback Plan
Single revert of this merge commit restores pre-test baseline. If only coverage gating blocks future experimental branches, temporarily increase `fail_under` in `.coveragerc`.

---
Let me know if you prefer a shorter executive summary variant.
