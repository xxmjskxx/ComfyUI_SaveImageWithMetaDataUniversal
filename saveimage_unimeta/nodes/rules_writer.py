"""Rules writer node (formerly in the monolithic node.py)."""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from typing import Any

logger = logging.getLogger(__name__)


class SaveCustomMetadataRules:
    """Enhanced writer supporting overwrite/append, backups and restore.

    Flow summary:
      * Optional restore of a selected backup set (short-circuits other inputs except rebuild flag).
      * Normal save path can create a timestamped backup (set folder) before applying changes.
      * Two save modes: overwrite (legacy) and append_new (only add missing / optionally replace conflicts).
      * Deterministic python extension generation (sorted order) when requested.
    """

    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802, N804
        # Dynamic enumeration of backup sets each time the UI queries node spec.
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        user_rules_dir = os.path.join(base_dir, "user_rules")
        backups_root = os.path.join(user_rules_dir, "backups")
        backup_choices = ["none"]
        if os.path.isdir(backups_root):
            try:
                for entry in os.listdir(backups_root):
                    full = os.path.join(backups_root, entry)
                    if os.path.isdir(full) and _looks_like_timestamp(entry):
                        backup_choices.append(entry)
            except OSError:
                pass
        # Sort newest first after 'none'
        if len(backup_choices) > 1:
            head, tail = backup_choices[0], backup_choices[1:]
            backup_choices = [head] + sorted(tail, reverse=True)

        return {
            "required": {
                "rules_json_string": (
                    "STRING",
                    {
                        "multiline": True,
                        "tooltip": (
                            "Paste JSON from 'Metadata Rule Scanner'. Keep top-level keys: 'nodes' and 'samplers'.\n"
                            "Nodes: { 'NodeClass': { 'MetaFieldName': { rule... } } }\n"
                            "Rule keys: field_name|fields|prefix|selector|validate|format (ignore 'status').\n"
                            "Samplers: { 'SamplerNode': { 'role': 'input_name' } }. Don't rename metafield constants."
                        ),
                    },
                ),
            },
            "optional": {
                "save_mode": (
                    "STRING",
                    {
                        "default": "overwrite",
                        "choices": ("overwrite", "append_new"),
                        "tooltip": (
                            "overwrite: replace existing user JSON with provided content (legacy).\n"
                            "append_new: add only missing metafields / sampler roles."
                        ),
                    },
                ),
                "backup_before_save": (
                    "BOOLEAN",
                    {"default": True, "tooltip": "Create a timestamped backup set before applying changes."},
                ),
                # Use enum-style tuple for dropdown instead of plain STRING so UI shows selection list
                "restore_backup_set": (
                    tuple(backup_choices),
                    {
                        "default": "none",
                        "tooltip": (
                            "Restore a previous backup set.\n"
                            "If not 'none', other inputs (except rebuild_python_rules) are ignored."
                        ),
                    },
                ),
                "replace_conflicts": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "append_new mode only. If True, conflicting metafields / sampler roles\n"
                            "are replaced by incoming definitions; otherwise they are kept and counted as skipped."
                        ),
                    },
                ),
                "rebuild_python_rules": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": (
                            "Generate defs/ext/generated_user_rules.py reflecting the resulting JSON.\n"
                            "Disable to only adjust JSON (faster when iterating)."
                        ),
                    },
                ),
                "limit_backup_sets": (
                    "INT",
                    {
                        "default": 20,
                        "min": 0,
                        "max": 500,
                        "step": 1,
                        "tooltip": (
                            "Retention for timestamped backup sets. 0 = no pruning.\n"
                            "After creating a new backup, oldest sets beyond this count are deleted."
                        ),
                    },
                ),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "save_rules"
    CATEGORY = "SaveImageWithMetaDataUniversal/rules"
    DESCRIPTION = (
        "Manage custom metadata capture rules: overwrite or append + backups + restore."
    )
    NODE_NAME = "Save Custom Metadata Rules"
    OUTPUT_NODE = True

    def save_rules(
        self,
        rules_json_string: str,
        save_mode: str = "overwrite",
        backup_before_save: bool = True,
        restore_backup_set: str = "none",
        replace_conflicts: bool = False,
        rebuild_python_rules: bool = True,
        limit_backup_sets: int = 20,
    ) -> tuple[str]:  # noqa: D401
        # Path constants (shared with loader semantics)
        PY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # noqa: N806
        # Test isolation parity with loader: if METADATA_TEST_MODE and an existing
        # tests/_test_outputs/user_rules directory is present, prefer it so writer output
        # does not pollute real tree. (Do not auto-create to avoid unintended
        # divergence from loader semantics which only prefers when it already exists.)
        test_mode = os.environ.get("METADATA_TEST_MODE", "").strip().lower() in {"1", "true", "yes", "on"}
        preferred_test_dir = os.path.join(PY_DIR, "tests/_test_outputs", "user_rules")
        if test_mode and os.path.isdir(preferred_test_dir):
            USER_RULES_DIR = preferred_test_dir  # noqa: N806
        else:
            USER_RULES_DIR = os.path.join(PY_DIR, "user_rules")  # noqa: N806
        os.makedirs(USER_RULES_DIR, exist_ok=True)
        USER_CAPTURES_FILE = os.path.join(USER_RULES_DIR, "user_captures.json")  # noqa: N806
        USER_SAMPLERS_FILE = os.path.join(USER_RULES_DIR, "user_samplers.json")  # noqa: N806
        EXT_DIR = os.path.join(PY_DIR, "defs", "ext")  # noqa: N806
        os.makedirs(EXT_DIR, exist_ok=True)
        GENERATED_EXT_FILE = os.path.join(EXT_DIR, "generated_user_rules.py")  # noqa: N806
        BACKUPS_ROOT = os.path.join(USER_RULES_DIR, "backups")  # noqa: N806
        os.makedirs(BACKUPS_ROOT, exist_ok=True)
        metrics: dict[str, Any] = {
            "mode": save_mode,
            "backup": None,
            "nodes_added": 0,
            "metafields_added": 0,
            "metafields_replaced": 0,
            "metafields_skipped_conflict": 0,
            "samplers_added": 0,
            "sampler_roles_added": 0,
            "sampler_roles_replaced": 0,
            "sampler_roles_skipped_conflict": 0,
            "pruned": 0,
            "unchanged": False,
            "restored": False,
            "partial": False,
        }

        try:
            # Restore path short-circuit
            if restore_backup_set and restore_backup_set != "none":
                pre_ts = _timestamp()
                created_dir = self._create_backup(
                    BACKUPS_ROOT, pre_ts, USER_CAPTURES_FILE, USER_SAMPLERS_FILE, GENERATED_EXT_FILE
                )
                if created_dir:
                    logger.info(
                        "[Metadata Loader] Created backup %s before restoring %s.", pre_ts, restore_backup_set
                    )
                metrics["restored"] = True
                target_dir = os.path.join(BACKUPS_ROOT, restore_backup_set)
                if not os.path.isdir(target_dir):
                    return (f"Restore failed: set {restore_backup_set} not found.",)
                missing: list[str] = []
                restored_files: list[str] = []
                for fname, dest in [
                    ("user_captures.json", USER_CAPTURES_FILE),
                    ("user_samplers.json", USER_SAMPLERS_FILE),
                ]:
                    src = os.path.join(target_dir, fname)
                    if os.path.exists(src):
                        shutil.copy2(src, dest)
                        restored_files.append(fname)
                    else:
                        missing.append(fname)
                ext_src = os.path.join(target_dir, "generated_user_rules.py")
                if rebuild_python_rules:
                    if os.path.exists(ext_src):
                        shutil.copy2(ext_src, GENERATED_EXT_FILE)
                        restored_files.append("generated_user_rules.py")
                    else:
                        try:
                            self._generate_python_extension(
                                GENERATED_EXT_FILE,
                                self._safe_load_json(USER_CAPTURES_FILE),
                                self._safe_load_json(USER_SAMPLERS_FILE),
                            )
                            restored_files.append("generated_user_rules.py (regenerated)")
                        except Exception as regen_err:  # pragma: no cover
                            logger.warning(
                                "[Metadata Loader] Could not regenerate extension after restore: %s", regen_err
                            )
                if missing:
                    metrics["partial"] = True
                status = f"Restored backup {restore_backup_set} (files: {', '.join(restored_files) or 'none'})"
                if missing:
                    status += f" [partial missing: {', '.join(missing)}]"
                return (status,)

            data = json.loads(rules_json_string)
            raw_nodes = data.get("nodes", {}) if isinstance(data.get("nodes"), dict) else {}
            samplers_in = data.get("samplers", {}) if isinstance(data.get("samplers"), dict) else {}

            sanitized_nodes: dict[str, dict] = {}
            for node_name, meta_map in raw_nodes.items():
                if not isinstance(meta_map, dict):
                    continue
                cleaned = {}
                for mf_name, rule in meta_map.items():
                    if isinstance(rule, dict):
                        r2 = {k: v for k, v in rule.items() if k != "status"}
                        cleaned[mf_name] = r2
                    else:
                        cleaned[mf_name] = rule
                sanitized_nodes[node_name] = cleaned

            if backup_before_save:
                ts = _timestamp()
                if self._create_backup(
                    BACKUPS_ROOT, ts, USER_CAPTURES_FILE, USER_SAMPLERS_FILE, GENERATED_EXT_FILE
                ):
                    metrics["backup"] = ts
                    if limit_backup_sets and limit_backup_sets > 0:
                        metrics["pruned"] = self._prune_backups(BACKUPS_ROOT, limit_backup_sets)
                else:
                    metrics["backup"] = "skipped-empty"
            else:
                metrics["backup"] = "disabled"

            existing_nodes = self._safe_load_json(USER_CAPTURES_FILE) or {}
            if not isinstance(existing_nodes, dict):
                existing_nodes = {}
            existing_samplers = self._safe_load_json(USER_SAMPLERS_FILE) or {}
            if not isinstance(existing_samplers, dict):
                existing_samplers = {}

            if save_mode == "overwrite":
                saved_files: list[str] = []
                if sanitized_nodes:
                    with open(USER_CAPTURES_FILE, "w", encoding="utf-8") as f:
                        json.dump(sanitized_nodes, f, indent=4)
                    saved_files.append("user_captures.json")
                if samplers_in:
                    with open(USER_SAMPLERS_FILE, "w", encoding="utf-8") as f:
                        json.dump(samplers_in, f, indent=4)
                    saved_files.append("user_samplers.json")
                final_nodes = sanitized_nodes
                final_samplers = samplers_in
            else:
                (final_nodes, final_samplers) = self._merge_append_new(
                    existing_nodes,
                    existing_samplers,
                    sanitized_nodes,
                    samplers_in,
                    replace_conflicts,
                    metrics,
                )
                if not metrics["unchanged"]:
                    with open(USER_CAPTURES_FILE, "w", encoding="utf-8") as f:
                        json.dump(final_nodes, f, indent=4)
                    with open(USER_SAMPLERS_FILE, "w", encoding="utf-8") as f:
                        json.dump(final_samplers, f, indent=4)

            if rebuild_python_rules:
                try:
                    self._generate_python_extension(GENERATED_EXT_FILE, final_nodes, final_samplers)
                except Exception as gen_err:  # pragma: no cover
                    logger.warning(
                        "[Metadata Loader] Could not generate python ext from rules: %s", gen_err
                    )

            self._warn_uninstalled_nodes(list(sanitized_nodes.keys()))

            if save_mode == "overwrite":
                if not sanitized_nodes and not samplers_in:
                    return ("No valid 'nodes' or 'samplers' sections found.",)
                status = [
                    "mode=overwrite",
                    f"backup={metrics['backup']}",
                    f"pruned={metrics['pruned']}",
                    f"nodes={len(final_nodes)}",
                    f"samplers={len(final_samplers)}",
                ]
                return ("; ".join(status),)
            else:
                status = [
                    "mode=append_new",
                    f"backup={metrics['backup']}",
                    f"pruned={metrics['pruned']}",
                ]
                if metrics["unchanged"]:
                    status.append("unchanged=True")
                else:
                    status.extend(
                        [
                            f"nodes_added={metrics['nodes_added']}",
                            f"metafields_added={metrics['metafields_added']}",
                            f"metafields_replaced={metrics['metafields_replaced']}",
                            f"metafields_skipped={metrics['metafields_skipped_conflict']}",
                            f"samplers_added={metrics['samplers_added']}",
                            f"sampler_roles_added={metrics['sampler_roles_added']}",
                            f"sampler_roles_replaced={metrics['sampler_roles_replaced']}",
                            f"sampler_roles_skipped={metrics['sampler_roles_skipped_conflict']}",
                        ]
                    )
                return ("; ".join(status),)
        except Exception as e:  # pragma: no cover
            raise ValueError(f"Error saving rules: {e}")

    # -------------------------- Internal helpers -------------------------- #

    @staticmethod
    def _create_backup(
        backups_root: str,
        timestamp: str,
        captures_path: str,
        samplers_path: str,
        ext_path: str,
    ) -> str | None:
        """Create a backup set directory containing any existing rule files.

        Returns the directory name (timestamp) if at least one file was copied, else None.
        """
        target_dir = os.path.join(backups_root, timestamp)
        if os.path.exists(target_dir):
            # Rare collision – add numeric suffix
            i = 1
            while os.path.exists(f"{target_dir}-{i}"):
                i += 1
            target_dir = f"{target_dir}-{i}"
        os.makedirs(target_dir, exist_ok=True)
        copied = 0
        for p in (captures_path, samplers_path, ext_path):
            if os.path.exists(p):
                try:
                    shutil.copy2(p, os.path.join(target_dir, os.path.basename(p)))
                    copied += 1
                except OSError as copy_err:  # pragma: no cover
                    logger.warning("[Metadata Loader] Failed backing up %s: %s", p, copy_err)
        if copied == 0:
            # Remove empty directory for cleanliness
            try:
                os.rmdir(target_dir)
            except OSError:
                pass
            return None
        return os.path.basename(target_dir)

    @staticmethod
    def _prune_backups(backups_root: str, limit: int) -> int:
        if limit <= 0:
            return 0
        try:
            entries = [e for e in os.listdir(backups_root) if os.path.isdir(os.path.join(backups_root, e))]
        except OSError:
            return 0
        # Filter to timestamp-like
        entries = [e for e in entries if _looks_like_timestamp(e)]
        if len(entries) <= limit:
            return 0
        entries_sorted = sorted(entries, reverse=True)  # newest first
        to_delete = entries_sorted[limit:]
        pruned = 0
        for e in to_delete:
            full = os.path.join(backups_root, e)
            try:
                shutil.rmtree(full)
                pruned += 1
            except OSError:  # pragma: no cover
                logger.warning("[Metadata Loader] Failed pruning backup set %s", e)
        return pruned

    @staticmethod
    def _safe_load_json(path: str):
        try:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:  # pragma: no cover
            logger.warning("[Metadata Loader] Failed loading JSON %s: %s", path, e)
        return None

    def _merge_append_new(
        self,
        existing_nodes: dict[str, Any],
        existing_samplers: dict[str, Any],
        incoming_nodes: dict[str, Any],
        incoming_samplers: dict[str, Any],
        replace_conflicts: bool,
        metrics: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        nodes_out = json.loads(json.dumps(existing_nodes))  # deep-ish copy
        samplers_out = json.loads(json.dumps(existing_samplers))

        # Track changes
        changed = False

        # Merge nodes/metafields
        for node_name, metafields in incoming_nodes.items():
            if node_name not in nodes_out:
                nodes_out[node_name] = metafields
                metrics["nodes_added"] += 1
                metrics["metafields_added"] += len(metafields)
                changed = True
                continue
            # Existing node: add new metafields or handle conflicts
            for mf_name, rule in metafields.items():
                if mf_name not in nodes_out[node_name]:
                    nodes_out[node_name][mf_name] = rule
                    metrics["metafields_added"] += 1
                    changed = True
                else:
                    if replace_conflicts:
                        nodes_out[node_name][mf_name] = rule
                        metrics["metafields_replaced"] += 1
                        changed = True
                    else:
                        metrics["metafields_skipped_conflict"] += 1

        # Merge samplers / roles
        for sampler_name, roles in incoming_samplers.items():
            existing_roles = samplers_out.get(sampler_name)
            if not isinstance(roles, dict):  # skip invalid mapping
                continue
            if not isinstance(existing_roles, dict):
                samplers_out[sampler_name] = roles
                metrics["samplers_added"] += 1
                metrics["sampler_roles_added"] += len(roles)
                changed = True
                continue
            for role, val in roles.items():
                if role not in existing_roles:
                    existing_roles[role] = val
                    metrics["sampler_roles_added"] += 1
                    changed = True
                else:
                    if replace_conflicts:
                        existing_roles[role] = val
                        metrics["sampler_roles_replaced"] += 1
                        changed = True
                    else:
                        metrics["sampler_roles_skipped_conflict"] += 1

        if not changed:
            metrics["unchanged"] = True
        return nodes_out, samplers_out

    @staticmethod
    def _generate_python_extension(path: str, nodes_dict: dict[str, Any], samplers_dict: dict[str, Any]) -> None:
        # Build deterministic Python module similar to legacy builder but sorted
        lines: list[str] = []
        lines.append("from ..meta import MetaField")
        lines.append(
            "from ..formatters import (\n"
            "    calc_model_hash, calc_vae_hash, calc_lora_hash, calc_unet_hash,\n"
            "    convert_skip_clip, get_scaled_width, get_scaled_height,\n"
            "    extract_embedding_names, extract_embedding_hashes\n"
            ")"
        )
        lines.append(
            "from ..validators import (\n"
            "    is_positive_prompt, is_negative_prompt\n"
            ")"
        )
        lines.append("from ..selectors import select_stack_by_prefix")
        lines.append("")
        lines.append("def _is_advanced_mode(input_data):")
        lines.append("    try:")
        lines.append(
            "        return (isinstance(input_data, list) and input_data and isinstance(input_data[0], dict) and "
            "isinstance(input_data[0].get('input_mode'), list) and input_data[0]['input_mode'] and "
            "input_data[0]['input_mode'][0] == 'advanced')"
        )
        lines.append("    except Exception:")
        lines.append("        return False")
        lines.append("")
        lines.append("def get_lora_model_name_stack(node_id, obj, prompt, extra_data, outputs, input_data):")
        lines.append("    return select_stack_by_prefix(input_data, 'lora_name', counter_key='lora_count')")
        lines.append("")
        lines.append("def get_lora_model_hash_stack(node_id, obj, prompt, extra_data, outputs, input_data):")
        lines.append("    names = select_stack_by_prefix(input_data, 'lora_name', counter_key='lora_count')")
        lines.append("    return [calc_lora_hash(n, input_data) for n in names]")
        lines.append("")
        lines.append("def get_lora_strength_model_stack(node_id, obj, prompt, extra_data, outputs, input_data):")
        lines.append("    if _is_advanced_mode(input_data):")
        lines.append("        return select_stack_by_prefix(input_data, 'model_str', counter_key='lora_count')")
        lines.append("    return select_stack_by_prefix(input_data, 'lora_wt', counter_key='lora_count')")
        lines.append("")
        lines.append("def get_lora_strength_clip_stack(node_id, obj, prompt, extra_data, outputs, input_data):")
        lines.append("    if _is_advanced_mode(input_data):")
        lines.append("        return select_stack_by_prefix(input_data, 'clip_str', counter_key='lora_count')")
        lines.append("    return select_stack_by_prefix(input_data, 'lora_wt', counter_key='lora_count')")
        lines.append("")
        lines.append("KNOWN = {")
        lines.append("    'calc_model_hash': calc_model_hash,")
        lines.append("    'calc_vae_hash': calc_vae_hash,")
        lines.append("    'calc_lora_hash': calc_lora_hash,")
        lines.append("    'calc_unet_hash': calc_unet_hash,")
        lines.append("    'convert_skip_clip': convert_skip_clip,")
        lines.append("    'get_scaled_width': get_scaled_width,")
        lines.append("    'get_scaled_height': get_scaled_height,")
        lines.append("    'extract_embedding_names': extract_embedding_names,")
        lines.append("    'extract_embedding_hashes': extract_embedding_hashes,")
        lines.append("    'is_positive_prompt': is_positive_prompt,")
        lines.append("    'is_negative_prompt': is_negative_prompt,")
        lines.append("    'get_lora_model_name_stack': get_lora_model_name_stack,")
        lines.append("    'get_lora_model_hash_stack': get_lora_model_hash_stack,")
        lines.append("    'get_lora_strength_model_stack': get_lora_strength_model_stack,")
        lines.append("    'get_lora_strength_clip_stack': get_lora_strength_clip_stack,")
        lines.append("}")
        lines.append("")
        lines.append("SAMPLERS = " + json.dumps(samplers_dict, indent=4))
        lines.append("")
        lines.append("CAPTURE_FIELD_LIST = {")
        for node_name in sorted(nodes_dict.keys()):
            rules = nodes_dict[node_name]
            lines.append("    " + json.dumps(node_name) + ": {")
            for metafield_name in sorted(rules.keys()):
                rule = rules[metafield_name]
                rule_copy = dict(rule)
                body_parts: list[str] = []
                if "field_name" in rule_copy:
                    body_parts.append(f"'field_name': {json.dumps(rule_copy['field_name'])}")
                if "fields" in rule_copy and isinstance(rule_copy.get("fields"), list | tuple):
                    body_parts.append(f"'fields': {json.dumps(rule_copy['fields'])}")
                if "prefix" in rule_copy:
                    body_parts.append(f"'prefix': {json.dumps(rule_copy['prefix'])}")
                if "selector" in rule_copy:
                    sel = rule_copy["selector"]
                    if isinstance(sel, str):
                        body_parts.append("'selector': KNOWN[" + json.dumps(sel) + "]")
                    else:
                        body_parts.append(f"'selector': {json.dumps(sel)}")
                if "validate" in rule_copy:
                    val = rule_copy["validate"]
                    if isinstance(val, str):
                        body_parts.append("'validate': KNOWN[" + json.dumps(val) + "]")
                    else:
                        body_parts.append(f"'validate': {json.dumps(val)}")
                if "format" in rule_copy:
                    fmt = rule_copy["format"]
                    if isinstance(fmt, str):
                        body_parts.append("'format': KNOWN[" + json.dumps(fmt) + "]")
                    else:
                        body_parts.append(f"'format': {json.dumps(fmt)}")
                body = ", ".join(body_parts)
                lines.append(f"        MetaField.{metafield_name}: {{" + body + "},")
            lines.append("    },")
        lines.append("}")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _warn_uninstalled_nodes(node_names):  # best-effort detection
        try:
            from nodes import NODE_CLASS_MAPPINGS  # type: ignore
            missing = [n for n in node_names if n not in NODE_CLASS_MAPPINGS]
            if missing:
                logger.warning(
                    "[Metadata Loader] The following node classes are not installed and were ignored: %s",
                    missing,
                )
        except Exception:  # pragma: no cover - environment dependent
            pass


def _timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.localtime())
_TIMESTAMP_BASE_LENGTH = 15  # len('YYYYMMDD-HHMMSS')

def _looks_like_timestamp(name: str) -> bool:
    """Return True for 'YYYYMMDD-HHMMSS' optionally followed by '-N' numeric suffix.

    Examples:
      20250101-123045 -> True
      20250101-123045-1 -> True
      20250101-1230 -> False (too short)
    """
    if len(name) < _TIMESTAMP_BASE_LENGTH:
        return False
    base = name[:_TIMESTAMP_BASE_LENGTH]
    try:
        time.strptime(base, "%Y%m%d-%H%M%S")
    except ValueError:
        return False
    # Allow optional -N suffix after the validated base
    if len(name) == _TIMESTAMP_BASE_LENGTH:
        return True
    if name[_TIMESTAMP_BASE_LENGTH] != "-":  # next char must be '-'
        return False
    suffix = name[_TIMESTAMP_BASE_LENGTH + 1 :]
    return suffix.isdigit() and len(suffix) > 0
