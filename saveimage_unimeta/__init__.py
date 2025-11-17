"""Initializes the `saveimage_unimeta` package and monkeypatches ComfyUI.

This module is the entry point for the `saveimage_unimeta` package. It sets up
the necessary hooks into the ComfyUI execution flow by monkeypatching the
`execution` module. This allows the package to intercept the execution of the
prompt and the retrieval of input data, which is essential for capturing the
metadata.

The module also defines environment flag constants for configuring the behavior
of the metadata capture and provides stubs for the `execution` module and hook
functions to allow for isolated unit testing.
"""
import functools  # noqa: N999 - module path mandated by ComfyUI folder naming
import os

TEST_MODE = bool(os.environ.get("METADATA_TEST_MODE"))

# Exposed environment flag constants for discoverability. These are not
# enforced here; downstream modules re-read os.environ dynamically at call time.
# Users can set them prior to launching ComfyUI. All default to False/absent.
METADATA_ENV_FLAGS = {
    "METADATA_TEST_MODE": False,  # Multiline deterministic params formatting
    "METADATA_NO_HASH_DETAIL": False,  # Suppress structured Hash detail JSON block
    "METADATA_NO_LORA_SUMMARY": False,  # Suppress aggregated LoRAs summary line
    "METADATA_DEBUG_PROMPTS": False,  # Verbose dual prompt handling logging
    "METADATA_DEBUG_LORA": False,  # Detailed LoRA parsing diagnostics
    "METADATA_DEBUG": False,  # General debug enablement
    # Future: "METADATA_MAX_JPEG_EXIF_KB" (UI param presently preferred)
}
if not TEST_MODE:  # Only import heavy hook & nodes when running inside ComfyUI
    from .hook import pre_execute, pre_get_input_data
else:  # Provide no-op placeholders for tests

    def pre_execute(*_, **__):  # type: ignore
        """A no-op placeholder for the `pre_execute` hook in test mode."""
        return None

    def pre_get_input_data(*_, **__):  # type: ignore
        """A no-op placeholder for the `pre_get_input_data` hook in test mode."""
        return None


# The real ComfyUI runtime provides an 'execution' module. During isolated unit tests
# that run outside ComfyUI, this import fails; we substitute a lightweight stub so
# that importing capture logic (and enums) still works. The stub only needs the
# attributes we monkeypatch below.
try:  # pragma: no cover - exercised implicitly
    import execution
except Exception:  # noqa: BLE001 - broad to ensure test environment resilience

    class _ExecutionStub:  # pragma: no cover
        """A stub for the ComfyUI `execution` module for use in tests."""

        class PromptExecutor:  # minimal surface for monkeypatch
            """A stub for the `PromptExecutor` class."""

            def execute(self, *_, **__):
                """A no-op `execute` method."""
                return None

        def get_input_data(self, *_, **__):
            """A no-op `get_input_data` method."""
            return None

    execution = _ExecutionStub()


def prefix_function(function, prefunction):
    """Wraps a function to execute a prefunction before it.

    This utility function takes two functions, `function` and `prefunction`,
    and returns a new function that, when called, first executes `prefunction`
    with the same arguments and then executes and returns the result of the
    original `function`.

    Args:
        function (callable): The original function to be wrapped.
        prefunction (callable): The function to be executed before the
            original function.

    Returns:
        callable: The wrapped function.
    """

    @functools.wraps(function)
    def run(*args, **kwargs):
        prefunction(*args, **kwargs)
        return function(*args, **kwargs)

    return run


if not TEST_MODE:
    try:  # Guard in case stub lacks attributes
        execution.PromptExecutor.execute = prefix_function(execution.PromptExecutor.execute, pre_execute)
        execution.get_input_data = prefix_function(execution.get_input_data, pre_get_input_data)
    except Exception:  # noqa: BLE001
        # In tests using the stub we silently allow failure; capture features will be limited
        pass
