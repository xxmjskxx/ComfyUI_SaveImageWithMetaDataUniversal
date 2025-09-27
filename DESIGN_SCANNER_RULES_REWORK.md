# Scanner & Rules Writer Planned Changes (Staging Document)

This file captures the agreed design before implementation for:
1. Repurposing the `Metadata Rule Scanner` legacy `include_existing` toggle.
2. Enhancing `Save Custom Metadata Rules` with append, backup, and restore features.
3. Relocating user JSON / examples directory (`py/` -> `user_rules/`).

---
## 1. Metadata Rule Scanner Changes

### Current Redundancy
`include_existing` only upgrades `mode=new_only` into `all`. Redundant with explicit `mode` selection.

### New Purpose ("missing vs user rules" lens)
Repurpose toggle (same input key for backward compatibility) to filter out any metafields and sampler roles already present in:
- Built-in defaults
- Loaded Python extensions (including `generated_user_rules.py`)
- User JSON (if present after conditional merge) – optional inclusion depending on implementation order

Effective behavior when repurposed toggle (name TBD: `filter_existing_user_rules`) is ON:
| mode | Result |
|------|--------|
| new_only | Only fields/roles not present in union of existing sources (similar to current but expanded baseline). |
| all | All nodes, but restricted to missing-only (turns into global missing-only lens). |
| existing_only | Only nodes already in baseline, restricted to missing fields/roles. |

Status tagging: All emitted entries become `status=new` (they are, by definition, absent). Optionally include a `filtered_count` in diff report.

### Error Handling
If `generated_user_rules.py` import fails: log warning, degrade to current behavior (baseline = defaults + extensions that DID load).

### Logging
One-time INFO each session: `Scanner: legacy include_existing repurposed; select mode=all for prior full-scan behavior.`

### Tests
1. Baseline missing detection with toggle OFF vs ON.
2. With a synthetic `generated_user_rules.py` containing some fields → ensure those disappear when toggle ON.
3. Sampler role filtering.
4. Import failure path (mock error) fallback.

---
## 2. Save Custom Metadata Rules Enhancements

### New Inputs
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `save_mode` | enum(`overwrite`,`append_new`) | overwrite | Overwrite replaces files; append_new merges only missing entries. |
| `backup_before_save` | bool | True | Create timestamped backup set before modifications. |
| `restore_backup_set` | enum(`none`, dynamic timestamps…) | none | If set to a timestamp, restore that backup set (ignore rules input). |
| `replace_conflicts` | bool | False | When `append_new`, replace conflicting metafields / sampler roles if True; otherwise skip. |
| `rebuild_python_rules` | bool | True | Regenerate `generated_user_rules.py` from final merged state. |
| `limit_backup_sets` | int | 20 | Keep only the most recent N backup sets (0 = no pruning). |

### Backup Layout
`saveimage_unimeta/user_rules/backups/<YYYYMMDD-HHMMSS>/`
Contains up to three files when present:
- user_captures.json
- user_samplers.json
- generated_user_rules.py

Atomic creation: write to temp dir then rename.

### Append Merge Semantics
Nodes:
- New node → add entirely
- Existing node → add missing metafields; replace only if `replace_conflicts=True`
Samplers:
- New sampler class → add full mapping
- Existing class → add missing roles; replace only if `replace_conflicts=True`

### Status Metrics (single-line summary)
`mode=append_new backup=created nodes_added=X metafields_added=Y metafields_replaced=Z sampler_roles_added=A sampler_roles_replaced=B skipped_conflicts=C pruned=M`

Restore status example:
`restored=20250926-152301 files=[user_captures.json,user_samplers.json,generated_user_rules.py] partial_missing=[]`

### Edge Cases
- Empty `nodes` + empty `samplers` → no writes; if overwrite: return `No changes` (still may create backup if enabled).
- Restore with partial set (missing one file) logs partial.
- `rebuild_python_rules=False` leaves existing extension untouched.
- Conflict with identical content treated as skipped (not replaced).

### Tests
1. Overwrite path creates files & backup.
2. Append without conflicts adds missing only.
3. Append with conflicts & replace_conflicts=True replaces entries.
4. Backup retention pruning (set limit to 1, create 2 backups → oldest removed).
5. Restore full set.
6. Restore partial set.
7. No-op append (status unchanged).
8. rebuild_python_rules=False keeps previous extension hash.

---
## 3. Directory Relocation (`py/` → `user_rules/`)

### Actions Performed (manual moves already staged outside code changes):
Moved:
- `saveimage_unimeta/py/user_captures.json` → `saveimage_unimeta/user_rules/user_captures.json`
- `saveimage_unimeta/py/user_samplers.json` → `saveimage_unimeta/user_rules/user_samplers.json`
- `saveimage_unimeta/user_captures_examples.json` → `saveimage_unimeta/user_rules/user_captures_examples.json`
- `saveimage_unimeta/user_samplers_example.json` → `saveimage_unimeta/user_rules/user_samplers_example.json`

### Required Code Updates
- In `defs/__init__.py` adjust `USER_CAPTURES_FILE` and `USER_SAMPLERS_FILE` to point to `user_rules/` instead of `py/`.
- In `rules_writer.py` adjust `PY_FILE_DIR` usage & path comments (rename variable to e.g. `USER_RULES_DIR`).
- Update tests referencing `py/user_captures.json` to `user_rules/user_captures.json`.
- README / docs: update paths wherever they mention `py/`.

### Backward Compatibility
If we want to support existing installations temporarily:
- On load: if `user_rules/` files missing, look for legacy `py/` files and (optionally) migrate them (move or copy then log a migration notice) once.
- Provide one-time INFO: `Migrated legacy user rule files from 'py/' to 'user_rules/'`.

### Migration Strategy
1. Implement dual-path detection for one release (prefer new dir).
2. After detection/migration, write a sentinel file `.migrated` in `user_rules/`.
3. Future release can drop legacy path fallback.

---
## 4. Open Questions (To Resolve Before Implementation)
- Do we want UTC timestamps (append 'Z')? (Default plan: local time, no Z.)
- Do we auto-migrate legacy `py/` files (recommended) vs hard break? (Recommended: soft migrate.)
- Max retention default acceptable at 20? (Yes unless changed.)
- Include JSON user rules in scanner missing-lens baseline? (Planned: yes, after extension load.)

---
## 5. Implementation Order
1. Directory path constant updates + migration shim.
2. Writer node new inputs + backup/restore logic.
3. Scanner toggle repurpose.
4. Tests adjusted + new tests added.
5. README / CHANGELOG update (Unreleased section).

---
## 6. Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Accidental data loss on overwrite | Default backup_before_save=True + timestamped sets. |
| UI confusion with new inputs | Concise tooltips; README table. |
| Large number of backups cluttering disk | Retention limit. |
| Scanner filter hides too much (user confusion) | Status counts + doc explaining lens. |
| Legacy path still referenced in user forks | Dual-path migration shim + log. |

---
## 7. Summary
This plan modernizes rule management with safe, auditable backups, a focused “what’s missing” scanner lens, and clearer directory semantics (`user_rules/`). Implementation ready once approved.
