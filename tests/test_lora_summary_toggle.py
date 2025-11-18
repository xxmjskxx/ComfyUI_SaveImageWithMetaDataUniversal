import pytest

from saveimage_unimeta.capture import Capture


def build_minimal_pnginfo():
    return {
        "Positive prompt": "a cat",
        "Negative prompt": "",
        # Simulated LoRA entries (individual)
        "Lora_1 Model name": "myLora",
        "Lora_1 Strength (Model)": 0.8,
        "Lora_1 Strength (CLIP)": 0.7,
        # Aggregated summary we expect capture/gen to create/inject in real flows
        "LoRAs": "myLora(0.8/0.7)",
    }


@pytest.mark.parametrize(
    "ui_flag, env_flag, expect_summary",
    [
        (True, False, True),  # UI forces include
        (False, False, False),  # UI suppresses
        (None, False, True),  # Default include when no env suppression and no UI override
        (None, True, False),  # Env suppression when no UI override
        (True, True, True),  # UI include overrides env suppression
        (False, True, False),  # UI suppress overrides (still suppressed)
    ],
)
def test_include_lora_summary_toggle(monkeypatch, ui_flag, env_flag, expect_summary):
    pnginfo = build_minimal_pnginfo()

    # Environment setup
    if env_flag:
        monkeypatch.setenv("METADATA_NO_LORA_SUMMARY", "1")
    else:
        monkeypatch.delenv("METADATA_NO_LORA_SUMMARY", raising=False)

    kwargs = {}
    if ui_flag is not None:
        kwargs["include_lora_summary"] = ui_flag

    params = Capture.gen_parameters_str(pnginfo, **kwargs)

    has_summary = "LoRAs:" in params
    mismatch_msg = (
        "Mismatch: ui_flag="
        f"{ui_flag} env_flag={env_flag} expected {expect_summary} got {has_summary}\n"
        f"Parameters:\n{params}"
    )
    assert has_summary == expect_summary, mismatch_msg
    # Individual entry should never disappear
    assert "Lora_1 Model name" in params or "myLora" in params  # basic safeguard
