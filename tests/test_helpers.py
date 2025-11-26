"""Shared test helpers for capture tests.

This module provides reusable helpers to avoid code duplication across test modules.
"""

from __future__ import annotations

import pytest


def install_prompt_environment(monkeypatch: pytest.MonkeyPatch, capture_mod, prompt: dict[str, dict]) -> None:
    """Install a deterministic hook/prompt environment for capture tests.

    This helper sets up:
    - A DummyHook with the given prompt
    - NODE_CLASS_MAPPINGS with stub classes for each node in the prompt
    - A fake get_input_data that returns node inputs

    Args:
        monkeypatch: pytest MonkeyPatch fixture
        capture_mod: The capture module being tested
        prompt: Dictionary of node_id -> node configuration
    """

    class DummyPromptExecuter:
        class Caches:
            outputs = {}

        caches = Caches()

    class DummyHook:
        current_prompt = prompt
        current_extra_data = {}
        prompt_executer = DummyPromptExecuter()

    monkeypatch.setattr(capture_mod, "hook", DummyHook)

    node_classes = {}
    for node in prompt.values():
        class_type = node["class_type"]
        if class_type not in node_classes:
            node_classes[class_type] = type(f"{class_type}Stub", (), {})
    monkeypatch.setattr(capture_mod, "NODE_CLASS_MAPPINGS", node_classes)

    def fake_get_input_data(node_inputs, obj_class, node_id, outputs, dyn_prompt, extra):
        del obj_class, node_id, outputs, dyn_prompt, extra
        return (node_inputs,)

    monkeypatch.setattr(capture_mod, "get_input_data", fake_get_input_data)
