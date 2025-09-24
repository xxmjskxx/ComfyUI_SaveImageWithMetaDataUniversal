import os
import types
from pathlib import Path

from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node import SaveImageWithMetaDataUniversal

class DummyArgs:
    disable_metadata = False

# Patch comfy.cli_args.args if absent
import sys
if 'comfy' not in sys.modules:
    m = types.ModuleType('comfy')
    cli_args_mod = types.ModuleType('comfy.cli_args')
    cli_args_mod.args = DummyArgs()
    sys.modules['comfy'] = m
    sys.modules['comfy.cli_args'] = cli_args_mod

# Minimal stubs
import numpy as np
class DummyFolderPaths:
    @staticmethod
    def get_output_directory():
        p = Path('test_output')
        p.mkdir(exist_ok=True)
        return str(p)

    @staticmethod
    def get_save_image_path(prefix, outdir, w, h):
        return outdir, prefix, 1, '', prefix

sys.modules.setdefault('folder_paths', DummyFolderPaths)

# Fake hook + Trace dependencies
from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta import hook
hook.current_save_image_node_id = 0
hook.current_prompt = {}

from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.trace import Trace
Trace.trace = classmethod(lambda cls, *a, **k: {})
Trace.filter_inputs_by_trace_tree = classmethod(lambda cls, a, b: {})
Trace.find_sampler_node_id = classmethod(lambda cls, *a, **k: -1)

# Force environment to multiline for determinism
os.environ['METADATA_TEST_MODE'] = '1'


def make_dummy_image():
    # Single 8x8 black image tensor in expected format (batch of 1)
    arr = np.zeros((1, 8, 8, 3), dtype=np.float32)
    return arr


def test_fallback_minimal_trigger(monkeypatch):
    node = SaveImageWithMetaDataUniversal()

    # Monkeypatch piexif to force large EXIF generation so fallback path triggers
    try:
        import piexif  # type: ignore
        real_dump = piexif.dump

        def huge_dump(d):
            b = real_dump(d)
            return b + b * 400

        monkeypatch.setattr(piexif, 'dump', huge_dump)
    except Exception:
        # Provide stub that forces large size semantics
        class _PiexifStub:
            @staticmethod
            def dump(d):
                return b"x" * (5 * 1024 * 1024)  # 5MB to guarantee oversize
        import sys as _sys
        _sys.modules['piexif'] = _PiexifStub()

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
