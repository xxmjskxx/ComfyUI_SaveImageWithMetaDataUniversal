import logging
import importlib


def test_suppress_missing_class_log(monkeypatch, caplog):
    """Ensure suppress_missing_class_log hides missing-class coverage info log."""
    try:  # prefer installed-style path
        from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.save_image import (  # type: ignore
            SaveImageWithMetaDataUniversal,
        )
    except ModuleNotFoundError:  # editable checkout fallback
        from saveimage_unimeta.nodes.save_image import SaveImageWithMetaDataUniversal  # type: ignore

    # Force a required_classes set with an unlikely fake node to trigger missing log if not suppressed
    try:
        node_mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node")
    except ModuleNotFoundError:
        node_mod = importlib.import_module("saveimage_unimeta.nodes.node")
    original_loader = getattr(node_mod, "load_user_definitions")
    observed = {}

    def noisy_loader(required_classes=None, suppress_missing_log=False):  # noqa: D401
        observed["saw_required"] = required_classes
        return original_loader(required_classes, suppress_missing_log=suppress_missing_log)

    monkeypatch.setattr(node_mod, "load_user_definitions", noisy_loader)

    fake_required = {"DefinitelyMissingNodeClass123"}

    # Run once without suppression to verify log appears
    caplog.set_level(logging.INFO)
    n = SaveImageWithMetaDataUniversal()
    # Monkeypatch Trace.trace to return a structure yielding our fake class
    try:
        trace_mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.trace")
    except ModuleNotFoundError:
        trace_mod = importlib.import_module("saveimage_unimeta.trace")
    monkeypatch.setattr(trace_mod.Trace, "trace", staticmethod(lambda _id, _p: {1: (0, list(fake_required)[0])}))
    n.save_images(images=[], suppress_missing_class_log=False)  # type: ignore[arg-type]
    emitted = "\n".join(r.message for r in caplog.records)
    assert "Missing classes in defaults+ext" in emitted

    # Clear and run with suppression to ensure log absent
    caplog.clear()
    n.save_images(images=[], suppress_missing_class_log=True)  # type: ignore[arg-type]
    emitted2 = "\n".join(r.message for r in caplog.records)
    assert "Missing classes in defaults+ext" not in emitted2

    # Sanity: ensure our fake class flowed into loader both times
    assert observed["saw_required"] is not None
