"""A legacy module for backward compatibility with ComfyUI custom nodes.

This module serves as a compatibility layer, re-exporting nodes and functions
that have been moved to other locations within the `saveimage_unimeta` package.
It ensures that older workflows that reference the original module paths
continue to function correctly. Additionally, it provides a stub for the `piexif`
library to support testing in environments where it may not be installed.
"""

from __future__ import annotations

# Legacy compatibility stub: re-export SaveCustomMetadataRules from the new module.
from .rules_writer import SaveCustomMetadataRules

# Provide piexif at this module level so tests can monkeypatch here and the save node can reference it.
try:  # Pillow EXIF helper (optional in test env)
    import piexif
    import piexif.helper
except Exception:  # noqa: BLE001

    class _PieExifStub:  # minimal stub for tests
        """A stub for the `piexif` library for use in test environments.

        This class mimics the essential components of the `piexif` library,
        allowing tests to run without requiring the full library to be
        installed. It provides a minimal implementation of the necessary
        classes and methods to simulate EXIF data handling.
        """

        class ExifIFD:
            """A stub for the `ExifIFD` class in `piexif`."""

            UserComment = 0x9286

        class ImageIFD:
            """A stub for the `ImageIFD` class in `piexif`."""

            Model = 0x0110
            Make = 0x010F

        @staticmethod
        def dump(_mapping):
            """Simulate the `dump` method of `piexif`.

            This method returns a fixed-size byte string to simulate the
            behavior of `piexif.dump` for testing purposes.

            Args:
                _mapping: The mapping to be dumped (unused).

            Returns:
                bytes: A byte string of a fixed size.
            """
            # Inflate size to ~10KB so small max_jpeg_exif_kb thresholds cause fallback in tests
            base = b"stub"
            if len(base) < 10 * 1024:
                base = base * ((10 * 1024 // len(base)) + 1)
            return base[: 10 * 1024]

        @staticmethod
        def insert(_exif_bytes, _path):
            """Simulate the `insert` method of `piexif`.

            This method is a no-op, returning `None` to mimic the behavior
            of `piexif.insert`.

            Args:
                _exif_bytes: The EXIF bytes to be inserted (unused).
                _path: The path to insert the EXIF data into (unused).

            Returns:
                None: This method always returns `None`.
            """
            return None

        class HelperStub:
            """A stub for the `helper` module in `piexif`."""

            class UserComment:
                """A stub for the `UserComment` class in `piexif.helper`."""

                @staticmethod
                def dump(value, encoding="unicode"):
                    """Simulate the `dump` method of `UserComment`.

                    This method encodes a string value to bytes, similar to
                    the behavior of `piexif.helper.UserComment.dump`.

                    Args:
                        value: The value to be dumped.
                        encoding (str, optional): The encoding to use. Defaults to "unicode".

                    Returns:
                        bytes: The encoded value as a byte string.
                    """
                    return value.encode("utf-8") if isinstance(value, str) else b""

        helper = HelperStub  # expose attribute name piexif.helper

    piexif = _PieExifStub()

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
    """Provide a compatibility layer for attribute access.

    This function is a fallback for attribute access, allowing for the lazy
    loading of the `SaveImageWithMetaDataUniversal` class. This helps to
-    avoid circular import issues and maintains backward compatibility.

    Args:
        name (str): The name of the attribute being accessed.

    Returns:
        The requested attribute, if it is `SaveImageWithMetaDataUniversal`.

    Raises:
        AttributeError: If the requested attribute is not found.
    """
    if name == "SaveImageWithMetaDataUniversal":
        from .save_image import SaveImageWithMetaDataUniversal as _C

        return _C
    raise AttributeError(name)
