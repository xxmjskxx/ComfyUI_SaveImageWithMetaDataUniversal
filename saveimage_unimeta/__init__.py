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
    from .hook import pre_execute, pre_get_input_data  # type: ignore
else:  # Provide no-op placeholders for tests

    def pre_execute(*_, **__):  # type: ignore
        return None

    def pre_get_input_data(*_, **__):  # type: ignore
        return None


# The real ComfyUI runtime provides an 'execution' module. During isolated unit tests
# that run outside ComfyUI, this import fails; we substitute a lightweight stub so
# that importing capture logic (and enums) still works. The stub only needs the
# attributes we monkeypatch below.
try:  # pragma: no cover - exercised implicitly
    import execution  # type: ignore
except Exception:  # noqa: BLE001 - broad to ensure test environment resilience

    class _ExecutionStub:  # pragma: no cover
        class PromptExecutor:  # minimal surface for monkeypatch
            def execute(self, *_, **__):  # noqa: D401 - simple pass-through
                return None

        def get_input_data(self, *_, **__):  # noqa: D401
            return None

    execution = _ExecutionStub()  # type: ignore


# refer. https://stackoverflow.com/a/35758398
def prefix_function(function, prefunction):
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
