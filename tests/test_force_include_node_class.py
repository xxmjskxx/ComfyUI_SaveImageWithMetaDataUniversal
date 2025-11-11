import importlib
import numpy as np

try:
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node import SaveImageWithMetaDataUniversal  # type: ignore
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes import MetadataForceInclude  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - dev editable path fallback
    from saveimage_unimeta.nodes.node import SaveImageWithMetaDataUniversal  # type: ignore
    from saveimage_unimeta.nodes import MetadataForceInclude  # type: ignore


def make_dummy_image():
    return np.zeros((1, 4, 4, 3), dtype=np.float32)


def test_force_include_node_class(monkeypatch):
    # Capture classes passed to load_user_definitions
    observed = {}
    # Patch the function inside the node module namespace (direct import used there)
    # Import the legacy shim module name still referenced inside save_image for monkeypatching
    node_mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node")
    original_loader = getattr(node_mod, "load_user_definitions")

    def spy(required_classes, suppress_missing_log=False):  # accept new kwarg
        observed["value"] = required_classes.copy() if required_classes else set()
        return original_loader(required_classes, suppress_missing_log=suppress_missing_log)

    monkeypatch.setattr(node_mod, "load_user_definitions", spy)

    # Configure forced classes via MetadataForceInclude node (new API)
    forced = "CustomClassA, CustomClassB"
    mf = MetadataForceInclude()
    mf.configure(force_include_node_class=forced, reset_forced=True, dry_run=False)

    node = SaveImageWithMetaDataUniversal()
    images = make_dummy_image()
    node.save_images(images=images, file_format="jpeg", max_jpeg_exif_kb=4)

    assert "value" in observed, "Spy did not record load invocation"
    assert (
        "CustomClassA" in observed["value"] and "CustomClassB" in observed["value"]
    ), "Forced classes not present in required_classes"
