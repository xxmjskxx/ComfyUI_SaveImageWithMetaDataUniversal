# from . import SAMPLERS
import re
from collections import deque

from .samplers import CONDITIONING_ROUTERS, GUIDERS, SAMPLERS

_CONNECTION_CACHE: dict[str, bool] = {}  # Cache for is_node_connected results


def _has_prompt_capture_rules(class_type: str) -> bool:
    """Check if a node class has prompt capture rules in CAPTURE_FIELD_LIST.

    Extensions can register their nodes as text encoders by adding
    ``MetaField.POSITIVE_PROMPT`` or ``MetaField.NEGATIVE_PROMPT`` entries
    to their ``CAPTURE_FIELD_LIST``.  This function performs a lazy import
    to avoid circular dependencies at module load time.
    """
    from . import CAPTURE_FIELD_LIST
    from .meta import MetaField

    rules = CAPTURE_FIELD_LIST.get(class_type)
    if isinstance(rules, dict):
        return MetaField.POSITIVE_PROMPT in rules or MetaField.NEGATIVE_PROMPT in rules
    return False


def _is_text_encoder(class_type: str) -> bool:
    """Heuristic to decide if a node class encodes text for conditioning.
    - First, match known encoder class names exactly (stable and explicit).
    - Then, check if extensions registered prompt capture rules for this class.
    - Finally, use a case-insensitive regex for common patterns (text/prompt + encode),
      allowing flexible spacing and ordering to catch variants without being too noisy.
    """
    if not class_type:
        return False
    ct = str(class_type)
    # Whitelist of commonly seen text encoders
    KNOWN = {  # noqa: N806 (constant-style inside function for clarity)
        "CLIPTextEncode",
        "CLIPTextEncodeFlux",
        "TextEncodeQwenImageEdit",
        "TextEncodeQwenImageEditPlus",
    }
    if ct in KNOWN:
        return True
    # Check if extensions registered prompt capture rules for this class
    if _has_prompt_capture_rules(ct):
        return True
    # Flexible pattern: match "text encode", "encode text", "prompt encode", "encode prompt" (any spacing)
    if re.search(
        r"(text\s*encode|encode\s*text|prompt\s*encode|encode\s*prompt)",
        ct,
        re.IGNORECASE,
    ):
        return True
    # Additional light-weight fallbacks (avoid matching generic 'Encode' unrelated to text)
    if re.search(
        r"(text[-_ ]?encoder|cliptextencode|t5\s*xxl\s*encode|t5\s*encode)",
        ct,
        re.IGNORECASE,
    ):
        return True
    return False


def is_positive_prompt(node_id, obj, prompt, extra_data, outputs, input_data_all):
    return node_id in _get_node_id_list(prompt, "positive")


def is_negative_prompt(node_id, obj, prompt, extra_data, outputs, input_data_all):
    return node_id in _get_node_id_list(prompt, "negative")


def _get_node_id_list(prompt, field_name):
    node_id_list = {}
    for nid, node in prompt.items():
        if node["class_type"] in SAMPLERS:
            field_map = SAMPLERS[node["class_type"]]
            d = deque()
            if field_name in field_map and field_map[field_name] in node["inputs"]:
                d.append(node["inputs"][field_map[field_name]][0])
            while len(d) > 0:
                current_node_id = d.popleft()
                if current_node_id not in prompt:
                    continue
                class_type = prompt[current_node_id]["class_type"]
                # Treat text-encoding nodes (known names or heuristic patterns) as prompt sources
                # so validators can correctly detect positive/negative prompt connections.
                if _is_text_encoder(class_type):
                    node_id_list[nid] = current_node_id
                    break
                # When traversing through a known guider node (e.g. CFGGuider),
                # or a conditioning-router node (e.g. ControlNetApplyAdvanced),
                # follow only the conditioning input that matches the requested
                # field so positive and negative prompts are resolved correctly.
                routing_map = GUIDERS.get(class_type) or CONDITIONING_ROUTERS.get(class_type)
                if routing_map is not None:
                    if field_name in routing_map:
                        input_name = routing_map[field_name]
                        node_inputs = prompt[current_node_id].get("inputs", {})
                        if input_name in node_inputs:
                            inp = node_inputs[input_name]
                            if isinstance(inp, list | tuple) and inp:
                                d.append(inp[0])
                    continue
                if "inputs" in prompt[current_node_id]:
                    for v in prompt[current_node_id]["inputs"].values():
                        if isinstance(v, list | tuple) and v:
                            d.append(v[0])
    return node_id_list.values()


def is_node_connected(node_id, prompt, *args):
    """
    Validation function to check if a node has any output connections.
    Caches the result for performance.
    """
    if node_id in _CONNECTION_CACHE:
        return _CONNECTION_CACHE[node_id]
    for other_node in prompt.values():
        # FIX: Check if 'inputs' key exists before accessing it.
        if "inputs" in other_node:
            for input_val in other_node["inputs"].values():
                if isinstance(input_val, list | tuple) and str(input_val[0]) == str(node_id):
                    _CONNECTION_CACHE[node_id] = True
                    return True
    _CONNECTION_CACHE[node_id] = False
    return False
