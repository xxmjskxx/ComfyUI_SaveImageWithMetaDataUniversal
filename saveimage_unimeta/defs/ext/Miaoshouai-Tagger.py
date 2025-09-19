# https://github.com/miaoshouai/ComfyUI-Miaoshouai-Tagger
from ..meta import MetaField

SAMPLERS = {}

CAPTURE_FIELD_LIST = {
    "Miaoshouai_Flux_CLIPTextEncode": {
        MetaField.POSITIVE_PROMPT: {"field_name": "caption"},
        MetaField.CFG: {"field_name": "guidance"},
    },
}
