"""A ComfyUI node for saving and managing custom metadata rules.

This module provides the `SaveCustomMetadataRules` class, which is a ComfyUI
node that allows users to save, back up, and restore their custom metadata
capture rules. It supports both overwriting and appending to existing rule
files. Rules are stored as JSON data only.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from typing import Any

from .. import defs as defs_mod
from ..version import resolve_runtime_version

logger = logging.getLogger(__name__)


class SaveCustomMetadataRules:
    """A node for managing metadata rules with overwrite/append, backup and restore functionality.

    This class provides a comprehensive solution for managing user-defined
    metadata rules. It allows for saving in overwrite or append mode, creating
    timestamped backups, restoring from backups, and pruning old backups.
    Flow summary:
      * Optional restore of a selected backup set (short-circuits other inputs).
      * Normal save path can create a timestamped backup (set folder) before applying changes.
      * Two save modes: overwrite (legacy) and append_new (only add missing / optionally replace conflicts).
    """

    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802
        """Define the input types for the `SaveCustomMetadataRules` node.

        This method dynamically enumerates available backup sets to populate the
        `restore_backup_set` dropdown. It defines inputs for the rules JSON,
        save mode, backup options, and other settings.

        Returns:
            dict: A dictionary defining the input schema for the node.
        """
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
                pass  # Backups directory may not exist or be inaccessible - continue without it
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
                    ("overwrite", "append_new"),
                    {
                        "default": "overwrite",
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
                            "If not 'none', other inputs are ignored."
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
                        "tooltip": "Deprecated, no effect. Rules are stored and loaded as JSON only.",
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
    DESCRIPTION = "Manage custom metadata capture rules: overwrite or append + backups + restore."
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
    ) -> tuple[str]:
        """Save, restore, or manage metadata rules.

        This method is the main entry point for the node's functionality. It
        handles the logic for restoring from a backup, saving rules in
        different modes, and stamping the rules version.

        Args:
            rules_json_string (str): The JSON string containing the metadata rules.
            save_mode (str, optional): The save mode ('overwrite' or 'append_new').
                Defaults to "overwrite".
            backup_before_save (bool, optional): Whether to create a backup before
                saving. Defaults to True.
            restore_backup_set (str, optional): The name of the backup set to
                restore. Defaults to "none".
            replace_conflicts (bool, optional): Whether to replace conflicting
                entries when appending. Defaults to False.
            rebuild_python_rules (bool, optional): Deprecated and ignored; kept so
                saved workflows keep their widget order.
            limit_backup_sets (int, optional): The maximum number of backup sets
                to retain. Defaults to 20.

        Returns:
            tuple[str]: A tuple containing a status message.

        Raises:
            ValueError: If an error occurs during the saving process.
        """
        # Path constants (shared with loader semantics). Delegate to the loader's
        # resolver so the writer, loader, and scanner stay in lockstep for both
        # the production (<package>/user_rules) and test-isolated
        # (<repo>/tests/_test_outputs/user_rules) locations.
        USER_RULES_DIR = defs_mod.resolve_user_rules_dir()  # noqa: N806
        os.makedirs(USER_RULES_DIR, exist_ok=True)
        USER_CAPTURES_FILE = os.path.join(USER_RULES_DIR, "user_captures.json")  # noqa: N806
        USER_SAMPLERS_FILE = os.path.join(USER_RULES_DIR, "user_samplers.json")  # noqa: N806
        RULES_VERSION_FILE = os.path.join(USER_RULES_DIR, "rules_version.json")  # noqa: N806
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
                    BACKUPS_ROOT, pre_ts, USER_CAPTURES_FILE, USER_SAMPLERS_FILE, RULES_VERSION_FILE
                )
                if created_dir:
                    logger.info("[Metadata Loader] Created backup %s before restoring %s.", pre_ts, restore_backup_set)
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
                # Older backup sets have no version stamp; drop the current one so the
                # restored rules are reported as unversioned rather than current.
                version_src = os.path.join(target_dir, "rules_version.json")
                if os.path.exists(version_src):
                    shutil.copy2(version_src, RULES_VERSION_FILE)
                elif os.path.exists(RULES_VERSION_FILE):
                    os.remove(RULES_VERSION_FILE)
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
                if self._create_backup(BACKUPS_ROOT, ts, USER_CAPTURES_FILE, USER_SAMPLERS_FILE, RULES_VERSION_FILE):
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

            with open(RULES_VERSION_FILE, "w", encoding="utf-8") as f:
                json.dump({"rules_version": resolve_runtime_version()}, f)

            self._warn_uninstalled_nodes(list(sanitized_nodes.keys()))

            if save_mode == "overwrite":
                if not sanitized_nodes and not samplers_in:
                    return ("No valid 'nodes' or 'samplers' sections found.",)
                status_parts = [
                    "mode=overwrite",
                    f"backup={metrics['backup']}",
                    f"pruned={metrics['pruned']}",
                    f"nodes={len(final_nodes)}",
                    f"samplers={len(final_samplers)}",
                ]
                return ("; ".join(status_parts),)
            else:
                status_parts = [
                    "mode=append_new",
                    f"backup={metrics['backup']}",
                    f"pruned={metrics['pruned']}",
                ]
                if metrics["unchanged"]:
                    status_parts.append("unchanged=True")
                else:
                    status_parts.extend(
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
                return ("; ".join(status_parts),)
        except Exception as e:  # pragma: no cover
            raise ValueError(f"Error saving rules: {e}")

    # -------------------------- Internal helpers -------------------------- #

    @staticmethod
    def _create_backup(
        backups_root: str,
        timestamp: str,
        captures_path: str,
        samplers_path: str,
        version_path: str,
    ) -> str | None:
        """Create a backup of the current rules files.

        This method creates a timestamped directory and copies the existing
        `user_captures.json`, `user_samplers.json`, and `rules_version.json`
        files into it.

        Args:
            backups_root (str): The root directory for backups.
            timestamp (str): The timestamp to use for the backup directory name.
            captures_path (str): The path to the `user_captures.json` file.
            samplers_path (str): The path to the `user_samplers.json` file.
            version_path (str): The path to the `rules_version.json` file.

        Returns:
            str | None: The name of the created backup directory, or None if no
                files were backed up.
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
        for p in (captures_path, samplers_path, version_path):
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
                pass  # Directory may not be empty or removable - not critical
            return None
        return os.path.basename(target_dir)

    @staticmethod
    def _prune_backups(backups_root: str, limit: int) -> int:
        """Remove old backup sets to enforce the retention limit.

        This method deletes the oldest backup sets if the total number of
        backups exceeds the specified limit.

        Args:
            backups_root (str): The root directory for backups.
            limit (int): The maximum number of backup sets to retain.

        Returns:
            int: The number of pruned backup sets.
        """
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
        """Load a JSON file, returning None on failure.

        This method provides a safe way to load a JSON file, handling
        exceptions such as file not found or invalid JSON format.

        Args:
            path (str): The path to the JSON file.

        Returns:
            The loaded JSON data, or None if an error occurred.
        """
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
        """Merge new rules into existing ones.

        This method implements the 'append_new' save mode, merging new node
        and sampler rules into the existing ones. It handles conflicts based
        on the `replace_conflicts` flag and updates the metrics dictionary.

        Args:
            existing_nodes (dict[str, Any]): The existing node rules.
            existing_samplers (dict[str, Any]): The existing sampler rules.
            incoming_nodes (dict[str, Any]): The new node rules to merge.
            incoming_samplers (dict[str, Any]): The new sampler rules to merge.
            replace_conflicts (bool): Whether to replace conflicting entries.
            metrics (dict[str, Any]): A dictionary to store metrics about the merge.

        Returns:
            tuple[dict[str, Any], dict[str, Any]]: A tuple containing the
                merged node and sampler rules.
        """
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
    def _warn_uninstalled_nodes(node_names):  # best-effort detection
        """Log a warning for any node classes that are not currently installed.

        This method checks the provided list of node names against the installed
        nodes in ComfyUI and logs a warning if any are missing.

        Args:
            node_names (list[str]): A list of node class names to check.
        """
        try:
            from nodes import NODE_CLASS_MAPPINGS

            missing = [n for n in node_names if n not in NODE_CLASS_MAPPINGS]
            if missing:
                logger.warning(
                    "[Metadata Loader] The following node classes are not installed and were ignored: %s",
                    missing,
                )
        except Exception:  # pragma: no cover - environment dependent
            pass


def _timestamp() -> str:
    """Generate a timestamp string in the format YYYYMMDD-HHMMSS.

    Returns:
        str: The formatted timestamp string.
    """
    return time.strftime("%Y%m%d-%H%M%S", time.localtime())


_TIMESTAMP_BASE_LENGTH = 15  # len('YYYYMMDD-HHMMSS')


def _looks_like_timestamp(name: str) -> bool:
    """Check if a string resembles a timestamp.

    This function checks if a string is in the format 'YYYYMMDD-HHMMSS' or
    'YYYYMMDD-HHMMSS-N', where N is a number.

    Args:
        name (str): The string to check.

    Returns:
        bool: True if the string looks like a timestamp, False otherwise.
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
