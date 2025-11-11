"""Centralized piexif alias used by save node and tests.

We import from the nodes.node module if available to keep a single monkeypatch point.
If that fails (during early import), we provide a local fallback stub identical in shape.
"""

from __future__ import annotations

try:
    from .nodes.node import piexif  # type: ignore  # noqa: F401
except Exception:  # pragma: no cover - bootstrapping path
    try:
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
