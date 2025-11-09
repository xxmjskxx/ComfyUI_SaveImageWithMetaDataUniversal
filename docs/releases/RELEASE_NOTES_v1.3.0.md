# Release Notes - v1.3.0

**Release Date:** 2025-10-31

## Overview

Version 1.3.0 represents a significant consolidation and enhancement release, bringing together improvements from the `names-fix` branch with critical compatibility updates from master. This release focuses on robustness, consistency, and forward compatibility with ComfyUI 0.3.65+.

## Highlights

### 🔧 ComfyUI 0.3.65+ Compatibility

**Critical Fix:** Added `_OutputCacheCompat` wrapper to maintain compatibility with ComfyUI 0.3.65+ API changes. The new version of ComfyUI changed the `get_input_data` function to expect an execution_list object with a `get_output_cache()` method instead of a plain dictionary. This release provides seamless backward compatibility while supporting both old and new ComfyUI versions.

### 📁 Enhanced Filename Resolution

**Major Improvement:** Completely revamped filename resolution system to handle complex real-world scenarios:
- Fixed resolution of model files with version numbers containing dots (e.g., `dark_gothic_fantasy_xl_3.01.safetensors`)
- Handles multiple dots in filenames correctly (e.g., `model.v1.2.3.safetensors`)
- Properly sanitizes Windows-problematic trailing spaces and dots
- Supports Unicode characters, extended ASCII, and special punctuation in filenames

### 🏗️ Code Consolidation

**Architectural Improvement:** Unified duplicate resolution logic across model/VAE/LoRA/UNet hash functions:
- New `pathresolve.py` module with reusable helpers
- `try_resolve_artifact()` for generic name→path resolution
- `load_or_calc_hash()` for consistent hash calculation with sidecar support
- Centralized `EXTENSION_ORDER` constant eliminates hardcoded extension lists

### 📊 Enhanced Hash Logging

**Developer Feature:** Configurable hash logging with multiple modes:
- `none` - No hash logging (default)
- `filename` - Log filename only
- `path` - Log relative path
- `detailed` - Log full path with context
- `debug` - Maximum verbosity

Control via `METADATA_HASH_LOG_MODE` environment variable.

## Breaking Changes

**None** - This release maintains full backward compatibility while adding forward compatibility.

## New Features

### Unified Artifact Resolution System

The new `pathresolve.py` module provides:

```python
# Generic resolution for any artifact type
result = try_resolve_artifact("checkpoints", model_name)
if result.full_path:
    # Use result.display_name and result.full_path
    pass

# Centralized hash calculation with sidecar support
hash_value = load_or_calc_hash(filepath, truncate=10)
```

### Enhanced Filename Sanitization

```python
from saveimage_unimeta.utils.pathresolve import sanitize_candidate

# Handles trailing punctuation, quotes, and Windows-problematic characters
clean_name = sanitize_candidate("model.name.v1.2.3. ")
# Returns: "model.name.v1.2.3"
```

### PEP 562 Lazy Imports

The package now implements PEP 562 lazy attribute access, improving test compatibility and reducing import overhead.

## Bug Fixes

1. **Filename Resolution with Dots**: Fixed incorrect parsing of filenames with version numbers (e.g., `model.v1.2.3` was treated as having extension `.3`)

2. **Startup Message Duplication**: Implemented session-based deduplication using logging registry to prevent multiple startup messages

3. **Hash Logging Propagation**: Fixed environment variable control for hash log propagation

4. **Test Import Issues**: Added proper E402 noqa comments and improved test isolation

## Testing

### New Test Coverage

- **test_output_cache_compat.py**: Comprehensive tests for ComfyUI 0.3.65+ compatibility wrapper
- **test_special_character_filenames.py**: Tests for Unicode, punctuation, and complex filename handling
- **test_lora_dots_fix.py**: Specific tests for the version number dot issue
- **test_hash_logging.py**: Tests for hash logging modes and configuration
- **test_startup_message.py**: Tests for startup message deduplication
- **test_pathresolve_additions.py**: Tests for new unified resolution helpers

### Test Results

```
289 passed, 5 skipped in 0.91s
All checks passed!
```

## Migration Guide

### For Users

**No action required** - This release is a drop-in replacement for v1.2.x.

### For Developers

If you've been experiencing issues with:

1. **Model files with version numbers in names**: These should now work correctly without renaming
2. **ComfyUI 0.3.65+ compatibility**: Upgrade to this version for full support
3. **Hash calculation inconsistencies**: New centralized system provides more consistent results

### Environment Variables

New environment variables available:

- `METADATA_HASH_LOG_MODE`: Set hash logging verbosity (none/filename/path/detailed/debug)
- `METADATA_HASH_LOG_PROPAGATE`: Control whether hash logs propagate to root logger (0/1)
- `METADATA_FORCE_REHASH`: Force recomputation of hashes, bypassing sidecar cache (0/1)

## Known Issues

- None specific to this release. See GitHub issues for general project status.

## Contributors

This release consolidates work from multiple contributors and reviews:

- 36 commits in the names-fix branch
- 43 review comments addressed
- Compatibility fixes merged from master v1.2.1
- Comprehensive testing and linting passes

## Upgrade Path

### From v1.2.x

1. Update your installation:
   ```bash
   cd ComfyUI/custom_nodes/ComfyUI_SaveImageWithMetaDataUniversal
   git pull origin master
   git checkout v1.3.0
   ```

2. Restart ComfyUI

3. No configuration changes required

### From v1.1.x or earlier

Follow the upgrade path through v1.2.0 first, then upgrade to v1.3.0.

## Next Steps

Version 1.3.0 establishes a solid foundation for future enhancements:

- Further consolidation of helper functions
- Additional metadata capture capabilities
- Enhanced error reporting and diagnostics
- Performance optimizations

## Support

- **Documentation**: See README.md and docs/ directory
- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Use GitHub Discussions for questions

---

**Full Changelog**: See CHANGELOG.md for complete details of all changes.
