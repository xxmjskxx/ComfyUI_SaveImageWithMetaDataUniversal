from .node import (  # noqa: N999 - package path inherited from external naming constraints
    CreateExtraMetaDataUniversal,
    MetadataRuleScanner,
    SaveCustomMetadataRules,
    SaveGeneratedUserRules,
    SaveImageWithMetaDataUniversal,
    ShowGeneratedUserRules,
)

NODE_CLASS_MAPPINGS = {
    "SaveImageWithMetaDataUniversal": SaveImageWithMetaDataUniversal,
    "CreateExtraMetaDataUniversal": CreateExtraMetaDataUniversal,
    "MetadataRuleScanner": MetadataRuleScanner,
    "SaveCustomMetadataRules": SaveCustomMetadataRules,
    "ShowGeneratedUserRules": ShowGeneratedUserRules,
    "SaveGeneratedUserRules": SaveGeneratedUserRules,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImageWithMetaDataUniversal": "Save Image w/ Metadata Universal",
    "CreateExtraMetaDataUniversal": "Create Extra MetaData",
    "MetadataRuleScanner": "Metadata Rule Scanner",
    "SaveCustomMetadataRules": "Save Custom Metadata Rules",
    "ShowGeneratedUserRules": "Show generated_user_rules.py",
    "SaveGeneratedUserRules": "Save generated_user_rules.py",
}
