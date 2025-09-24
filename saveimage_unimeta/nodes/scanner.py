"""MetadataRuleScanner node: scans installed nodes and suggests capture rules.

This module was extracted from the legacy monolithic node.py to improve maintainability.
"""
import json
import logging
import os

import nodes
from ..utils.color import cstr
from ..defs.captures import CAPTURE_FIELD_LIST
from ..defs.samplers import SAMPLERS
from ..defs.meta import MetaField

logger = logging.getLogger(__name__)
_DEBUG_VERBOSE = os.environ.get("METADATA_DEBUG", "0") not in ("0", "false", "False", None, "")


HEURISTIC_RULES = [
    {
        "metafield": MetaField.MODEL_NAME,
        "keywords": ("ckpt_name", "base_ckpt_name", "checkpoint", "ckpt"),
        "format": "calc_model_hash",
        "hash_field": MetaField.MODEL_HASH,
        "required_class_keywords": [
            "loader",
            "load",
            "select",
            "selector",
            "ByteDanceSeedreamNode",
        ],
        "excluded_class_keywords": ["lora"],
    },
    {
        "metafield": MetaField.MODEL_NAME,
        "keywords": ("unet_name", "model_name", "model"),
        "format": "calc_unet_hash",
        "hash_field": MetaField.MODEL_HASH,
        "required_class_keywords": ["loader", "load", "select", "selector"],
        "excluded_class_keywords": ["lora"],
    },
    {
        "metafield": MetaField.VAE_NAME,
        "keywords": ("vae_name", "vae"),
        "format": "calc_vae_hash",
        "hash_field": MetaField.VAE_HASH,
        "required_class_keywords": ["loader", "vae", "load"],
        "excluded_class_keywords": ["encode", "decode"],
        "exact_only": True,
    },
    {
        "metafield": MetaField.CLIP_MODEL_NAME,
        "keywords": ("clip_name", "clip_name1", "clip_name2", "clip_name3"),
        "is_multi": True,
        "required_class_regex": [
            r"load\s*.*\s*clip",
        ],
        "required_class_keywords": ["clip loader", "load clip", "cliploader"],
        "sort_numeric": True,
    },
    {
        "metafield": MetaField.POSITIVE_PROMPT,
        "keywords": (
            "prompt",
            "text",
            "positive_prompt",
            "t5xxl",
            "clip_l",
            "prompt_positive",
            "text_positive",
            "positive",
            "positive_g",
            "positive_l",
            "text_g",
            "text_l",
            "conditioning.positive",
        ),
        "validate": "is_positive_prompt",
        "required_context": ["clip"],
        "required_class_keywords": [
            "encode",
            "prompt",
            "positive",
            "ByteDanceSeedreamNode",
        ],
    },
    {
        "metafield": MetaField.NEGATIVE_PROMPT,
        "keywords": (
            "prompt",
            "text",
            "negative_prompt",
            "prompt_negative",
            "text_negative",
            "negative",
            "t5xxl",
            "clip_l",
            "negative_g",
            "negative_l",
            "conditioning.negative",
        ),
        "validate": "is_negative_prompt",
        "required_context": ["clip"],
        "required_class_keywords": ["encode", "prompt", "negative"],
    },
    {
        "metafield": MetaField.SEED,
        "keywords": ("seed", "noise_seed", "random_seed"),
        "required_class_keywords": ["sampler", "seed", "ByteDanceSeedreamNode"],
        "type": ("INT"),
    },
    {
        "metafield": MetaField.STEPS,
        "keywords": ("steps",),
        "required_context": ("seed", "cfg", "denoise", "scheduler"),
        "required_class_keywords": ["sampler", "scheduler", "steps"],
        "type": ("INT"),
    },
    {
        "metafield": MetaField.CFG,
        "keywords": ("cfg", "cfg_scale"),
        "required_class_keywords": ["sampler", "cfg"],
        "type": ("FLOAT"),
    },
    {
        "metafield": MetaField.GUIDANCE,
        "keywords": ("guidance",),
        "required_class_keywords": ["sampler", "guidance", "clip", "encode"],
        "excluded_keywords": ("cfg",),
        "type": ("FLOAT"),
    },
    {
        "metafield": MetaField.SAMPLER_NAME,
        "keywords": ("sampler_name", "sampler", "sampler_mode"),
        "required_class_keywords": ["sampler"],
    },
    {
        "metafield": MetaField.SCHEDULER,
        "keywords": ("scheduler", "scheduler_name"),
        "required_class_keywords": ["sampler", "scheduler", "sigmas"],
    },
    {
        "metafield": MetaField.DENOISE,
        "keywords": ("denoise",),
        "required_class_keywords": ["sampler", "scheduler"],
        "type": ("FLOAT"),
    },
    {
        "metafield": MetaField.MAX_SHIFT,
        "keywords": ("max_shift",),
        "required_class_keywords": ["ModelSampling"],
        "type": ("FLOAT"),
    },
    {
        "metafield": MetaField.BASE_SHIFT,
        "keywords": ("base_shift",),
        "required_class_keywords": ["ModelSampling"],
        "type": ("FLOAT"),
    },
    {
        "metafield": MetaField.SHIFT,
        "keywords": ("shift",),
        "required_class_keywords": ["ModelSampling"],
        "excluded_keywords": ("base_shift", "max_shift"),
        "exact_only": True,
        "type": ("FLOAT"),
    },
    {
        "metafield": MetaField.WEIGHT_DTYPE,
        "keywords": ("weight_dtype",),
        "required_class_regex": [
            r"loader\s*.*\s*model",
            r"load\s*.*\s*model",
            r"model\s*.*\s*loader",
            r"select\s*.*\s*model",
            r"model\s*.*\s*selector",
        ],
        "required_class_keyword_groups": {
            "groups": [
                ["loader", "load", "select", "selector"],
                ["models", "model"],
            ],
            "mins": [1, 1],
        },
        "required_class_keywords": [
            "loader",
            "load",
            "select",
            "selector",
            "diffusion",
            "model",
        ],
    },
    {
        "metafield": MetaField.IMAGE_WIDTH,
        "keywords": (
            "width",
            "empty_latent_width",
            "resolution",
            "dimensions",
            "dimension",
        ),
        "required_context": ["height", "batch_size"],
        "required_class_keywords": [
            "latent",
            "loader",
            "load3d",
            "ByteDanceSeedreamNode",
        ],
    },
    {
        "metafield": MetaField.IMAGE_HEIGHT,
        "keywords": (
            "height",
            "empty_latent_height",
            "resolution",
            "dimensions",
            "dimension",
        ),
        "required_context": ["width", "batch_size"],
        "required_class_keywords": [
            "latent",
            "loader",
            "load3d",
            "ByteDanceSeedreamNode",
        ],
    },
    {
        "metafield": MetaField.LORA_MODEL_NAME,
        "keywords": ("lora_name", "lora"),
        "keywords_regex": (r"^lora_name_?\d{0,2}$", r"^lora_\d{1,2}$"),
        "is_multi": True,
        "format": "calc_lora_hash",
        "hash_field": MetaField.LORA_MODEL_HASH,
        "required_class_keywords": ["lora", "loader", "load"],
        "sort_numeric": True,
        "excluded_keywords": ("lora_syntax", "loaded_loras", "text"),
    },
    {
        "metafield": MetaField.LORA_STRENGTH_MODEL,
        "keywords": (
            "strength_model",
            "lora_strength",
            "lora_wt",
            "strength",
            "weight",
            "wt",
            "model_str",
            "lora_str",
        ),
        "keywords_regex": (
            r"^strength_model_?\d{0,2}$",
            r"^lora_strength_?\d{0,2}$",
            r"^lora_wt_?\d{0,2}$",
            r"^strength_0?\d$",
        ),
        "required_context": ["lora_name"],
        "is_multi": True,
        "required_class_keywords": ["lora", "loader", "load"],
        "type": "FLOAT",
        "sort_numeric": True,
    },
    {
        "metafield": MetaField.LORA_STRENGTH_CLIP,
        "keywords": (
            "strength_clip",
            "clip_strength",
            "clip_str",
            "strength",
            "weight",
            "wt",
            "clip",
        ),
        "keywords_regex": (r"^clip_str_?\d{0,2}$", r"^strength_clip_?\d{0,2}$"),
        "required_context": ["lora_name"],
        "is_multi": True,
        "required_class_keywords": ["lora", "loader", "load"],
        "type": "FLOAT",
        "sort_numeric": True,
    },
]


class MetadataRuleScanner:
    @classmethod
    def INPUT_TYPES(s):  # noqa: N802,N804
        return {
            "required": {
                "exclude_keywords": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": (
                            "mask,find,resize,rotate,detailer,bus,scale,vision,text to,crop,xy,plot,controlnet,save,"
                            "trainlora,postshot"
                        ),
                        "tooltip": (
                            "Comma-separated keywords to exclude nodes whose class names contain any of them."
                        ),
                    },
                )
            },
            "optional": {
                "include_existing": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "If true, also rescan nodes already present in current capture definitions "
                            "(useful after runtime changes)."
                        ),
                    },
                ),
                "mode": (
                    ("new_only", "all", "existing_only"),
                    {
                        "default": "new_only",
                        "tooltip": (
                            "new_only: only new fields for existing nodes\n"
                            "all: full suggestions\nexisting_only: only nodes already captured."
                        ),
                    },
                ),
                "force_include_metafields": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": "",
                        "tooltip": (
                            "Comma-separated MetaField names to always include even if already present "
                            "(e.g. MODEL_HASH,LORA_MODEL_HASH)."
                        ),
                    },
                ),
                "force_include_node_class": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": (
                            "Exact node class names (comma or newline separated) always to include in scan output, "
                            "even if excluded by keywords or mode."
                        ),
                    },
                ),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("suggested_rules_json", "diff_report")
    FUNCTION = "scan_for_rules"
    CATEGORY = "SaveImageWithMetaDataUniversal/rules"
    DESCRIPTION = (
        "Scans installed nodes to suggest rules for capturing metadata and outputs the rules in JSON format. "
        "'exclude_keywords' can filter out irrelevant nodes by their class names. "
        "'force_include_node_class' accepts exact class names to always include, overriding exclusion & mode filters."
    )
    NODE_NAME = "Metadata Rule Scanner"

    def find_common_prefix(self, strings):
        if not strings or len(strings) < 2:
            return None
        prefix = os.path.commonprefix(strings)
        return prefix.rstrip("0123456789_") if prefix and not prefix.isdigit() else None

    def scan_for_rules(
        self,
        exclude_keywords="",
        include_existing=False,
        mode="new_only",
        force_include_metafields="",
        force_include_node_class="",
    ):
        if _DEBUG_VERBOSE:
            logger.info(cstr("[Metadata Scanner] Starting scan...").msg)
        import re  # local to avoid global import cost when node unused

        suggested_nodes, suggested_samplers = {}, {}
        forced_node_names = {
            cls.strip()
            for cls in re.split(r"[\n,]", force_include_node_class or "")
            if cls.strip()
        }
        exclude_list = [kw.strip().lower() for kw in exclude_keywords.split(",") if kw.strip()]
        all_nodes = {k: v for k, v in nodes.NODE_CLASS_MAPPINGS.items() if hasattr(v, "INPUT_TYPES")}

        initial_mode = mode or "new_only"
        if include_existing and initial_mode == "new_only":
            effective_mode = "all"
            if _DEBUG_VERBOSE:
                logger.info(
                    cstr(
                        "[Metadata Scanner] include_existing=True upgraded mode from 'new_only' to 'all' (compat mode)."
                    ).msg
                )
        else:
            effective_mode = initial_mode
        force_include_set = {tok.strip().upper() for tok in force_include_metafields.split(",") if tok.strip()}
        new_nodes_count = 0
        existing_nodes_with_new = 0
        total_new_fields = 0
        total_existing_fields_included = 0
        total_skipped_fields = 0

        # --- Stage 1: Smarter Sampler Detection ---
        for class_name, class_object in all_nodes.items():
            if class_name not in forced_node_names and any(kw in class_name.lower() for kw in exclude_list):
                continue
            if "sampler" in class_name.lower():
                try:
                    inputs = class_object.INPUT_TYPES().get("required", {})
                    candidate = None
                    if "positive" in inputs and "negative" in inputs:
                        candidate = {"positive": "positive", "negative": "negative"}
                    elif "base_positive" in inputs and "base_negative" in inputs:
                        candidate = {
                            "positive": "base_positive",
                            "negative": "base_negative",
                        }
                    elif "guider" in inputs:
                        candidate = {"positive": "guider"}
                    if candidate:
                        if class_name in SAMPLERS:
                            existing_map = SAMPLERS.get(class_name, {})
                            if effective_mode == "existing_only" or effective_mode == "all":
                                if effective_mode == "all":
                                    suggested_samplers[class_name] = candidate
                                elif effective_mode == "existing_only":
                                    inter = {k: v for k, v in candidate.items() if k in existing_map}
                                    if inter:
                                        suggested_samplers[class_name] = inter
                            elif effective_mode == "new_only":
                                diff = {k: v for k, v in candidate.items() if k not in existing_map}
                                if diff:
                                    suggested_samplers[class_name] = diff
                        else:
                            if effective_mode != "existing_only":
                                suggested_samplers[class_name] = candidate
                        if class_name in suggested_samplers:
                            if _DEBUG_VERBOSE:
                                logger.info(
                                    cstr("[Metadata Scanner] Found potential sampler: %s").msg,
                                    class_name,
                                )
                except Exception as e:
                    if _DEBUG_VERBOSE:
                        logger.debug(
                            cstr("[Metadata Scanner] Sampler detection error for %s: %s").msg,
                            class_name,
                            e,
                        )
                    continue

        # --- Stage 2: More Accurate Capture Rule Detection ---
        for class_name, class_object in all_nodes.items():
            excluded_by_keyword = any(kw in class_name.lower() for kw in exclude_list)
            is_forced = class_name in forced_node_names
            if excluded_by_keyword and not is_forced:
                continue
            is_existing = class_name in CAPTURE_FIELD_LIST
            if is_existing and effective_mode == "new_only":
                pass
            elif is_existing and effective_mode == "existing_only":
                pass
            elif is_existing and effective_mode == "all":
                pass
            elif not is_existing and effective_mode == "existing_only":
                if not is_forced:
                    continue
            elif not is_existing and effective_mode in ("new_only", "all"):
                pass

            try:
                inputs, node_suggestions = class_object.INPUT_TYPES(), {}
                req_inputs = inputs.get("required", {}) or {}
                opt_inputs = inputs.get("optional", {}) or {}
                all_input_names = set(req_inputs.keys()) | set(opt_inputs.keys())
                lower_class_name = class_name.lower()

                field_types = {}

                def _declared_type_for(name):
                    val = req_inputs.get(name)
                    if val is None:
                        val = opt_inputs.get(name)
                    dtype = None
                    if isinstance(val, tuple | list) and len(val) > 0:
                        first = val[0]
                        if isinstance(first, str):
                            dtype = first
                        elif isinstance(first, tuple | list) and len(first) > 0 and isinstance(first[0], str):
                            dtype = first[0]
                    elif isinstance(val, str):
                        dtype = val
                    return dtype.upper() if isinstance(dtype, str) else None

                for nm in all_input_names:
                    try:
                        field_types[nm] = _declared_type_for(nm)
                    except Exception:
                        field_types[nm] = None

                for rule in HEURISTIC_RULES:
                    excluded_kws = rule.get("excluded_class_keywords")
                    if excluded_kws and any(kw in lower_class_name for kw in excluded_kws):
                        continue

                    def _matches_required_class(rule_obj, lower_name):
                        patterns = rule_obj.get("required_class_regex") or []
                        for pat in patterns:
                            try:
                                import re as _re
                                if _re.search(pat, lower_name):
                                    return True
                            except Exception:
                                pass
                        groups_spec = rule_obj.get("required_class_keyword_groups")
                        if groups_spec:
                            groups = None
                            mins = None
                            if isinstance(groups_spec, dict):
                                groups = groups_spec.get("groups")
                                mins = groups_spec.get("mins") or groups_spec.get("required")
                            elif isinstance(groups_spec, list):
                                groups = [g.get("keywords", []) for g in groups_spec if isinstance(g, dict)]
                                mins = [g.get("min", 1) for g in groups_spec if isinstance(g, dict)]
                            if (
                                isinstance(groups, list | tuple)
                                and isinstance(mins, list | tuple)
                                and len(groups) == len(mins)
                                and groups
                            ):
                                import re as _re
                                name_simple = _re.sub(r"[ _-]+", "", lower_name)
                                all_ok = True
                                for kws, min_req in zip(groups, mins):
                                    count = 0
                                    for kw in kws or []:
                                        if not isinstance(kw, str):
                                            continue
                                        kw_l = kw.lower()
                                        if kw_l in lower_name:
                                            count += 1
                                        else:
                                            kw_simple = _re.sub(r"[ _-]+", "", kw_l)
                                            if kw_simple and kw_simple in name_simple:
                                                count += 1
                                    try:
                                        need = int(min_req)
                                    except Exception:
                                        need = 1
                                    if need > count:
                                        all_ok = False
                                        break
                                if all_ok:
                                    return True

                        class_kws2 = rule_obj.get("required_class_keywords")
                        if class_kws2:
                            for kw in class_kws2:
                                try:
                                    if isinstance(kw, str) and kw.lower() in lower_name:
                                        return True
                                except Exception:
                                    pass
                            return False
                        return True

                    if not _matches_required_class(rule, lower_class_name):
                        continue

                    context_kws = rule.get("required_context")
                    if context_kws and not any(
                        any(ctx in name.lower() for ctx in context_kws)
                        for name in all_input_names
                    ):
                        continue

                    if rule["metafield"] in node_suggestions:
                        continue

                    excluded_kws = tuple(rule.get("excluded_keywords") or ())
                    excluded_kws = tuple(kw.lower() for kw in excluded_kws if isinstance(kw, str))
                    allowed_types = rule.get("type")
                    if isinstance(allowed_types, list | tuple | set):
                        allowed_types_norm = {str(t).upper() for t in allowed_types}
                    elif allowed_types is not None:
                        allowed_types_norm = {str(allowed_types).upper()}
                    else:
                        allowed_types_norm = None

                    def _type_ok(field_name: str) -> bool:
                        if allowed_types_norm is None:
                            return True
                        ftype = field_types.get(field_name)
                        if not ftype:
                            return False
                        return ftype in allowed_types_norm

                    if rule.get("is_multi"):
                        kws_norm = [
                            kw.lower() if isinstance(kw, str) else str(kw).lower()
                            for kw in rule.get("keywords", [])
                        ]
                        regex_patterns = rule.get("keywords_regex") or []
                        matching_fields = []
                        for fn in all_input_names:
                            lname = fn.lower()
                            if excluded_kws and any(ex_kw in lname for ex_kw in excluded_kws):
                                continue
                            if not _type_ok(fn):
                                continue
                            matched = False
                            if rule.get("exact_only"):
                                if any(lname == kw for kw in kws_norm):
                                    matched = True
                            else:
                                if any(kw in lname for kw in kws_norm):
                                    matched = True
                            if not matched and regex_patterns:
                                for pat in regex_patterns:
                                    try:
                                        import re as _re
                                        if _re.search(pat, fn, _re.IGNORECASE):
                                            matched = True
                                            break
                                    except Exception:
                                        continue
                            if matched:
                                matching_fields.append(fn)
                        if matching_fields:
                            if rule.get("sort_numeric"):
                                import re as _re

                                def _num_key(s):
                                    m = _re.search(r"(\d+)(?!.*\d)", s)
                                    return (
                                        int(m.group(1)) if m else 1_000_000,
                                        s.lower(),
                                    )

                                matching_fields = sorted(matching_fields, key=_num_key)
                            else:
                                matching_fields = sorted(matching_fields)
                            if len(matching_fields) == 1:
                                suggestion = {"field_name": matching_fields[0]}
                                if rule.get("validate"):
                                    suggestion["validate"] = rule["validate"]
                                node_suggestions[rule["metafield"]] = suggestion
                                if rule.get("format") and rule.get("hash_field"):
                                    node_suggestions[rule["hash_field"]] = {
                                        "field_name": matching_fields[0],
                                        "format": rule["format"],
                                    }
                            else:
                                suggestion = {"fields": matching_fields}
                                if rule.get("validate"):
                                    suggestion["validate"] = rule["validate"]
                                node_suggestions[rule["metafield"]] = suggestion
                                if rule.get("format") and rule.get("hash_field"):
                                    node_suggestions[rule["hash_field"]] = {
                                        "fields": matching_fields,
                                        "format": rule["format"],
                                    }
                        continue

                    best_field = None
                    lower_names = {name: name.lower() for name in all_input_names}
                    if excluded_kws:
                        lower_names_filtered = {
                            name: lname
                            for name, lname in lower_names.items()
                            if not any(ex_kw in lname for ex_kw in excluded_kws) and _type_ok(name)
                        }
                    else:
                        lower_names_filtered = {name: lname for name, lname in lower_names.items() if _type_ok(name)}

                    exact_only = bool(rule.get("exact_only"))

                    regex_patterns = rule.get("keywords_regex") or []
                    for kw in rule["keywords"]:
                        kw_norm = kw.lower() if isinstance(kw, str) else str(kw).lower()
                        for name, lname in lower_names_filtered.items():
                            if lname == kw_norm:
                                best_field = name
                                break
                        if best_field:
                            break
                    if not best_field and not exact_only:
                        for kw in rule["keywords"]:
                            kw_norm = kw.lower() if isinstance(kw, str) else str(kw).lower()
                            for name, lname in lower_names_filtered.items():
                                if kw_norm in lname:
                                    best_field = name
                                    break
                            if best_field:
                                break
                    if not best_field and regex_patterns:
                        for pat in regex_patterns:
                            try:
                                import re as _re
                                for name in lower_names_filtered.keys():
                                    if _re.search(pat, name, _re.IGNORECASE):
                                        best_field = name
                                        break
                                if best_field:
                                    break
                            except Exception:
                                continue

                    if best_field:
                        suggestion = {"field_name": best_field}
                        if rule.get("validate"):
                            suggestion["validate"] = rule["validate"]

                        node_suggestions[rule["metafield"]] = suggestion

                        if rule.get("format") and rule.get("hash_field"):
                            hash_field = rule.get("hash_field")
                            hash_suggestion = {
                                "field_name": best_field,
                                "format": rule["format"],
                            }
                            node_suggestions[hash_field] = hash_suggestion

                if node_suggestions:
                    if is_existing:
                        existing_rules = CAPTURE_FIELD_LIST.get(class_name, {}) or {}
                        candidate_total = len(node_suggestions)
                        final_map = {}
                        if effective_mode == "new_only":
                            for mf, data in node_suggestions.items():
                                if mf not in existing_rules or mf.name in force_include_set:
                                    tagged = dict(data)
                                    tagged.setdefault(
                                        "status",
                                        "new" if mf not in existing_rules else "existing",
                                    )
                                    final_map[mf] = tagged
                        elif effective_mode == "existing_only":
                            for mf, data in node_suggestions.items():
                                if mf in existing_rules or mf.name in force_include_set:
                                    tagged = dict(data)
                                    tagged.setdefault(
                                        "status",
                                        "existing" if mf in existing_rules else "new",
                                    )
                                    final_map[mf] = tagged
                        elif effective_mode == "all":
                            for mf, data in node_suggestions.items():
                                tagged = dict(data)
                                tagged.setdefault(
                                    "status",
                                    "existing" if mf in existing_rules else "new",
                                )
                                final_map[mf] = tagged
                        if final_map:
                            suggested_nodes[class_name] = final_map
                            new_here = sum(1 for mf in final_map if final_map[mf].get("status") == "new")
                            existing_here = sum(1 for mf in final_map if final_map[mf].get("status") == "existing")
                            total_new_fields += new_here
                            total_existing_fields_included += existing_here
                            skipped = candidate_total - len(final_map)
                            if skipped > 0:
                                total_skipped_fields += skipped
                            if new_here > 0:
                                existing_nodes_with_new += 1
                    else:
                        if effective_mode != "existing_only":
                            tagged_map = {}
                            for mf, data in node_suggestions.items():
                                tagged = dict(data)
                                tagged.setdefault("status", "new")
                                tagged_map[mf] = tagged
                            suggested_nodes[class_name] = tagged_map
                            new_nodes_count += 1
                            total_new_fields += len(tagged_map)
            except Exception as e:
                logger.warning("[Scanner Warning] Could not process '%s': %s", class_name, e)

        sampler_status = {}
        if suggested_samplers:
            for s_name, mapping in suggested_samplers.items():
                existing_map = SAMPLERS.get(s_name, {})
                sampler_status[s_name] = {
                    k: {
                        "value": v,
                        "status": ("existing" if k in existing_map else "new"),
                    }
                    for k, v in mapping.items()
                }

        final_output = {
            "nodes": {},
            "samplers": {},
            "samplers_status": sampler_status,
            "summary": {},
        }
        if suggested_nodes:
            final_output["nodes"] = {
                node: {mf.name: data for mf, data in rules.items()}
                for node, rules in suggested_nodes.items()
            }
        for forced in forced_node_names:
            if forced not in final_output["nodes"]:
                final_output["nodes"][forced] = {}
        if suggested_samplers:
            final_output["samplers"] = suggested_samplers
        final_output["summary"] = {
            "mode": effective_mode,
            "new_nodes": new_nodes_count,
            "existing_nodes_with_new_fields": existing_nodes_with_new,
            "total_new_fields": total_new_fields,
            "total_existing_fields_included": total_existing_fields_included,
            "total_skipped_fields": total_skipped_fields,
            "force_included_metafields": sorted(list(force_include_set)) if force_include_set else [],
            "forced_node_classes": sorted(list(forced_node_names)) if forced_node_names else [],
        }

        diff_chunks = [
            f"Mode={effective_mode}",
            f"New nodes={new_nodes_count}",
            f"Existing nodes w/ new fields={existing_nodes_with_new}",
            f"New fields={total_new_fields}",
            f"Existing fields included={total_existing_fields_included}",
            f"Skipped fields={total_skipped_fields}",
            "Force metafields="
            + (
                ",".join(sorted(force_include_set))
                if force_include_set
                else "None"
            ),
        ]
        if forced_node_names:
            diff_chunks.append(
                "Forced node classes=" + ",".join(sorted(forced_node_names))
            )
        diff_report = "; ".join(diff_chunks)

        pretty_json = json.dumps(final_output, indent=4)

        base_result = (pretty_json, diff_report)

        env = os.environ
        if not env.get("PYTEST_CURRENT_TEST") and not env.get("METADATA_TEST_MODE"):
            try:
                return {  # type: ignore[return-value]
                    "ui": {"scan_results": [pretty_json], "diff_report": [diff_report]},
                    "scan_results": pretty_json,
                    "diff_report": diff_report,
                    "result": base_result,
                }
            except Exception:
                pass
        return base_result
