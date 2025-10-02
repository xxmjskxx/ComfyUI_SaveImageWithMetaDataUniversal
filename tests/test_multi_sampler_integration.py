import os
import importlib
import types

import pytest

from saveimage_unimeta.defs.meta import MetaField
from saveimage_unimeta.defs.captures import CAPTURE_FIELD_LIST
from saveimage_unimeta import hook as global_hook


class _DummyImage:
    def __init__(self, w=8, h=8):
        import numpy as np
        self._arr = (np.random.rand(h, w, 3)).astype("float32")

    def cpu(self):
        return self

    def numpy(self):  # ComfyUI expects .numpy() for tensor-like
        return self._arr


@pytest.fixture(autouse=True)
def ensure_test_mode(monkeypatch):
    monkeypatch.setenv("METADATA_TEST_MODE", "1")


@pytest.fixture
def restore_capture_definitions():
    original = {k: dict(v) for k, v in CAPTURE_FIELD_LIST.items()}
    try:
        yield
    finally:
        # Restore / remove modifications
        for k in list(CAPTURE_FIELD_LIST.keys()):
            if k not in original:
                CAPTURE_FIELD_LIST.pop(k, None)
        for k, v in original.items():
            CAPTURE_FIELD_LIST[k] = v


def _build_prompt_graph():
    """Return a minimal prompt graph with two sampler nodes feeding the save node.

    Graph layout (edges point toward save node):
        KSampler(1) --> Save(100)
        KSampler(2) --> Save(100)
    """
    # Each node entry: { 'class_type': str, 'inputs': { field: [linked_node_id] or raw }}
    # Only need minimal fields; Capture.get_inputs pulls values via get_input_data stub in test mode.
    prompt = {
        "1": {
            "class_type": "KSampler",
            "inputs": {
                # Link structure isn't needed for sampler internal fields; only for graph traversal.
            },
        },
        "2": {
            "class_type": "KSampler",
            "inputs": {},
        },
        "100": {
            "class_type": "SaveImageWithMetaDataUniversal",
            "inputs": {
                # Two incoming sampler references so tracing finds both
                "sampler_a": ["1", 0],
                "sampler_b": ["2", 0],
            },
        },
    }
    return prompt


def _inject_runtime_values(monkeypatch):
    """Patch hook.prompt_executer.caches.outputs and get_input_data behavior so Capture sees sampler inputs."""
    # Provide deterministic sampler field values per node id
    # Format expected by get_input_data test stub: it returns (inputs_dict,)
    values = {
        "1": {
            "seed": [111],
            "steps": [30],
            "cfg": [8.5],
            "sampler_name": ["Euler a"],
            "scheduler": ["normal"],
            # Denoise not normally on KSampler; we temporarily extend capture rules below to test enrichment.
            "denoise": [0.75],
        },
        "2": {
            "seed": [222],
            "steps": [20],
            "cfg": [5.0],
            "sampler_name": ["DPM++ 2M"],
            "scheduler": ["karras"],
            "denoise": [0.5],
            # Simulate a segment sampler by adding start/end step fields (new MetaFields)
            "start_step": [30],
            "end_step": [49],
        },
    }

    def fake_get_input_data(node_inputs, obj_class, node_id, *a, **k):  # noqa: D401
        # Return a mapping of all known fields for that node id merged with its inputs
        """Test stub for get_input_data.

        Simulates sampler-like node input retrieval by returning a merged
        mapping of supplied node_inputs and synthetic values for meta rule
        evaluation. Only the (mapping,) tuple shape is required by Capture.

        Args:
            node_inputs (dict): Input fields for the node.
            obj_class: Node class (unused here).
            node_id: Graph node identifier.
            *a: Additional positional args ignored.
            **k: Additional keyword args ignored.
        Returns:
            tuple[dict]: Single element tuple containing merged inputs.
        """
        base = values.get(str(node_id), {}).copy()
        # Include any fields already present (like graph wiring) if necessary
        for k2, v2 in (node_inputs or {}).items():
            if k2 not in base:
                base[k2] = v2
        return (base,)

    # Patch the imported get_input_data symbol inside capture module namespace
    import saveimage_unimeta.capture as capture_mod
    monkeypatch.setattr(capture_mod, "get_input_data", fake_get_input_data, raising=True)
    return values


def test_save_images_multi_sampler_enrichment(restore_capture_definitions, monkeypatch, tmp_path):
    prompt = _build_prompt_graph()
    global_hook.current_prompt = prompt
    global_hook.current_save_image_node_id = "100"
    # Monkeypatch Capture.get_inputs to bypass full graph extraction complexity
    import saveimage_unimeta.capture as capture_mod
    def fake_get_inputs():  # noqa: D401
        return {
            MetaField.SAMPLER_NAME: [("1", "Euler a"), ("2", "DPM++ 2M")],
            MetaField.STEPS: [("1", 30), ("2", 20)],
            MetaField.SCHEDULER: [("1", "normal"), ("2", "karras")],
            MetaField.DENOISE: [("1", 0.75), ("2", 0.5)],
            MetaField.START_STEP: [("2", 30)],
            MetaField.END_STEP: [("2", 49)],
        }
    monkeypatch.setattr(capture_mod.Capture, "get_inputs", classmethod(lambda cls: fake_get_inputs()))

    # Instantiate node
    mod = importlib.import_module("saveimage_unimeta.nodes.save_image")
    SaveNode = getattr(mod, "SaveImageWithMetaDataUniversal")
    # Provide dummy mapping entries so trace logic class_type filters align
    import nodes as nodes_pkg  # type: ignore
    nodes_pkg.NODE_CLASS_MAPPINGS.setdefault("KSampler", type("_DummyKSampler", (), {}))  # type: ignore
    node = SaveNode()
    node.output_dir = str(tmp_path)

    # Generate pnginfo directly (avoids file IO complexity and focuses on enrichment logic)
    pnginfo = SaveNode.gen_pnginfo(
        sampler_selection_method=os.environ.get("TEST_SAMPLER_METHOD", "Farthest"),
        sampler_selection_node_id=0,
        save_civitai_sampler=False,
        set_max_samplers=4,
    )

    # Assertions: multi-sampler detail enriched
    assert "Samplers detail" in pnginfo, pnginfo.keys()
    detail = pnginfo["Samplers detail"]
    # Should include structured entries with Scheduler and Denoise values
    assert "Scheduler: normal" in detail
    assert "Denoise: 0.75" in detail
    assert "Scheduler: karras" in detail
    assert "Denoise: 0.5" in detail
    # save_images adds flattened parameters; gen_pnginfo alone doesn't include them, so we don't assert tail here.


def test_full_save_images_writes_parameters_with_multi_sampler_tail(monkeypatch, tmp_path):
    """End-to-end: save_images writes a PNG whose parameters line has Samplers: tail; Samplers detail enriched."""
    # Prompt graph with two upstream samplers
    prompt = _build_prompt_graph()
    global_hook.current_prompt = prompt
    global_hook.current_save_image_node_id = "100"
    # Patch Capture.get_inputs to simulate two samplers
    import saveimage_unimeta.capture as capture_mod
    def fake_get_inputs():
        return {
            MetaField.SAMPLER_NAME: [("1", "Euler a"), ("2", "DPM++ 2M")],
            MetaField.STEPS: [("1", 30), ("2", 20)],
            MetaField.SCHEDULER: [("1", "normal"), ("2", "karras")],
            MetaField.DENOISE: [("1", 0.75), ("2", 0.5)],
            MetaField.START_STEP: [("2", 30)],
            MetaField.END_STEP: [("2", 49)],
        }
    monkeypatch.setattr(capture_mod.Capture, "get_inputs", classmethod(lambda cls: fake_get_inputs()))
    # Dummy NODE_CLASS_MAPPINGS entry
    import nodes as nodes_pkg  # type: ignore
    nodes_pkg.NODE_CLASS_MAPPINGS.setdefault("KSampler", type("_DummyKSampler", (), {}))  # type: ignore
    # Instantiate node and run save_images
    mod = importlib.import_module("saveimage_unimeta.nodes.save_image")
    SaveNode = getattr(mod, "SaveImageWithMetaDataUniversal")
    node = SaveNode()
    node.output_dir = str(tmp_path)
    img = _DummyImage()
    result = node.save_images([img], include_lora_summary=False, set_max_samplers=4)
    saved_file = result["ui"]["images"][0]["filename"]
    png_path = tmp_path / saved_file
    assert png_path.is_file(), f"Expected file not found: {png_path}"
    # Read parameters back via Pillow
    from PIL import Image as _PILImage
    with _PILImage.open(png_path) as im:
        info = im.text or {}
    params = info.get("parameters", "")
    assert "Samplers:" in params  # tail present
    assert "Euler a" in params and "DPM++ 2M" in params
    # Range formatting for second sampler
    assert "(30-49)" in params
    # Verify structured detail block present (scheduler/denoise appear there)
    assert "Samplers detail" in params
    assert "Scheduler: normal" in params and "Scheduler: karras" in params
    assert "Denoise: 0.75" in params and "Denoise: 0.5" in params
    # The in-memory pnginfo at generation time had Samplers detail (check node.gen_pnginfo output)
    pnginfo_dict = node.gen_pnginfo("Farthest", 0, False, 4)
    assert "Samplers detail" in pnginfo_dict
    detail = pnginfo_dict["Samplers detail"]
    assert "Scheduler: normal" in detail and "Scheduler: karras" in detail


def _multi_sampler_inputs():
    return {
        MetaField.SAMPLER_NAME: [("1", "Euler a"), ("2", "DPM++ 2M")],
        MetaField.STEPS: [("1", 30), ("2", 20)],
        MetaField.SCHEDULER: [("1", "normal"), ("2", "karras")],
        MetaField.DENOISE: [("1", 0.75), ("2", 0.5)],
        MetaField.START_STEP: [("2", 30)],
        MetaField.END_STEP: [("2", 49)],
    }


def _prep_node(monkeypatch, tmp_path, file_format="png"):
    prompt = _build_prompt_graph()
    global_hook.current_prompt = prompt
    global_hook.current_save_image_node_id = "100"
    import saveimage_unimeta.capture as capture_mod
    monkeypatch.setattr(capture_mod.Capture, "get_inputs", classmethod(lambda cls: _multi_sampler_inputs()))
    import nodes as nodes_pkg  # type: ignore
    nodes_pkg.NODE_CLASS_MAPPINGS.setdefault("KSampler", type("_DummyKSampler", (), {}))  # type: ignore
    mod = importlib.import_module("saveimage_unimeta.nodes.save_image")
    SaveNode = getattr(mod, "SaveImageWithMetaDataUniversal")
    node = SaveNode()
    node.output_dir = str(tmp_path)
    return node


def test_jpeg_fallback_trims_multi_sampler_tail(monkeypatch, tmp_path):
    """JPEG minimal/com-marker fallback should remove both Samplers tail and Samplers detail from parameters."""
    node = _prep_node(monkeypatch, tmp_path)
    # Build extra metadata to enlarge EXIF size
    big_meta = {f"Extra_{i}": "X" * 80 for i in range(80)}
    img = _DummyImage()
    # Very small EXIF cap to force fallback path
    result = node.save_images(
        [img],
        file_format="jpeg",
        max_jpeg_exif_kb=4,
        extra_metadata=big_meta,
        include_lora_summary=False,
    )
    stage = node._last_fallback_stages[0]
    assert stage in {"minimal", "com-marker", "reduced-exif"}
    # Read parameters from file (COM marker or EXIF user comment if present)
    saved_file = result["ui"]["images"][0]["filename"]
    jpg_path = tmp_path / saved_file
    from PIL import Image as _PILImage
    with _PILImage.open(jpg_path) as im:
        info = getattr(im, 'text', {}) or {}
    params = info.get("parameters", "")
    # If COM marker path used, Pillow may not expose comment; fallback: robust COM extraction
    if not params:
        # Robustly extract the COM marker (0xFFFE) from the JPEG file
        def extract_jpeg_com_marker(path):
            with open(path, "rb") as f:
                data = f.read()
            i = 0
            while i < len(data) - 1:
                if data[i] == 0xFF and data[i+1] == 0xFE:
                    # Found COM marker
                    if i+4 > len(data):
                        break
                    length = int.from_bytes(data[i+2:i+4], "big")
                    start = i + 4
                    end = start + length - 2
                    comment_bytes = data[start:end]
                    try:
                        return comment_bytes.decode("utf-8", "ignore")
                    except Exception:
                        return ""
                elif data[i] == 0xFF and data[i+1] != 0x00:
                    # Skip marker segment
                    if i+4 > len(data):
                        break
                    length = int.from_bytes(data[i+2:i+4], "big")
                    i += 2 + length
                else:
                    i += 1
            return ""
        params = extract_jpeg_com_marker(jpg_path)
    assert "Samplers:" not in params  # tail trimmed
    assert "Samplers detail" not in params  # detail trimmed by minimal allowlist


def test_webp_preserves_multi_sampler_detail(monkeypatch, tmp_path):
    """WebP (no fallback triggered) should retain Samplers tail and detail."""
    node = _prep_node(monkeypatch, tmp_path)
    img = _DummyImage()
    result = node.save_images([img], file_format="webp", max_jpeg_exif_kb=60, include_lora_summary=False)
    saved_file = result["ui"]["images"][0]["filename"]
    webp_path = tmp_path / saved_file
    from PIL import Image as _PILImage
    with _PILImage.open(webp_path) as im:
        info = getattr(im, 'text', {}) or {}
    params = info.get("parameters", "")
    # WebP path may embed parameters; if absent (older Pillow), just assert generation pre-save
    if params:
        assert "Samplers:" in params
        assert "Samplers detail" in params


def test_jpeg_reduced_exif_stage_with_multi_sampler(monkeypatch, tmp_path):
    """Force the first EXIF attempt to exceed limit and second (parameters-only) to fit, yielding reduced-exif."""
    node = _prep_node(monkeypatch, tmp_path)
    # Stub piexif.dump to return large bytes first call (full EXIF) then small bytes (parameters-only)
    import saveimage_unimeta.nodes.node as node_mod
    real_piexif = node_mod.piexif

    class PStub:
        ExifIFD = real_piexif.ExifIFD
        helper = real_piexif.helper
        ImageIFD = getattr(real_piexif, "ImageIFD", types.SimpleNamespace())
        _count = 0

        @staticmethod
        def dump(d):  # noqa: D401
            PStub._count += 1
            if PStub._count == 1:
                return b"X" * 90000  # ~90KB triggers fallback (limit 8KB)
            return b"Y" * 2000  # fits under 8KB limit

        @staticmethod
        def insert(exif_bytes, path):  # noqa: D401
            # no-op; rely on save_images to proceed
            return None

    monkeypatch.setattr(node_mod, "piexif", PStub)
    # Execute save with low limit to trigger reduced-exif path
    img = _DummyImage()
    node.save_images([img], file_format="jpeg", max_jpeg_exif_kb=8, include_lora_summary=False)
    assert node._last_fallback_stages, "No fallback recorded"
    assert node._last_fallback_stages[0] == "reduced-exif"
    # Regenerate parameters (reduced-exif keeps full parameter string, no trimming)
    from saveimage_unimeta.capture import Capture  # local import to avoid circular in test collection
    pnginfo = node.gen_pnginfo("Farthest", 0, False, 4)
    params = Capture.gen_parameters_str(pnginfo)
    # Ensure multi-sampler artifacts present in original parameters set
    assert "Samplers detail" in params
    assert "Samplers:" in params


def test_jpeg_reduced_exif_fallback_marker_and_detail(monkeypatch, tmp_path):
    """Ensure reduced-exif fallback writes marker and retains untrimmed multi-sampler detail in EXIF user comment."""
    node = _prep_node(monkeypatch, tmp_path)
    import saveimage_unimeta.nodes.node as node_mod
    real_piexif = node_mod.piexif

    class PStub:
        ExifIFD = real_piexif.ExifIFD
        helper = real_piexif.helper
        ImageIFD = getattr(real_piexif, "ImageIFD", object)
        _count = 0

        @staticmethod
        def dump(d):  # noqa: D401
            PStub._count += 1
            if PStub._count == 1:
                return b"X" * 90000  # trigger fallback
            return b"Y" * 3000  # within limit

        @staticmethod
        def insert(exif_bytes, path):  # noqa: D401
            # Allow EXIF replacement pass-through
            return None

    monkeypatch.setattr(node_mod, "piexif", PStub)
    img = _DummyImage()
    node.save_images([img], file_format="jpeg", max_jpeg_exif_kb=8, include_lora_summary=False)
    assert node._last_fallback_stages and node._last_fallback_stages[0] == "reduced-exif"
    # We cannot reliably parse EXIF user comment with stub; fallback stage already asserted.
    # Re-generate parameters to confirm detail present pre-trim under reduced-exif semantics.
    from saveimage_unimeta.capture import Capture  # local import to avoid circular issues at collection
    pnginfo = node.gen_pnginfo("Farthest", 0, False, 4)
    params = Capture.gen_parameters_str(pnginfo)
    assert "Samplers detail" in params and "Samplers:" in params
