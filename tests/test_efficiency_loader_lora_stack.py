"""Test LoRA capture from Efficient Loader with lora_stack inputs.

This test validates that LoRAs loaded through a lora_stack input connection
to an Efficient Loader are properly captured in metadata. The issue reported
is that "Efficient Loader" with lora_stack was working but recently broke,
while "Eff. Loader SDXL" with lora_stack still works correctly.
"""
import os
import pytest

# Enable test mode before importing capture
os.environ["METADATA_TEST_MODE"] = "1"

import saveimage_unimeta.capture as cap
from saveimage_unimeta.capture import Capture
from saveimage_unimeta.defs import load_user_definitions
from saveimage_unimeta.defs.meta import MetaField


REQUIRED_NODE_CLASSES = {
    "Efficient Loader",
    "Eff. Loader SDXL",
    "KSampler Adv. (Efficient)",
    "KSampler SDXL (Eff.)",
    "LoRA Stacker",
    "CR LoRA Stack",
}


@pytest.fixture(autouse=True)
def patch_capture_runtime(monkeypatch):
    """Normalize get_input_data and node mapping so tests control inputs."""

    def fake_get_input_data(node_inputs, obj_class, node_id, outputs_compat, dyn_prompt, extra):
        normalized = {}
        for key, raw in node_inputs.items():
            if isinstance(raw, list | tuple):  # noqa: UP038
                normalized[key] = list(raw)
            else:
                normalized[key] = [raw]
        return (normalized,)

    monkeypatch.setattr(cap, "get_input_data", fake_get_input_data)
    monkeypatch.setattr(
        cap,
        "NODE_CLASS_MAPPINGS",
        {name: object for name in REQUIRED_NODE_CLASSES},
        raising=False,
    )
    load_user_definitions(required_classes=None, suppress_missing_log=True)
    yield


def _install_hook(monkeypatch, workflow, outputs=None):
    outputs_map = outputs or {}

    class MockHook:
        current_prompt = workflow
        current_extra_data = {}

        class MockPromptExecuter:
            class MockCaches:
                outputs = outputs_map

            caches = MockCaches()

        prompt_executer = MockPromptExecuter()

    monkeypatch.setattr(cap, "hook", MockHook)


@pytest.fixture(name="workflow_with_lora_stack")
def fixture_workflow_with_lora_stack():
    """Simplified workflow: Efficient Loader <- LoRA Stacker <- CR LoRA Stack."""
    return {
        "4": {  # KSampler Adv. (Efficient) - the save node traces back from here
            "class_type": "KSampler Adv. (Efficient)",
            "inputs": {
                "noise_seed": [457],
                "steps": [25],
                "cfg": [6.0],
                "sampler_name": ["dpmpp_2m"],
                "scheduler": ["karras"],
                "model": ["7", 0],
                "positive": ["7", 1],
                "negative": ["7", 2],
            },
        },
        "7": {  # Efficient Loader with lora_stack from node 8, lora_name="None"
            "class_type": "Efficient Loader",
            "inputs": {
                "ckpt_name": ["cyberrealistic_v50.safetensors"],
                "lora_name": ["None"],  # No inline LoRA
                "lora_model_strength": [1.0],
                "lora_clip_strength": [1.0],
                "positive": ["1boy, mask"],
                "negative": ["lowres"],
                "lora_stack": ["8", 0],  # Connected to LoRA Stacker
            },
        },
        "8": {  # LoRA Stacker with lora_stack from node 17
            "class_type": "LoRA Stacker",
            "inputs": {
                "lora_name_1": ["lora1.safetensors"],
                "lora_wt_1": [1.0],
                "lora_name_2": ["lora2.safetensors"],
                "lora_wt_2": [0.8],
                "lora_stack": ["17", 0],  # Connected to CR LoRA Stack
            },
        },
        "17": {  # CR LoRA Stack with 1 enabled LoRA
            "class_type": "CR LoRA Stack",
            "inputs": {
                "switch_1": ["On"],
                "lora_name_1": ["lora3.safetensors"],
                "model_weight_1": [0.7],
                "clip_weight_1": [0.69],
                "switch_2": ["Off"],
                "lora_name_2": ["None"],
            },
        },
    }


@pytest.fixture(name="workflow_sdxl_with_lora_stack")
def fixture_workflow_sdxl_with_lora_stack():
    """Eff. Loader SDXL with lora_stack - this should work correctly."""
    return {
        "3": {  # KSampler SDXL (Eff.)
            "class_type": "KSampler SDXL (Eff.)",
            "inputs": {
                "noise_seed": [790],
                "steps": [8],
                "cfg": [7.5],
                "sampler_name": ["heun"],
                "scheduler": ["AYS SDXL"],
                "sdxl_tuple": ["2", 0],
            },
        },
        "2": {  # Eff. Loader SDXL with lora_stack from node 8
            "class_type": "Eff. Loader SDXL",
            "inputs": {
                "base_ckpt_name": ["Juggernaut_X_RunDiffusion.safetensors"],
                "positive": ["1boy, dark, gothic"],
                "negative": ["lowres, bad quality"],
                "lora_stack": ["8", 0],
            },
        },
        "8": {  # LoRA Stacker
            "class_type": "LoRA Stacker",
            "inputs": {
                "lora_name_1": ["Hyper-SDXL-8steps-lora.safetensors"],
                "lora_wt_1": [0.2],
            },
        },
    }


def test_efficient_loader_with_lora_stack_captures_upstream_loras(workflow_with_lora_stack, monkeypatch):
    """Test that LoRAs from lora_stack input to Efficient Loader are captured.
    
    This is the failing test - it should capture 3 LoRAs total:
    - 2 from node 8 (LoRA Stacker)
    - 1 from node 17 (CR LoRA Stack)
    
    But currently it captures 0 LoRAs because lora_stack inputs are not being processed.
    """
    # The lora_stack output from nodes needs to be simulated
    # Node 17 (CR LoRA Stack) outputs a lora_stack with 1 LoRA
    # Node 8 (LoRA Stacker) receives that stack and adds 2 more LoRAs
    outputs = {
        "17": {
            "lora_stack": ([
                ("lora3.safetensors", 0.7, 0.69),
            ],)
        },
        "8": {
            "lora_stack": ([
                ("lora1.safetensors", 1.0, 1.0),
                ("lora2.safetensors", 0.8, 0.8),
                ("lora3.safetensors", 0.7, 0.69),  # From node 17
            ],)
        },
    }
    
    # Mock the hook module
    _install_hook(monkeypatch, workflow_with_lora_stack, outputs)
    
    # Get inputs
    inputs = Capture.get_inputs()
    
    # Check that LoRAs were captured
    lora_names = inputs.get(MetaField.LORA_MODEL_NAME, [])
    print(f"\nCaptured LoRA names: {lora_names}")
    
    # Extract just the name values
    names = [Capture._extract_value(entry) for entry in lora_names]
    print(f"Extracted names: {names}")
    
    # Should have 3 LoRAs: lora1, lora2 from node 8, and lora3 from node 17
    # Note: lora3 might appear twice (once from node 17, once from node 8's aggregated stack)
    # but the test should verify that at minimum all 3 are present
    assert len(names) >= 3, f"Expected at least 3 LoRAs but got {len(names)}: {names}"
    assert "lora1.safetensors" in names
    assert "lora2.safetensors" in names
    assert "lora3.safetensors" in names
    
    # Make sure "None" is not captured
    assert "None" not in names


def test_eff_loader_sdxl_with_lora_stack_works(workflow_sdxl_with_lora_stack, monkeypatch):
    """Test that Eff. Loader SDXL with lora_stack works correctly (baseline)."""
    # Simulate the LoRA Stacker output
    outputs = {
        "8": {
            "lora_stack": ([
                ("Hyper-SDXL-8steps-lora.safetensors", 0.2, 0.2),
            ],)
        },
    }
    
    _install_hook(monkeypatch, workflow_sdxl_with_lora_stack, outputs)
    
    inputs = Capture.get_inputs()
    lora_names = inputs.get(MetaField.LORA_MODEL_NAME, [])
    names = [Capture._extract_value(entry) for entry in lora_names]
    
    print(f"\nEff. Loader SDXL captured LoRAs: {names}")
    
    # Should capture the upstream LoRA; duplicates are acceptable when both the
    # loader and stacker report the same entry.
    assert len(names) >= 1, f"Expected at least 1 LoRA but got {len(names)}: {names}"
    assert "Hyper-SDXL-8steps-lora.safetensors" in names


def test_efficient_loader_inline_lora_only(monkeypatch):
    """Test that inline LoRA in Efficient Loader is captured when not 'None'."""
    workflow = {
        "4": {
            "class_type": "KSampler Adv. (Efficient)",
            "inputs": {
                "noise_seed": [457],
                "steps": [25],
                "model": ["10", 0],
            },
        },
        "10": {
            "class_type": "Efficient Loader",
            "inputs": {
                "ckpt_name": ["cyberrealistic_v50.safetensors"],
                "lora_name": ["Hyper-SD15-8steps-CFG-lora.safetensors"],
                "lora_model_strength": [0.7],
                "lora_clip_strength": [0.71],
                "positive": ["scenic mountain view"],
                "negative": ["lowres"],
            },
        },
    }
    
    _install_hook(monkeypatch, workflow, outputs={})
    
    inputs = Capture.get_inputs()
    lora_names = inputs.get(MetaField.LORA_MODEL_NAME, [])
    names = [Capture._extract_value(entry) for entry in lora_names]
    
    print(f"\nInline LoRA captured: {names}")
    
    # Should capture the inline LoRA
    assert len(names) == 1
    assert "Hyper-SD15-8steps-CFG-lora.safetensors" in names


def test_efficient_loader_none_inline_not_captured(monkeypatch):
    """Test that lora_name='None' is not captured as a LoRA."""
    workflow = {
        "4": {
            "class_type": "KSampler Adv. (Efficient)",
            "inputs": {
                "noise_seed": [457],
                "model": ["10", 0],
            },
        },
        "10": {
            "class_type": "Efficient Loader",
            "inputs": {
                "ckpt_name": ["cyberrealistic_v50.safetensors"],
                "lora_name": ["None"],
                "lora_model_strength": [1.0],
                "lora_clip_strength": [1.0],
                "positive": ["test"],
                "negative": ["test"],
            },
        },
    }
    
    _install_hook(monkeypatch, workflow, outputs={})
    
    inputs = Capture.get_inputs()
    lora_names = inputs.get(MetaField.LORA_MODEL_NAME, [])
    names = [Capture._extract_value(entry) for entry in lora_names]
    
    print(f"\nCaptured when lora_name='None': {names}")
    
    # Should NOT capture "None" as a LoRA
    assert len(names) == 0, f"Expected 0 LoRAs but got {len(names)}: {names}"
    assert "None" not in names
