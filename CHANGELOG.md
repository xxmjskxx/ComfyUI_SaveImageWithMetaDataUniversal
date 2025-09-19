# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- (placeholder)

## [0.2.0] - 2025-09-19
### Added
- `MetadataRuleScanner` node to configure metadata rule scanning and force inclusion of specified node classes.
- Global registry `FORCED_INCLUDE_CLASSES` with helpers: `set_forced_include`, `clear_forced_include`.

### Changed
- Moved `force_include_node_class` input from `SaveImageWithMetaDataUniversal` to dedicated `MetadataRuleScanner` node.
- Improved description wrapping for `SaveImageWithMetaDataUniversal` to satisfy style guidance.

### Metadata Fallback
- Maintained multi-stage JPEG metadata fallback: full EXIF → reduced-exif → minimal → COM marker with fallback annotation.

### Notes
- Remaining long lines in `node.py` are legacy and will be incrementally cleaned.

