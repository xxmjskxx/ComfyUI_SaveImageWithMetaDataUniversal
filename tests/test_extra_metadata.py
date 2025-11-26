"""Tests for the CreateExtraMetaDataUniversal node.

These tests verify:
1. No stale cache issue with mutable default arguments
2. Chaining multiple CreateExtraMetaData nodes works correctly
3. Empty keys are not added to the metadata
4. Extra metadata ordering appears after Hashes in parameter strings
"""

import os

os.environ["METADATA_TEST_MODE"] = "1"

from saveimage_unimeta.nodes.extra_metadata import CreateExtraMetaDataUniversal


class TestExtraMetadataNoStaleCache:
    """Tests to ensure no stale cache issue from mutable default arguments."""

    def test_separate_instances_no_shared_state(self):
        """Verify that separate invocations don't share mutable state."""
        node = CreateExtraMetaDataUniversal()

        # First call with some metadata
        result1 = node.create_extra_metadata(key1="Artist", value1="Alice")
        meta1 = result1[0]

        # Second call should start fresh, not inherit from first call
        result2 = node.create_extra_metadata(key1="Location", value1="Paris")
        meta2 = result2[0]

        # meta1 should only have Artist
        assert "Artist" in meta1
        assert meta1["Artist"] == "Alice"
        assert "Location" not in meta1

        # meta2 should only have Location
        assert "Location" in meta2
        assert meta2["Location"] == "Paris"
        assert "Artist" not in meta2

    def test_multiple_calls_no_accumulation(self):
        """Verify metadata doesn't accumulate across multiple calls without chaining."""
        node = CreateExtraMetaDataUniversal()

        # Make several sequential calls
        result1 = node.create_extra_metadata(key1="Key1", value1="Value1")
        result2 = node.create_extra_metadata(key1="Key2", value1="Value2")
        result3 = node.create_extra_metadata(key1="Key3", value1="Value3")

        # Each should only have their own key
        assert len([k for k in result1[0] if k]) == 1
        assert len([k for k in result2[0] if k]) == 1
        assert len([k for k in result3[0] if k]) == 1

        assert "Key1" in result1[0]
        assert "Key2" in result2[0]
        assert "Key3" in result3[0]

        # None should have the other keys
        assert "Key2" not in result1[0]
        assert "Key3" not in result1[0]
        assert "Key1" not in result2[0]
        assert "Key3" not in result2[0]
        assert "Key1" not in result3[0]
        assert "Key2" not in result3[0]


class TestExtraMetadataChaining:
    """Tests for chaining multiple CreateExtraMetaData nodes."""

    def test_chaining_two_nodes(self):
        """Verify chaining two CreateExtraMetaData nodes works correctly."""
        node1 = CreateExtraMetaDataUniversal()
        node2 = CreateExtraMetaDataUniversal()

        # First node creates initial metadata
        result1 = node1.create_extra_metadata(key1="Artist", value1="Alice")
        meta1 = result1[0]

        # Second node receives first node's output and adds more
        result2 = node2.create_extra_metadata(
            extra_metadata=meta1,
            key1="Location",
            value1="Paris",
        )
        meta2 = result2[0]

        # Final result should have both
        assert "Artist" in meta2
        assert meta2["Artist"] == "Alice"
        assert "Location" in meta2
        assert meta2["Location"] == "Paris"

        # Original should be unchanged (no mutation)
        assert "Location" not in meta1

    def test_chaining_multiple_nodes(self):
        """Verify chaining many CreateExtraMetaData nodes works correctly."""
        nodes = [CreateExtraMetaDataUniversal() for _ in range(5)]

        # Chain the nodes together
        metadata = None
        for i, node in enumerate(nodes):
            result = node.create_extra_metadata(
                extra_metadata=metadata,
                key1=f"Key{i}",
                value1=f"Value{i}",
            )
            metadata = result[0]

        # Final metadata should have all keys
        for i in range(5):
            assert f"Key{i}" in metadata
            assert metadata[f"Key{i}"] == f"Value{i}"

    def test_chaining_with_multiple_keys_per_node(self):
        """Verify chaining with multiple key-value pairs per node."""
        node1 = CreateExtraMetaDataUniversal()
        node2 = CreateExtraMetaDataUniversal()

        # First node with multiple keys
        result1 = node1.create_extra_metadata(
            key1="Artist",
            value1="Alice",
            key2="Year",
            value2="2024",
        )
        meta1 = result1[0]

        # Second node adds more
        result2 = node2.create_extra_metadata(
            extra_metadata=meta1,
            key1="Location",
            value1="Paris",
            key2="Style",
            value2="Impressionism",
        )
        meta2 = result2[0]

        # All four keys should be present
        assert meta2["Artist"] == "Alice"
        assert meta2["Year"] == "2024"
        assert meta2["Location"] == "Paris"
        assert meta2["Style"] == "Impressionism"


class TestExtraMetadataEmptyKeys:
    """Tests for handling empty keys."""

    def test_empty_keys_not_added(self):
        """Verify that empty keys are not added to metadata."""
        node = CreateExtraMetaDataUniversal()

        result = node.create_extra_metadata(
            key1="Artist",
            value1="Alice",
            key2="",  # Empty key
            value2="ShouldNotAppear",
            key3="Year",
            value3="2024",
            key4="",  # Empty key
            value4="AlsoShouldNotAppear",
        )
        metadata = result[0]

        # Only non-empty keys should be present
        assert "Artist" in metadata
        assert "Year" in metadata
        assert "" not in metadata
        # Values for empty keys should not appear
        assert len(metadata) == 2

    def test_all_empty_keys_returns_empty_dict(self):
        """Verify that all empty keys returns an empty dict."""
        node = CreateExtraMetaDataUniversal()

        result = node.create_extra_metadata(
            key1="",
            value1="Value1",
            key2="",
            value2="Value2",
        )
        metadata = result[0]

        # Should be empty
        assert len(metadata) == 0


class TestExtraMetadataOrdering:
    """Tests for extra metadata ordering in parameter strings."""

    def test_extra_metadata_after_hashes(self):
        """Verify extra metadata appears after Hashes in parameter strings."""
        from saveimage_unimeta.capture import Capture

        # Create a pnginfo_dict with Hashes and extra metadata
        pnginfo_dict = {
            "Positive prompt": "a beautiful landscape",
            "Negative prompt": "blurry",
            "Steps": 20,
            "Sampler": "euler",
            "CFG scale": 7.5,
            "Seed": 12345,
            "Model": "test_model",
            "Hashes": '{"model": "abc123"}',
            "CustomField1": "CustomValue1",  # Extra metadata
            "AnotherCustom": "AnotherValue",  # Extra metadata (sorts before "C")
            "__extra_metadata_keys": ["CustomField1", "AnotherCustom"],
        }

        # Generate parameter string
        param_str = Capture.gen_parameters_str(pnginfo_dict)

        # Find positions of Hashes and extra metadata
        hashes_pos = param_str.find("Hashes:")
        custom1_pos = param_str.find("CustomField1:")
        another_pos = param_str.find("AnotherCustom:")

        # Both custom fields should appear after Hashes
        assert hashes_pos != -1, "Hashes should be present"
        assert custom1_pos != -1, "CustomField1 should be present"
        assert another_pos != -1, "AnotherCustom should be present"
        assert hashes_pos < custom1_pos, "CustomField1 should come after Hashes"
        assert hashes_pos < another_pos, "AnotherCustom should come after Hashes"

    def test_extra_metadata_before_version(self):
        """Verify extra metadata appears before Metadata generator version."""
        from saveimage_unimeta.capture import Capture

        pnginfo_dict = {
            "Positive prompt": "test",
            "Negative prompt": "",
            "CustomField": "CustomValue",
            "Metadata generator version": "1.0.0",
            "__extra_metadata_keys": ["CustomField"],
        }

        param_str = Capture.gen_parameters_str(pnginfo_dict)

        custom_pos = param_str.find("CustomField:")
        version_pos = param_str.find("Metadata generator version:")

        assert custom_pos != -1
        assert version_pos != -1
        assert custom_pos < version_pos, "Extra metadata should come before version"

    def test_clip_fields_ordering(self):
        """Ensure CLIP fields remain in the core block before the Hashes + extra metadata tail."""
        from saveimage_unimeta.capture import Capture

        pnginfo_dict = {
            "Positive prompt": "flux",
            "Negative prompt": "",
            "Steps": 4,
            "Sampler": "dpmpp_2m Karras",
            "Model": "flux.safetensors",
            "CLIP_1 Model name": "umt5_xxl_fp8",
            "Hashes": '{"model": "cafebabe"}',
            "CustomField": "CustomValue",
            "Metadata generator version": "1.2.3",
            "__extra_metadata_keys": ["CustomField"],
        }

        param_str = Capture.gen_parameters_str(pnginfo_dict)

        clip_pos = param_str.find("CLIP_1 Model name:")
        hashes_pos = param_str.find("Hashes:")
        custom_pos = param_str.find("CustomField:")

        assert clip_pos != -1, "CLIP field missing"
        assert hashes_pos != -1, "Hashes missing"
        assert custom_pos != -1, "Extra metadata missing"
        assert clip_pos < hashes_pos < custom_pos, "Ordering should be CLIP -> Hashes -> extras"


class TestExtraMetadataIntegration:
    """Integration tests combining multiple aspects."""

    def test_chained_nodes_dont_pollute_subsequent_workflows(self):
        """Simulate the reported bug: subsequent workflows shouldn't see stale data."""
        node = CreateExtraMetaDataUniversal()

        # Simulate first workflow
        workflow1_result = node.create_extra_metadata(
            key1="Workflow",
            value1="First",
            key2="Author",
            value2="Alice",
        )
        workflow1_meta = workflow1_result[0]

        # Simulate second workflow (different data, no chaining)
        workflow2_result = node.create_extra_metadata(
            key1="Workflow",
            value1="Second",
        )
        workflow2_meta = workflow2_result[0]

        # Second workflow should only have its own data
        assert workflow2_meta["Workflow"] == "Second"
        assert "Author" not in workflow2_meta

        # First workflow's data should be unchanged
        assert workflow1_meta["Workflow"] == "First"
        assert workflow1_meta["Author"] == "Alice"

    def test_disconnected_node_no_stale_data(self):
        """Simulate disconnecting a CreateExtraMetaData node - no stale data should remain."""
        node1 = CreateExtraMetaDataUniversal()
        node2 = CreateExtraMetaDataUniversal()

        # First run: node1 -> node2 (chained)
        meta1 = node1.create_extra_metadata(key1="Key1", value1="Value1")[0]
        chained_meta = node2.create_extra_metadata(
            extra_metadata=meta1,
            key1="Key2",
            value1="Value2",
        )[0]

        assert "Key1" in chained_meta
        assert "Key2" in chained_meta

        # Second run: node2 only (node1 disconnected, so no extra_metadata passed)
        disconnected_meta = node2.create_extra_metadata(
            key1="Key3",
            value1="Value3",
        )[0]

        # Should only have Key3, not Key1 or Key2 from previous runs
        assert "Key3" in disconnected_meta
        assert "Key1" not in disconnected_meta
        assert "Key2" not in disconnected_meta
