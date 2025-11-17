SAMPLE_PARAMS = (
    "Steps: 30, Sampler: Euler, CFG scale: 7, Seed: 123, Model: foo, Model hash: deadbeef, "
    "VAE: bar, VAE hash: abcdef01, Size: 512x512, Weight dtype: fp16, Batch size: 2, ExtraKey1: X, "
    "ExtraKey2: Y, Lora_A: (loraA:0.8), Lora_B: (loraB:0.5)"
)


def test_build_minimal_parameters_trims(node_instance):
    trimmed = node_instance._build_minimal_parameters(SAMPLE_PARAMS)
    assert len(trimmed) < len(SAMPLE_PARAMS)
    assert "Weight dtype" not in trimmed
    assert "ExtraKey1" not in trimmed and "ExtraKey2" not in trimmed
    for keep in [
        "Steps:",
        "Sampler:",
        "CFG scale:",
        "Seed:",
        "Model:",
        "Model hash:",
        "VAE:",
        "VAE hash:",
        "Lora_A",
        "Lora_B",
    ]:  # noqa: E501
        assert keep.split(":")[0] in trimmed
