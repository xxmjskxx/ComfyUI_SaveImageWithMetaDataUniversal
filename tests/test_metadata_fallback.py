import os
import sys
import types
from pathlib import Path
import numpy as np
from .fixtures_piexif import build_piexif_stub

try:
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node import (
        SaveImageWithMetaDataUniversal,
    )
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta import hook
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.trace import Trace
except ModuleNotFoundError:
    # Add parent of the package directory (e.g. custom_nodes) to sys.path for test execution contexts
    pkg_root = Path(__file__).resolve().parents[2]
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node import (
        SaveImageWithMetaDataUniversal,
    )
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta import hook
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.trace import Trace

class DummyArgs:
    disable_metadata = False

def _ensure_comfy_stub():
    if 'comfy' not in sys.modules:
        m = types.ModuleType('comfy')
        cli_args_mod = types.ModuleType('comfy.cli_args')
        cli_args_mod.args = DummyArgs()
        sys.modules['comfy'] = m
        sys.modules['comfy.cli_args'] = cli_args_mod

class DummyFolderPaths:
    @staticmethod
    def get_output_directory():
        p = Path('test_output')
        p.mkdir(exist_ok=True)
        return str(p)

    @staticmethod
    def get_save_image_path(prefix, outdir, w, h):
        return outdir, prefix, 1, '', prefix

def _prepare_environment():
    _ensure_comfy_stub()
    sys.modules.setdefault('folder_paths', DummyFolderPaths)
    hook.current_save_image_node_id = 0
    hook.current_prompt = {}
    Trace.trace = classmethod(lambda cls, *a, **k: {})
    Trace.filter_inputs_by_trace_tree = classmethod(lambda cls, a, b: {})
    Trace.find_sampler_node_id = classmethod(lambda cls, *a, **k: -1)

# Force environment to multiline for determinism
os.environ['METADATA_TEST_MODE'] = '1'
_prepare_environment()


def make_dummy_image():
    # Single 8x8 black image tensor in expected format (batch of 1)
    arr = np.zeros((1, 8, 8, 3), dtype=np.float32)
    return arr


def test_fallback_minimal_trigger(monkeypatch):
    node = SaveImageWithMetaDataUniversal()

    # Use huge stub to force fallback; consistent deterministic behavior
    node_mod = sys.modules['ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node']
    monkeypatch.setattr(node_mod, 'piexif', build_piexif_stub('huge'))

    images = make_dummy_image()
    # Trigger save as JPEG with tiny limit to guarantee fallback
    res = node.save_images(images=images, file_format='jpeg', max_jpeg_exif_kb=4)

    # Ensure a fallback stage recorded
    assert node._last_fallback_stages, 'No fallback stages recorded'
    stage = node._last_fallback_stages[0]
    assert stage in {'reduced-exif', 'minimal', 'com-marker'}

    # Validate that minimal trimming removed Size / Weight dtype footprints if reached minimal/com-marker
    # We can't easily reopen COM marker here without adding PIL parsing; rely on stage + absence of exceptions.
    assert 'images' in res['ui']
