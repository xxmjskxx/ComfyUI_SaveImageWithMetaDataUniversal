from __future__ import annotations

import pytest
import sys
from unittest.mock import patch, MagicMock
from saveimage_unimeta.nodes.node import __getattr__, piexif, SaveImageWithMetaDataUniversal

def test_node_getattr_compatibility():
    """Test that __getattr__ handles SaveImageWithMetaDataUniversal correctly."""
    assert __getattr__("SaveImageWithMetaDataUniversal") is SaveImageWithMetaDataUniversal

    with pytest.raises(AttributeError, match="InvalidAttribute"):
        __getattr__("InvalidAttribute")

def test_node_piexif_stub_implementation(monkeypatch):
    """Test the internal _PieExifStub implementation by manually instantiating it or forcing the fallback."""
    # Ensure clean state for this test
    with patch.dict(sys.modules):
        # Remove modules that might be cached or mocked
        # We must also remove parent packages if they might hold references
        for mod in ["saveimage_unimeta.nodes.node", "saveimage_unimeta.nodes", "piexif"]:
            if mod in sys.modules:
                del sys.modules[mod]

        class BlockImport:
            def find_spec(self, fullname, path, target=None):
                if fullname == "piexif":
                    raise ImportError(f"Blocked {fullname}")
                return None

        sys.meta_path.insert(0, BlockImport())
        try:
            # Force re-import of nodes.node to trigger fallback
            import saveimage_unimeta.nodes.node as node_mod

            stub = node_mod.piexif

            assert stub.__class__.__name__ == "_PieExifStub"
            assert stub.ImageIFD.Model == 0x0110
            assert stub.ExifIFD.UserComment == 0x9286

            # Test dump
            base = b"stub"
            expected = (base * ((10 * 1024 // len(base)) + 1))[: 10 * 1024]
            assert stub.dump({}) == expected

            # Test insert
            assert stub.insert(b"", "") is None

            # Test helper.UserComment.dump
            assert stub.helper.UserComment.dump("hello") == b"hello"
            assert stub.helper.UserComment.dump(123) == b""

        finally:
             sys.meta_path.pop(0)

def test_node_exports():
    """Verify that expected symbols are exported."""
    # Since previous tests might have messed with imports, we ensure we have a valid module here
    if "saveimage_unimeta.nodes.node" not in sys.modules:
         import saveimage_unimeta.nodes.node
    node_mod = sys.modules["saveimage_unimeta.nodes.node"]

    assert "SaveCustomMetadataRules" in node_mod.__all__
    assert "SaveImageWithMetaDataUniversal" in node_mod.__all__
    assert "load_user_definitions" in node_mod.__all__
    assert "piexif" in node_mod.__all__
