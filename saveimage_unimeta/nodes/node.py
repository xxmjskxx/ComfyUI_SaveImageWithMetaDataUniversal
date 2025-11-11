"""Legacy writer node module.

This module intentionally contains only the SaveCustomMetadataRules node. All other
node classes have been split into dedicated modules under saveimage_unimeta.nodes.
"""

from __future__ import annotations

# Legacy compatibility stub: re-export SaveCustomMetadataRules from the new module.
from .rules_writer import SaveCustomMetadataRules

# Provide piexif at this module level so tests can monkeypatch here and the save node can reference it.
try:  # Pillow EXIF helper (optional in test env)
    import piexif  # type: ignore
    import piexif.helper  # type: ignore
except Exception:  # noqa: BLE001

    class _PieExifStub:  # minimal stub for tests
        class ExifIFD:
            UserComment = 0x9286

        class ImageIFD:
            Model = 0x0110
            Make = 0x010F

        @staticmethod
        def dump(_mapping):
            # Inflate size to ~10KB so small max_jpeg_exif_kb thresholds cause fallback in tests
            base = b"stub"
            if len(base) < 10 * 1024:
                base = base * ((10 * 1024 // len(base)) + 1)
            return base[: 10 * 1024]

        @staticmethod
        def insert(_exif_bytes, _path):
            return None

        class HelperStub:  # type: ignore
            class UserComment:
                @staticmethod
                def dump(value, encoding="unicode"):
                    return value.encode("utf-8") if isinstance(value, str) else b""

        helper = HelperStub  # expose attribute name piexif.helper

    piexif = _PieExifStub()  # type: ignore

from ..defs import load_user_definitions  # re-export for legacy tests and used by save node

# Import after defining piexif and load_user_definitions to avoid circular issues
from .save_image import SaveImageWithMetaDataUniversal

__all__ = [
    "SaveCustomMetadataRules",
    "SaveImageWithMetaDataUniversal",
    "load_user_definitions",
    "piexif",
]


def __getattr__(name: str):  # pragma: no cover - thin compatibility layer
    if name == "SaveImageWithMetaDataUniversal":
        from .save_image import SaveImageWithMetaDataUniversal as _C

        return _C
    raise AttributeError(name)
