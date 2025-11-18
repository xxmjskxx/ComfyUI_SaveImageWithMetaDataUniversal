import os
import tempfile
import shutil

import folder_paths

from saveimage_unimeta.utils.lora import build_lora_index, find_lora_info


def test_lora_st_extension_indexing(monkeypatch):
    # Create a temporary directory to simulate a loras search path
    temp_root = tempfile.mkdtemp(prefix="loras_st_")
    try:
        # Create fake .st LoRA file
        fake_name = "mystyle"
        fake_path = os.path.join(temp_root, fake_name + ".st")
        with open(fake_path, "wb") as f:
            f.write(b"dummy lora contents")

        # Provide folder_paths.get_folder_paths mock
        def _mock_get_folder_paths(kind):  # noqa: D401
            if kind == "loras":
                return [temp_root]
            return []

        monkeypatch.setattr(folder_paths, "get_folder_paths", _mock_get_folder_paths)
        # Reset internal index flags (module globals)
        from saveimage_unimeta.utils import lora as lora_mod

        lora_mod._LORA_INDEX = None
        lora_mod._LORA_INDEX_BUILT = False

        build_lora_index()
        info = find_lora_info(fake_name)
        assert info is not None, "Expected .st LoRA to be indexed"
        assert info["filename"].endswith(".st")
        assert os.path.abspath(info["abspath"]) == os.path.abspath(fake_path)
    finally:
        shutil.rmtree(temp_root)
