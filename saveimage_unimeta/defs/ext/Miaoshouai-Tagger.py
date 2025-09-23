# https://github.com/miaoshouai/ComfyUI-Miaoshouai-Tagger
from ..meta import MetaField


CAPTURE_FIELD_LIST = {
    "Miaoshouai_Flux_CLIPTextEncode": {
        MetaField.POSITIVE_PROMPT: {"field_name": "caption"},
        MetaField.GUIDANCE:             {"field_name": "guidance"},
    },
}
