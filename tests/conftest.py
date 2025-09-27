import os
import sys
import types

# Early stub for folder_paths (must precede any package imports that expect it)
if "folder_paths" not in sys.modules:  # pragma: no cover - test bootstrap
    fp_mod = types.ModuleType("folder_paths")
    _DEF_OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "_test_outputs"))
    try:
        os.makedirs(_DEF_OUT, exist_ok=True)
    except OSError:
        pass
    fp_mod.get_output_directory = lambda: _DEF_OUT  # type: ignore
    fp_mod.get_save_image_path = lambda prefix, output_dir, *a, **k: (output_dir or _DEF_OUT, prefix, 0, "", prefix)  # type: ignore
    fp_mod.get_folder_paths = lambda kind: []  # type: ignore
    fp_mod.get_full_path = lambda kind, name: name  # type: ignore
    sys.modules["folder_paths"] = fp_mod

# Force test mode before any package import so saveimage_unimeta avoids heavy runtime deps
os.environ.setdefault("METADATA_TEST_MODE", "1")
import numpy as np
import pytest

# Ensure package root is on sys.path for absolute imports when pytest alters CWD.
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_TEST_OUTPUT_DIR = os.path.join(_ROOT, "_test_outputs")
os.makedirs(_TEST_OUTPUT_DIR, exist_ok=True)

# Coverage helper: create an empty placeholder generated_user_rules.py so that
# if tests import the module then delete/regenerate it, coverage still has a
# source file to attribute (prevents 'No source for code' error in CI when the
# file is momentarily absent at report time). The real writer will overwrite.
_ext_dir = os.path.join(_ROOT, 'saveimage_unimeta', 'defs', 'ext')
try:
    os.makedirs(_ext_dir, exist_ok=True)
    _placeholder = os.path.join(_ext_dir, 'generated_user_rules.py')
    if not os.path.exists(_placeholder):
        with open(_placeholder, 'w', encoding='utf-8') as _f:
            _f.write(
                "# Placeholder generated_user_rules.py for test coverage stability.\n"
                "CAPTURE_FIELD_LIST = {}\n"
                "SAMPLERS = {}\n"
                "KNOWN = {}\n"
            )
except OSError:
    pass

# Provide lightweight stubs for ComfyUI runtime modules if absent.
if "folder_paths" not in sys.modules:  # pragma: no cover - only for test env
    fp_mod = types.ModuleType("folder_paths")

    def _get_output_directory():
        return _TEST_OUTPUT_DIR

    def _get_save_image_path(prefix, output_dir, width, height):  # mimic 5-tuple
        return (output_dir, prefix, 0, "", prefix)

    def _get_folder_paths(kind):  # minimal for tests needing lora paths
        return []

    fp_mod.get_output_directory = _get_output_directory  # type: ignore
    fp_mod.get_save_image_path = _get_save_image_path  # type: ignore
    fp_mod.get_folder_paths = _get_folder_paths  # type: ignore
    sys.modules["folder_paths"] = fp_mod

if "nodes" not in sys.modules:  # minimal placeholder
    nodes_mod = types.ModuleType("nodes")
    # Provide the mapping expected by capture logic; leave empty for tests that monkeypatch.
    nodes_mod.NODE_CLASS_MAPPINGS = {}  # type: ignore
    sys.modules["nodes"] = nodes_mod

# Stub comfy modules accessed by formatters/hash calculators if ComfyUI not installed.
if "comfy" not in sys.modules:  # pragma: no cover
    comfy_mod = types.ModuleType("comfy")
    # Submodules placeholders
    for sub in [
        "sd1_clip",
        "sd2_clip",
        "clip_model" ,
        "model_management",
    ]:
        m = types.ModuleType(f"comfy.{sub}")
        setattr(comfy_mod, sub.split(".")[-1], m)
        sys.modules[f"comfy.{sub}"] = m
    # minimal attributes used in formatters (hash helpers often call model_management)
    mm = sys.modules["comfy.model_management"]
    mm.current_loaded_models = lambda: []  # type: ignore
    sys.modules["comfy"] = comfy_mod

# Provide hook stub earlier than node import so capture.py picks it up
if "saveimage_unimeta.hook" not in sys.modules:  # pragma: no cover
    hook_mod = types.ModuleType("saveimage_unimeta.hook")

    class _PromptExecuterStub:
        class Caches:
            outputs = {}

        caches = Caches()

    hook_mod.current_prompt = {}
    hook_mod.current_extra_data = {}
    hook_mod.prompt_executer = _PromptExecuterStub()
    hook_mod.current_save_image_node_id = -1
    def _noop(*a, **k):
        return None
    hook_mod.pre_execute = _noop
    hook_mod.pre_get_input_data = _noop
    sys.modules["saveimage_unimeta.hook"] = hook_mod

try:  # Prefer installed package style path
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.save_image import (  # type: ignore
        SaveImageWithMetaDataUniversal,
    )
except ModuleNotFoundError:  # Fallback: relative (editable dev checkout)
    from saveimage_unimeta.nodes.save_image import SaveImageWithMetaDataUniversal  # type: ignore


@pytest.fixture()
def dummy_image():
    return np.zeros((1, 8, 8, 3), dtype=np.float32)


@pytest.fixture()
def node_instance(tmp_path):
    node = SaveImageWithMetaDataUniversal()
    node.output_dir = str(tmp_path)
    return node
# Ensure project root is on sys.path so that
# 'ComfyUI_SaveImageWithMetaDataUniversal' can be imported in tests.

# Signal package to avoid heavy ComfyUI-only imports
os.environ.setdefault("METADATA_TEST_MODE", "1")

TESTS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(TESTS_DIR, '..'))
CUSTOM_NODES_PARENT = os.path.abspath(os.path.join(PROJECT_ROOT, '..'))

for path in (CUSTOM_NODES_PARENT, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

# Sanity debug (harmless if left): ensure import works early; swallow errors to avoid pollution
try:  # pragma: no cover - defensive
    __import__("ComfyUI_SaveImageWithMetaDataUniversal")
except Exception:  # noqa: BLE001 - tests bootstrap
    pass

# Provide a lightweight stub for folder_paths expected by some modules during import.
if "folder_paths" not in sys.modules:  # pragma: no cover - environment setup
    import types
    fp = types.ModuleType("folder_paths")
    def _no_op(*_a, **_kw): return None
    # Minimal API surface used in code
    fp.get_output_directory = lambda: "."
    fp.get_save_image_path = lambda *a, **k: (".", "", "test.png", None)
    fp.get_folder_paths = lambda kind: []  # returns list of search paths
    fp.get_full_path = lambda kind, name: name  # pretend name is already a path
    sys.modules["folder_paths"] = fp

# Provide comfy tokenizer stubs
if "comfy" not in sys.modules:  # pragma: no cover
    import types
    comfy = types.ModuleType("comfy")
    sd1_clip = types.ModuleType("comfy.sd1_clip")
    sdxl_clip = types.ModuleType("comfy.sdxl_clip")
    text_encoders = types.ModuleType("comfy.text_encoders")
    flux_mod = types.ModuleType("comfy.text_encoders.flux")
    sd2_clip = types.ModuleType("comfy.text_encoders.sd2_clip")
    sd3_clip = types.ModuleType("comfy.text_encoders.sd3_clip")

    class _BaseTokenizer:  # minimal placeholder
        pass
    class SD1Tokenizer(_BaseTokenizer): ...
    class SDXLTokenizer(_BaseTokenizer): ...
    class FluxTokenizer(_BaseTokenizer): ...
    class SD2Tokenizer(_BaseTokenizer): ...
    class SD3Tokenizer(_BaseTokenizer): ...

    def escape_important(x): return x
    def unescape_important(x): return x
    def token_weights(x): return []

    sd1_clip.SD1Tokenizer = SD1Tokenizer
    sd1_clip.escape_important = escape_important
    sd1_clip.unescape_important = unescape_important
    sd1_clip.token_weights = token_weights
    sd1_clip.expand_directory_list = lambda paths: paths  # identity expansion
    sdxl_clip.SDXLTokenizer = SDXLTokenizer
    flux_mod.FluxTokenizer = FluxTokenizer
    sd2_clip.SD2Tokenizer = SD2Tokenizer
    sd3_clip.SD3Tokenizer = SD3Tokenizer

    text_encoders.flux = flux_mod
    text_encoders.sd2_clip = sd2_clip
    text_encoders.sd3_clip = sd3_clip

    sys.modules["comfy"] = comfy
    sys.modules["comfy.sd1_clip"] = sd1_clip
    sys.modules["comfy.sdxl_clip"] = sdxl_clip
    sys.modules["comfy.text_encoders"] = text_encoders
    sys.modules["comfy.text_encoders.flux"] = flux_mod
    sys.modules["comfy.text_encoders.sd2_clip"] = sd2_clip
    sys.modules["comfy.text_encoders.sd3_clip"] = sd3_clip

# Provide minimal 'nodes' module with NODE_CLASS_MAPPINGS used in capture.
if "nodes" not in sys.modules:  # pragma: no cover
    import types
    nodes_mod = types.ModuleType("nodes")
    nodes_mod.NODE_CLASS_MAPPINGS = {}
    nodes_mod.checkpoint_nodes = {}
    sys.modules["nodes"] = nodes_mod


# Fixture to save/restore environment flags used by the metadata loader
@pytest.fixture()
def reset_env_flags():
    keys = [
        "METADATA_TEST_MODE",
        "METADATA_NO_HASH_DETAIL",
        "METADATA_NO_LORA_SUMMARY",
        "METADATA_DEBUG_PROMPTS",
    ]
    saved = {k: os.environ.get(k) for k in keys}
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

# -----------------------------
# Test mode detection utilities
# -----------------------------
_TEST_MODE_TRUTHY = {"1", "true", "yes", "on"}

def metadata_test_mode_enabled() -> bool:
    """Return True if METADATA_TEST_MODE is explicitly enabled.

    Mirrors runtime parsing logic in saveimage_unimeta.defs.__init__ so tests
    use identical truthiness semantics.
    """
    return os.environ.get("METADATA_TEST_MODE", "").strip().lower() in _TEST_MODE_TRUTHY

@pytest.fixture()
def metadata_test_mode():  # pragma: no cover - trivial accessor
    return metadata_test_mode_enabled()
