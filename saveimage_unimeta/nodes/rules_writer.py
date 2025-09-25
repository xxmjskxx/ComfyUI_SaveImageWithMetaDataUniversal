"""Rules writer node (formerly in the monolithic node.py)."""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)


class SaveCustomMetadataRules:
    @classmethod
    def INPUT_TYPES(s):  # noqa: N802, N804
        return {"required": {"rules_json_string": ("STRING", {"multiline": True})}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "save_rules"
    CATEGORY = "SaveImageWithMetaDataUniversal/rules"
    DESCRIPTION = (
        "Saves custom metadata capture rules to user_captures.json and user_samplers.json, and generates a Python "
        "extension allowing imported nodes to have their 'field_name's and values written to metadata."
    )
    NODE_NAME = "Save Custom Metadata Rules"
    OUTPUT_NODE = True

    def save_rules(self, rules_json_string):
        # This path needs to be consistent with the loading paths.
        PY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # noqa: N806
        USER_CAPTURES_FILE = os.path.join(PY_DIR, "user_captures.json")  # noqa: N806
        USER_SAMPLERS_FILE = os.path.join(PY_DIR, "user_samplers.json")  # noqa: N806
        EXT_DIR = os.path.join(PY_DIR, "defs", "ext")  # noqa: N806
        os.makedirs(EXT_DIR, exist_ok=True)
        GENERATED_EXT_FILE = os.path.join(EXT_DIR, "generated_user_rules.py")  # noqa: N806

        saved_files: list[str] = []
        try:
            data = json.loads(rules_json_string)
            raw_nodes = data.get("nodes", {}) if isinstance(data.get("nodes"), dict) else {}
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
            if sanitized_nodes:
                with open(USER_CAPTURES_FILE, "w", encoding="utf-8") as f:
                    json.dump(sanitized_nodes, f, indent=4)
                saved_files.append("user_captures.json")
            if "samplers" in data and isinstance(data["samplers"], dict):
                with open(USER_SAMPLERS_FILE, "w", encoding="utf-8") as f:
                    json.dump(data["samplers"], f, indent=4)
                saved_files.append("user_samplers.json")

            # Additionally, emit a Python extension that wires up formatter callables
            # so that downstream loading can import functions (merge 1 path as well).
            try:
                nodes_dict = sanitized_nodes
                samplers_dict = data.get("samplers", {})
                # Build a simple Python module text
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
                # Common selectors from built-in extensions (wrapped for style)
                # Import shared selector and define minimal, self-contained wrappers
                # so this generated file does not depend on external extension modules.
                lines.append("from ..selectors import select_stack_by_prefix")
                lines.append("")
                lines.append("def get_lora_model_name_stack(node_id, obj, prompt, extra_data, outputs, input_data):")
                lines.append("    return select_stack_by_prefix(input_data, 'lora_name', counter_key='lora_count')")
                lines.append("")
                lines.append("def get_lora_model_hash_stack(node_id, obj, prompt, extra_data, outputs, input_data):")
                lines.append("    names = select_stack_by_prefix(input_data, 'lora_name', counter_key='lora_count')")
                lines.append("    return [calc_lora_hash(n, input_data) for n in names]")
                lines.append("")
                lines.append(
                    "def get_lora_strength_model_stack(node_id, obj, prompt, extra_data, outputs, input_data):"
                )
                lines.append("    # Mirrors Efficiency Nodes behavior: advanced mode switches to 'model_str'.")
                lines.append("    try:")
                lines.append("        if input_data[0].get('input_mode', [''])[0] == 'advanced':")
                lines.append(
                    "            return select_stack_by_prefix("
                    "input_data, 'model_str', counter_key='lora_count')"
                )
                lines.append("    except Exception:")
                lines.append("        pass")
                lines.append("    return select_stack_by_prefix(input_data, 'lora_wt', counter_key='lora_count')")
                lines.append("")
                lines.append(
                    "def get_lora_strength_clip_stack(node_id, obj, prompt, extra_data, outputs, input_data):"
                )
                lines.append("    # Mirrors Efficiency Nodes behavior: advanced mode uses 'clip_str'.")
                lines.append("    try:")
                lines.append("        if input_data[0].get('input_mode', [''])[0] == 'advanced':")
                lines.append(
                    "            return select_stack_by_prefix("
                    "input_data, 'clip_str', counter_key='lora_count')"
                )
                lines.append("    except Exception:")
                lines.append("        pass")
                lines.append("    return select_stack_by_prefix(input_data, 'lora_wt', counter_key='lora_count')")
                lines.append("")
                # A mapping of known callable names to actual objects
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
                # Ensure valid assignment syntax on a single statement
                lines.append("SAMPLERS = " + json.dumps(samplers_dict, indent=4))
                lines.append("")
                lines.append("CAPTURE_FIELD_LIST = {")
                # We need to render MetaField keys; write as MetaField.NAME
                for node_name, rules in nodes_dict.items():
                    lines.append("    " + json.dumps(node_name) + ": {")
                    for metafield_name, rule in rules.items():
                        # Convert function names to identifiers
                        rule_copy = dict(rule)
                        # Known callable fields: 'format'
                        if isinstance(rule_copy.get("format"), str):
                            rule_copy["format"] = rule_copy["format"]
                        # Known keys are field_name, fields, prefix, selector, validate, format
                        # Build the dict literal by hand to allow non-quoted callables
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

                with open(GENERATED_EXT_FILE, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
                saved_files.append("defs/ext/generated_user_rules.py")
            except Exception as gen_err:  # pragma: no cover - non-critical convenience path
                logger.warning(
                    "[Metadata Loader] Could not generate python ext from rules: %s",
                    gen_err,
                )
            if not saved_files:
                return ("No valid 'nodes' or 'samplers' sections found.",)
            return (f"Successfully saved: {', '.join(saved_files)}",)
        except Exception as e:
            raise ValueError(f"Error saving rules: {e}")
