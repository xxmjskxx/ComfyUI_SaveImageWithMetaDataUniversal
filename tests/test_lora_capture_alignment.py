import saveimage_unimeta.capture as capture_mod
from saveimage_unimeta.capture import Capture, MetaField, _LoRARecord


def test_gen_loras_preserves_names_when_hashes_missing():
    inputs = {
        MetaField.LORA_MODEL_NAME: ["flux_lora_a.safetensors", "flux_lora_b.safetensors"],
        MetaField.LORA_MODEL_HASH: ["abc123def0"],
        MetaField.LORA_STRENGTH_MODEL: ["0.6", "0.4"],
        MetaField.LORA_STRENGTH_CLIP: ["0.5"],
    }

    pnginfo = Capture.gen_loras(inputs)

    assert pnginfo["Lora_0 Model name"] == "flux_lora_a.safetensors"
    assert pnginfo["Lora_1 Model name"] == "flux_lora_b.safetensors"
    assert "Lora_1 Model hash" in pnginfo
    assert pnginfo["Lora_1 Model hash"] is None

    hashes = Capture.get_hashes_for_civitai(inputs, inputs, pnginfo)
    assert hashes.get("lora:flux_lora_a") == "abc123def0"
    assert "lora:flux_lora_b" not in hashes


def test_hashes_accept_supplied_lora_records():
    inputs = {}
    pnginfo = {}
    records = [_LoRARecord("standalone_lora.safetensors", "deadbeef22", None, None)]

    hashes = Capture.get_hashes_for_civitai(inputs, inputs, pnginfo, records)

    assert hashes["lora:standalone_lora"] == "deadbeef22"


def test_calc_lora_hash_overrides_duplicate_capture(monkeypatch):
    calls = []

    def fake_calc(name, _):
        calls.append(name)
        lookup = {
            "flux_lora_a.safetensors": "foo1111111",
            "flux_lora_b.safetensors": "bar2222222",
            "flux\\fashion\\closeupfilm.safetensors": "special33333",
        }
        return lookup.get(name, "N/A")

    monkeypatch.setattr(capture_mod, "calc_lora_hash", fake_calc)

    inputs = {
        MetaField.LORA_MODEL_NAME: [
            "flux_lora_a.safetensors",
            ("node42", "flux\\fashion\\closeupfilm.safetensors"),
            "flux_lora_b.safetensors",
        ],
        MetaField.LORA_MODEL_HASH: ["abc123def0", "abc123def0", "abc123def0"],
    }

    pnginfo = Capture.gen_loras(inputs)

    assert pnginfo["Lora_0 Model hash"] == "foo1111111"
    assert pnginfo["Lora_1 Model hash"] == "special33333"
    assert pnginfo["Lora_2 Model hash"] == "bar2222222"
    assert calls == [
        "flux_lora_a.safetensors",
        "flux\\fashion\\closeupfilm.safetensors",
        "flux_lora_b.safetensors",
    ]


def test_numeric_lora_entries_are_dropped(monkeypatch):
    monkeypatch.setattr(capture_mod, "calc_lora_hash", lambda *args, **kwargs: "hash-ok")

    inputs = {
        MetaField.LORA_MODEL_NAME: ["1.0", "valid_lora.safetensors", "None"],
        MetaField.LORA_MODEL_HASH: ["bad", "goodhash", ""],
    }

    pnginfo = Capture.gen_loras(inputs)

    assert list(pnginfo.keys()) == [
        "Lora_0 Model name",
        "Lora_0 Model hash",
    ]
    assert pnginfo["Lora_0 Model name"] == "valid_lora.safetensors"


def test_clip_and_model_strengths_are_not_swapped():
    inputs = {
        MetaField.LORA_MODEL_NAME: ["flux_lora_a.safetensors", "flux_lora_b.safetensors"],
        MetaField.LORA_MODEL_HASH: ["abc123def0", "9998887776"],
        MetaField.LORA_STRENGTH_MODEL: [0.96, 1.05],
        MetaField.LORA_STRENGTH_CLIP: [1.02, 0.98],
    }

    pnginfo = Capture.gen_loras(inputs)

    assert pnginfo["Lora_0 Strength model"] == 0.96
    assert pnginfo["Lora_0 Strength clip"] == 1.02
    assert pnginfo["Lora_1 Strength model"] == 1.05
    assert pnginfo["Lora_1 Strength clip"] == 0.98
