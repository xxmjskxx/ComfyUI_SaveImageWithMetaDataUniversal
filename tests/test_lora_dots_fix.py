import os
import tempfile
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from saveimage_unimeta.utils.pathresolve import EXTENSION_ORDER

project_root = Path(__file__).parent.parent
if str(project_root) not in os.sys.path:
    os.sys.path.insert(0, str(project_root))

try:
    from saveimage_unimeta.defs.formatters import calc_lora_hash, calc_model_hash, calc_vae_hash, calc_unet_hash

    FORMATTERS_AVAILABLE = True
except ImportError as e:  # pragma: no cover
    logging.warning("Could not import formatters: %s", e)
    FORMATTERS_AVAILABLE = False


TEST_CASES_LORA = [
    ("dark_gothic_fantasy_xl_3.01", "dark_gothic_fantasy_xl_3.01.safetensors"),
    ("model.v1.2.3", "model.v1.2.3.safetensors"),
    ("style.model.v2.1", "style.model.v2.1.safetensors"),
    ("lora.with.dots", "lora.with.dots.safetensors"),
    ("version.1.2.3.final", "version.1.2.3.final.safetensors"),
    ("normal_lora", "normal_lora.safetensors"),
    ("lora-with-dashes", "lora-with-dashes.safetensors"),
    ("lora_with_underscores", "lora_with_underscores.safetensors"),
]


def _mock_folder_paths(temp_dir: str):
    mfp = MagicMock()

    def _get_full_path(folder_type: str, filename: str):
        base_path = os.path.join(temp_dir, folder_type)
        direct = os.path.join(base_path, filename)
        if os.path.exists(direct):
            return direct
        for ext in EXTENSION_ORDER:
            cand = os.path.join(base_path, filename + ext)
            if os.path.exists(cand):
                return cand
        raise FileNotFoundError(filename)

    mfp.get_full_path = _get_full_path  # type: ignore[attr-defined]
    return mfp


@pytest.mark.skipif(not FORMATTERS_AVAILABLE, reason="Formatters not available")
@pytest.mark.parametrize("lora_name,expected_file", TEST_CASES_LORA)
def test_lora_version_numbers_with_dots(lora_name, expected_file):
    with tempfile.TemporaryDirectory() as td:
        lora_dir = os.path.join(td, "loras")
        os.makedirs(lora_dir, exist_ok=True)
        # create file
        with open(os.path.join(lora_dir, expected_file), "w", encoding="utf-8") as f:
            f.write("mock lora content for testing")
        mfp = _mock_folder_paths(td)
        with patch("saveimage_unimeta.defs.formatters.folder_paths", mfp):
            h1 = calc_lora_hash(lora_name, [])
            assert h1 != "N/A" and len(h1) == 10
            h2 = calc_lora_hash(lora_name, [])
            assert h1 == h2


@pytest.mark.skipif(not FORMATTERS_AVAILABLE, reason="Formatters not available")
def test_all_model_types_with_dots():
    test_name = "dark_gothic_fantasy_xl_3.01"
    model_types = [
        ("loras", calc_lora_hash),
        ("checkpoints", calc_model_hash),
        ("vae", calc_vae_hash),
        ("unet", calc_unet_hash),
    ]
    with tempfile.TemporaryDirectory() as td:
        for folder, _hf in model_types:
            d = os.path.join(td, folder)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, f"{test_name}.safetensors"), "w", encoding="utf-8") as f:
                f.write(f"mock {folder} content")
        mfp = _mock_folder_paths(td)
        with patch("saveimage_unimeta.defs.formatters.folder_paths", mfp):
            for folder, hf in model_types:
                h = hf(test_name, [])
                assert h != "N/A" and len(h) == 10


SPLITEXT_CASES = [
    ("dark_gothic_fantasy_xl_3.01", "dark_gothic_fantasy_xl_3", ".01"),
    ("model.v1.2.3", "model.v1.2", ".3"),
    ("file.name.with.dots", "file.name.with", ".dots"),
    ("version.1.2.3.final", "version.1.2.3", ".final"),
    ("normal_file.safetensors", "normal_file", ".safetensors"),
    ("file.safetensors", "file", ".safetensors"),
]


@pytest.mark.parametrize("filename,expected_base,expected_ext", SPLITEXT_CASES)
def test_splitext_behavior_documentation(filename, expected_base, expected_ext):
    base, ext = os.path.splitext(filename)
    assert base == expected_base
    assert ext == expected_ext
