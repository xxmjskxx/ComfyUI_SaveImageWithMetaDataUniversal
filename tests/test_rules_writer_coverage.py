
import os
import shutil
import json
import pytest
import time
from unittest.mock import MagicMock, patch
from saveimage_unimeta.nodes.rules_writer import SaveCustomMetadataRules, _timestamp, _looks_like_timestamp

def test_timestamp_utils():
    ts = _timestamp()
    assert len(ts) == 15
    assert _looks_like_timestamp(ts)
    assert _looks_like_timestamp(ts + "-1")
    assert not _looks_like_timestamp("not-a-timestamp")
    assert not _looks_like_timestamp("20200101-1200") # too short

def test_prune_backups(tmp_path):
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()

    # Create fake backups
    for i in range(5):
        (backups_dir / f"20250101-00000{i}").mkdir() # Oldest
        time.sleep(0.01) # Ensure time diff for safety, though sorted via string

    # Check creation
    assert len(list(backups_dir.iterdir())) == 5

    # Limit to 3
    SaveCustomMetadataRules._prune_backups(str(backups_dir), 3)

    remaining = sorted([p.name for p in backups_dir.iterdir()])
    assert len(remaining) == 3

    assert "20250101-000004" in remaining
    assert "20250101-000000" not in remaining

def test_safe_load_json(tmp_path):
    f = tmp_path / "test.json"
    f.write_text('{"key": "value"}')
    assert SaveCustomMetadataRules._safe_load_json(str(f)) == {"key": "value"}

    # Missing
    assert SaveCustomMetadataRules._safe_load_json(str(tmp_path / "missing.json")) is None

    # Invalid
    f_inv = tmp_path / "invalid.json"
    f_inv.write_text("{invalid")
    assert SaveCustomMetadataRules._safe_load_json(str(f_inv)) is None

def test_create_backup(tmp_path):
    root = tmp_path / "backups"
    root.mkdir()
    src = tmp_path / "src"
    src.mkdir()

    cap = src / "captures.json"
    cap.write_text("{}")

    # Partial backup (only captures exists)
    backup_name = SaveCustomMetadataRules._create_backup(str(root), "ts", str(cap), str(src/"samplers.json"), str(src/"ext.py"))
    assert backup_name == "ts"
    assert (root / "ts" / "captures.json").exists()

    # Collision handling
    backup_name_2 = SaveCustomMetadataRules._create_backup(str(root), "ts", str(cap), str(src/"samplers.json"), str(src/"ext.py"))
    assert backup_name_2 == "ts-1"

    # Empty backup (no source files)
    backup_name_3 = SaveCustomMetadataRules._create_backup(str(root), "empty", "bad", "bad", "bad")
    assert backup_name_3 is None
    assert not (root / "empty").exists()

def test_merge_append_new():
    existing_nodes = {"Node1": {"Meta1": "Rule1"}}
    existing_samplers = {"Sampler1": {"role": "old"}}

    incoming_nodes = {
        "Node1": {"Meta1": "Conflict", "Meta2": "New"},
        "Node2": {"Meta3": "NewNode"}
    }
    incoming_samplers = {
        "Sampler1": {"role": "conflict", "new_role": "val"},
        "Sampler2": {"role": "new"}
    }

    metrics = {
        "mode": "append_new", "backup": None, "nodes_added": 0, "metafields_added": 0,
        "metafields_replaced": 0, "metafields_skipped_conflict": 0,
        "samplers_added": 0, "sampler_roles_added": 0, "sampler_roles_replaced": 0,
        "sampler_roles_skipped_conflict": 0, "pruned": 0, "unchanged": False,
        "restored": False, "partial": False,
    }

    # Without conflict replacement
    writer = SaveCustomMetadataRules()
    out_n, out_s = writer._merge_append_new(existing_nodes, existing_samplers, incoming_nodes, incoming_samplers, False, metrics)

    assert out_n["Node1"]["Meta1"] == "Rule1" # Kept old
    assert out_n["Node1"]["Meta2"] == "New"
    assert out_n["Node2"]["Meta3"] == "NewNode"
    assert metrics["metafields_skipped_conflict"] == 1

    assert out_s["Sampler1"]["role"] == "old"
    assert out_s["Sampler1"]["new_role"] == "val"
    assert out_s["Sampler2"]["role"] == "new"

    # With conflict replacement
    metrics = {k:0 for k in metrics if isinstance(metrics[k], int)} # Reset counters
    metrics["unchanged"] = False

    out_n, out_s = writer._merge_append_new(existing_nodes, existing_samplers, incoming_nodes, incoming_samplers, True, metrics)
    assert out_n["Node1"]["Meta1"] == "Conflict"
    assert metrics["metafields_replaced"] == 1

def test_generate_python_extension(tmp_path):
    # Minimal test to ensure file generation and content structure
    out_file = tmp_path / "generated.py"
    nodes = {"Node1": {"Meta1": {"field_name": "f", "validate": "is_positive_prompt"}}}
    samplers = {}

    SaveCustomMetadataRules._generate_python_extension(str(out_file), nodes, samplers)

    assert out_file.exists()
    content = out_file.read_text()
    assert "class MetaField" in content or "from ..meta import MetaField" in content
    assert '"Node1": {' in content
    assert "MetaField.Meta1:" in content
    # Code uses KNOWN["..."] (double quotes)
    assert 'KNOWN["is_positive_prompt"]' in content

def test_save_rules_integration(tmp_path, monkeypatch):
    writer = SaveCustomMetadataRules()

    with patch("os.makedirs"), \
         patch("builtins.open", new_callable=MagicMock) as mock_open, \
         patch("json.dump") as mock_json_dump, \
         patch("json.load", return_value={}) as mock_json_load, \
         patch("shutil.copy2"), \
         patch("os.listdir", return_value=[]), \
         patch("saveimage_unimeta.nodes.rules_writer.SaveCustomMetadataRules._generate_python_extension"):

         res = writer.save_rules(
             rules_json_string='{"nodes": {"N": {}}, "samplers": {}}',
             save_mode="overwrite",
             backup_before_save=False
         )
         # Should succeed now that we provided content
         assert "mode=overwrite" in res[0]

def test_restore_backup_logic():
    # Test restore path
    writer = SaveCustomMetadataRules()

    with patch("os.makedirs"), \
         patch("os.path.isdir", return_value=True), \
         patch("os.path.exists", return_value=True), \
         patch("shutil.copy2") as mock_copy, \
         patch("saveimage_unimeta.nodes.rules_writer.SaveCustomMetadataRules._create_backup", return_value="ts"):

        res = writer.save_rules(
            rules_json_string="{}",
            restore_backup_set="backup1"
        )

        assert "Restored backup backup1" in res[0]
        # Should have copied 3 files (captures, samplers, py)
        assert mock_copy.call_count >= 3
