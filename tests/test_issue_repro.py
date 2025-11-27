
import sys
from unittest.mock import MagicMock

# Mock folder_paths and nodes module before importing anything else
sys.modules['folder_paths'] = MagicMock()
sys.modules['nodes'] = MagicMock()
sys.modules['server'] = MagicMock()

import unittest
from unittest.mock import patch
import os

# Ensure the package is in path
# Assumes the test is run with PYTHONPATH set correctly to include the repo root or where saveimage_unimeta is importable

from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.utils import pathresolve

class TestPathResolveBug(unittest.TestCase):
    @patch('ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.utils.pathresolve.folder_paths')
    @patch('os.path.exists')
    def test_probe_folder_quoted_filename_with_extension(self, mock_exists, mock_folder_paths):
        # Setup
        kind = "checkpoints"
        filename = "model.safetensors"
        quoted_filename = f"'{filename}'"

        # Mock folder_paths.get_full_path to return the path if the name matches filename, else None
        def get_full_path_side_effect(kind, name):
            if name == filename:
                return f"/path/to/{filename}"
            return None

        mock_folder_paths.get_full_path.side_effect = get_full_path_side_effect

        # Mock os.path.exists to return True for the resolved path
        def exists_side_effect(path):
            if path == f"/path/to/{filename}":
                return True
            return False

        mock_exists.side_effect = exists_side_effect

        # Call _probe_folder with the quoted filename
        result = pathresolve._probe_folder(kind, quoted_filename)

        # Assert
        self.assertEqual(result, f"/path/to/{filename}")

if __name__ == '__main__':
    unittest.main()
