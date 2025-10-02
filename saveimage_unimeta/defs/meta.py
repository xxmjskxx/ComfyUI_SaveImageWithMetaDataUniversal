from enum import IntEnum


class MetaField(IntEnum):
    MODEL_NAME = 0
    MODEL_HASH = 1
    VAE_NAME = 2
    VAE_HASH = 3
    POSITIVE_PROMPT = 10
    NEGATIVE_PROMPT = 11
    CLIP_SKIP = 12
    SEED = 20
    STEPS = 21
    CFG = 22
    SAMPLER_NAME = 23
    # Backwards compatibility / test aliases
    SAMPLER = 23  # alias for SAMPLER_NAME expected by tests
    SCHEDULER = 24
    GUIDANCE = 25
    DENOISE = 26
    # CLIP_1 = 27
    # CLIP_2 = 28
    CLIP_MODEL_NAME = 27  # inputs such as clip_name, clip_name1, clip_name2
    WEIGHT_DTYPE = 29  # found on Load Diffusion Model node
    IMAGE_WIDTH = 30
    IMAGE_HEIGHT = 31
    # Aliases matching test expectations
    WIDTH = 30  # alias for IMAGE_WIDTH
    HEIGHT = 31  # alias for IMAGE_HEIGHT
    MAX_SHIFT = 32
    BASE_SHIFT = 33
    T5_PROMPT = 34  # input is t5xxl
    CLIP_PROMPT = 35  # input is clip_l
    SHIFT = 36
    EMBEDDING_NAME = 40
    EMBEDDING_HASH = 41
    LORA_MODEL_NAME = 50
    LORA_MODEL_HASH = 51
    LORA_STRENGTH_MODEL = 52
    LORA_STRENGTH_CLIP = 53
    START_STEP = 54  # per-sampler subrange start (Wan / multi-sampler support)
    END_STEP = 55    # per-sampler subrange end (Wan / multi-sampler support)
