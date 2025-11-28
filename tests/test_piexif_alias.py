from __future__ import annotations

import sys
from unittest.mock import patch, MagicMock
import pytest

def test_piexif_import_success():
    """Test that piexif is imported correctly when available."""
    # Simulate presence of piexif
    mock_piexif = MagicMock()
    mock_piexif.helper = MagicMock()

    # We must patch before any import happens, and we need to ensure we don't pick up
    # existing modules.

    with patch.dict(sys.modules, {"piexif": mock_piexif, "piexif.helper": mock_piexif.helper}):
        # Clear modules that might have cached piexif
        to_remove = [
            "saveimage_unimeta.piexif_alias",
            "saveimage_unimeta.nodes.node",
            "saveimage_unimeta.nodes"
        ]
        saved_modules = {}
        for m in to_remove:
            if m in sys.modules:
                saved_modules[m] = sys.modules.pop(m)

        try:
            # We also need to make sure `from .nodes.node import piexif` in piexif_alias.py
            # eventually resolves to our mocked piexif.
            # `saveimage_unimeta.nodes.node` does `import piexif`.

            # Since sys.modules['piexif'] is mocked, importing node should pick it up.

            import saveimage_unimeta.piexif_alias
            # If piexif_alias prefers nodes.node.piexif, that's fine, nodes.node should have the mock.

            assert saveimage_unimeta.piexif_alias.piexif == mock_piexif

        finally:
            # Restore modules to avoid breaking other tests
            # (Though reloading them is safer)
            for m, mod in saved_modules.items():
                sys.modules[m] = mod

def test_piexif_fallback_stub():
    """Test that the fallback stub is used when piexif is not available."""
    # This test is tricky because we need to fail imports.
    # The `test_piexif_alias_fallback_logic` below covers this more thoroughly.
    pass

def test_piexif_alias_fallback_logic(monkeypatch):
    """
    Test the fallback logic in piexif_alias.py by forcing imports to fail.
    """
    with patch.dict(sys.modules):
        # Clean up modules
        for mod in ["saveimage_unimeta.piexif_alias", "saveimage_unimeta.nodes.node", "piexif"]:
            if mod in sys.modules:
                del sys.modules[mod]

        # Block imports
        class BlockImport:
            def find_spec(self, fullname, path, target=None):
                if fullname == "saveimage_unimeta.nodes.node" or fullname == "piexif":
                    raise ImportError(f"Blocked {fullname}")
                return None

        sys.meta_path.insert(0, BlockImport())

        try:
            import saveimage_unimeta.piexif_alias
            stub = saveimage_unimeta.piexif_alias.piexif

            # Verify it is the stub
            assert stub.__class__.__name__ == "_PieExifStub"

            # The calculation in source:
            # base = b"stub"
            # base = base * ((10 * 1024 // len(base)) + 1)
            # return base[: 10 * 1024]

            base = b"stub"
            expected = (base * ((10 * 1024 // len(base)) + 1))[: 10 * 1024]
            assert stub.dump({}) == expected
            assert stub.insert(b"", "") is None
            assert stub.helper.UserComment.dump("test") == b"test"

        finally:
            sys.meta_path.pop(0)
