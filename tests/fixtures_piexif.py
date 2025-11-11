"""Shared piexif stub builder for EXIF-related tests.

Reduces duplication of large inline PStub classes across tests.
"""
from __future__ import annotations

import importlib
from typing import Literal


def _load_real_piexif():
    try:  # pragma: no cover
        import piexif as real_piexif  # type: ignore
    except (ImportError, ModuleNotFoundError):
        mod = importlib.import_module('ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.node')
        real_piexif = getattr(mod, 'piexif')
    return real_piexif


def build_piexif_stub(mode: Literal['huge', 'small', 'adaptive']) -> object:
    real = _load_real_piexif()

    class PStub:  # pragma: no cover - deterministic
        ImageIFD = getattr(real, 'ImageIFD', type('ImageIFD', (), {'Model': 0x0110, 'Make': 0x010F}))
        ExifIFD = getattr(real, 'ExifIFD', type('ExifIFD', (), {'UserComment': 0x9286}))
        _UserComment = type(
            'UC',
            (),
            {'dump': staticmethod(lambda v, encoding="unicode": v.encode('utf-8') if isinstance(v, str) else b'')},
        )
        helper = getattr(real, 'helper', type('H', (), {'UserComment': _UserComment}))

        @staticmethod
        def dump(d):
            if mode == 'huge':
                return b'Z' * (128 * 1024)
            if mode == 'small':
                return b'SMALL'
            # adaptive: emulate size difference for reduced-exif stage
            if '0th' in d and d['0th']:
                return b'A' * (40 * 1024)
            return b'B' * (2 * 1024)

        @staticmethod
        def insert(exif_bytes, path):
            return None

    return PStub


import pytest  # noqa: E402


@pytest.fixture
def piexif_stub_factory():
    return build_piexif_stub
