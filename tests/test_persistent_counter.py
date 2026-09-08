"""Tests for the persistent (cross-session) collision counter (A)."""
import os

try:  # prefer installed-style path
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.save_image import (
        SaveImageWithMetaDataUniversal,
    )
except ModuleNotFoundError:  # editable checkout fallback
    from saveimage_unimeta.nodes.save_image import SaveImageWithMetaDataUniversal


def _write(path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("x")


def test_first_run_uses_fallback(tmp_path):
    """An empty folder keeps the session fallback counter."""
    assert SaveImageWithMetaDataUniversal._next_free_counter(str(tmp_path), "base", "png", 0) == 0


def test_cross_session_skips_to_next_free(tmp_path):
    """Existing files from a previous session advance past the highest counter."""
    _write(os.path.join(tmp_path, "base_00001_.png"))
    _write(os.path.join(tmp_path, "base_00003_.png"))
    assert SaveImageWithMetaDataUniversal._next_free_counter(str(tmp_path), "base", "png", 0) == 4


def test_extension_isolation(tmp_path):
    """A different format extension does not collide."""
    _write(os.path.join(tmp_path, "base_00001_.jpg"))
    assert SaveImageWithMetaDataUniversal._next_free_counter(str(tmp_path), "base", "png", 0) == 0


def test_prefix_isolation(tmp_path):
    """A different base prefix is ignored."""
    _write(os.path.join(tmp_path, "other_00001_.png"))
    assert SaveImageWithMetaDataUniversal._next_free_counter(str(tmp_path), "base", "png", 0) == 0


def test_malformed_counter_skipped(tmp_path):
    """Non-numeric or wrong-width `_NNNNN_` entries are skipped, not crashed on."""
    _write(os.path.join(tmp_path, "base_00abc_.png"))
    _write(os.path.join(tmp_path, "base_0002_.png"))  # only four digits
    assert SaveImageWithMetaDataUniversal._next_free_counter(str(tmp_path), "base", "png", 0) == 0


def test_race_bump_advances_past_taken_slot(tmp_path):
    """The existence bump advances past an already-taken slot."""
    _write(os.path.join(tmp_path, "base_00000_.png"))
    assert SaveImageWithMetaDataUniversal._next_free_counter(str(tmp_path), "base", "png", 0) == 1


def test_respects_higher_fallback(tmp_path):
    """The session fallback is kept when it is already higher than existing files."""
    _write(os.path.join(tmp_path, "base_00002_.png"))
    assert SaveImageWithMetaDataUniversal._next_free_counter(str(tmp_path), "base", "png", 5) == 5


def test_save_images_skips_existing_file(node_instance, dummy_image):
    """save_images advances past a file left by a previous session."""
    _write(os.path.join(str(node_instance.output_dir), "img_00000_.png"))
    result = node_instance.save_images(images=dummy_image, file_format="png", filename_prefix="img")
    filepath = result["result"][1]
    assert os.path.basename(filepath) == "img_00001_.png"
    assert os.path.exists(filepath)
