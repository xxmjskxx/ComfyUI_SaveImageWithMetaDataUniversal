"""Provides a centralized alias for the `piexif` library.

This module ensures that the `piexif` library is available throughout the
`saveimage_unimeta` package, while also providing a fallback stub for testing
environments where `piexif` may not be installed. It attempts to import the
`piexif` object from the `nodes.node` module, which serves as a single point
for monkeypatching in tests. If this import fails, it falls back to a local
stub that mimics the necessary components of the `piexif` library.
"""

from __future__ import annotations

try:
    from .nodes.node import piexif  # noqa: F401
except Exception:  # pragma: no cover - bootstrapping path
    try:
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
