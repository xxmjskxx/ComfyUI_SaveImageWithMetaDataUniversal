# Release Notes - v1.3.0

**Release Date:** 2025-11-18  
**Commits:** 219 from v1.2.4  
**Files Changed:** 168 files  
**Changes:** +17,242 insertions, -2,657 deletions

## Overview

Version 1.3.0 is a major consolidation release representing months of development work across 219 commits. This release brings substantial improvements to LoRA/embedding handling, a redesigned user rule system, enhanced scanner capabilities, comprehensive testing infrastructure, and extensive documentation improvements. This is the largest update since v1.0.0.

## Highlights

### 🎯 LoRA & Embedding System Overhaul

**Major Enhancement:** Complete redesign of LoRA and embedding detection and metadata capture:

- **Opt-in inline parsing**: New `inline_lora_candidate` flag system prevents accidental prompt scanning. Only nodes that explicitly opt in will have their prompts parsed for `<lora:...>` tags, eliminating false positives and improving performance.

- **Enhanced LoRA manager**: Now intelligently inspects structured fields (`lora_stack`, `loras`, `loaded_loras`) before falling back to text parsing, properly capturing names, hashes, and per-slot strengths from all major LoRA loader types.

- **Fixed "Schedule LoRAs" bug**: PCLazyLoraLoader nodes now maintain separate model/CLIP strength lists with dedicated selectors, eliminating metadata duplication.

- **Cached embedding hashes**: Significant performance improvement by reusing computed embedding hashes across scanner and capture operations.

- **Per-node strength tracking**: Revamped strength alignment logic preserves accurate strength values per node instance.

### 🔧 User Rule System Redesign

**Architectural Improvement:** Intelligent rule merging with selective loading:

- **Coverage-aware merging**: New `required_classes` parameter enables selective rule loading. When provided, only explicitly requested or forced classes are merged, allowing test runs to ignore unrelated user definitions while still applying targeted overrides.

- **Version tracking**: Automatic detection of outdated rule files with clear warnings to re-run scanner after updates.

- **Legacy preservation**: Global loads (rule scanner, migrations) maintain full backward compatibility by loading all user entries.

### 📊 Scanner Intelligence

**Enhanced Capabilities:** Smarter node detection and rule generation:

- **Priority keywords**: Scanner now supports keyword-based prioritization for better rule generation ordering.

- **Improved heuristics**: Refined sampler selection and metadata field detection algorithms.

- **Better LoRA/embedding detection**: Fixed hash resolution bugs and improved detection accuracy across different node types.

### 🧪 Comprehensive Testing Infrastructure

**Quality Assurance:** Extensive test coverage and validation tools:

- **New test suites**: `test_lora_manager_selectors.py`, `test_pclazy_hashes.py`, inline LoRA opt-in tests, strength preservation tests, and clip duplication regression tests.

- **CLI validation tools**: Enhanced workflow validation with verbose mode, metadata dumps, comprehensive tracing, and field-level validation.

- **Integration testing**: Full end-to-end validation through `test_validate_metadata_integration.py`.

- **Python 3.13 support**: Added to CI matrix for future-proofing.

### 📚 Documentation Excellence

**Developer Experience:** Comprehensive documentation across the codebase:

- **Universal docstrings**: Every Python file now has detailed docstrings covering purpose, inputs, outputs, and environment dependencies.
- **Enhanced instructions**: Expanded `.github/copilot-instructions.md` and related guidance files.
- **Inline explanations**: Complex logic sections and exception handlers now include clear explanatory comments.
- **Generated rules clarity**: `saveimage_unimeta/defs/ext/generated_user_rules.py` now starts with a descriptive docstring
   reminding contributors that it is rebuilt by the Metadata Rule Scanner / Save Custom Metadata Rules nodes and that
   edits belong in the JSON sources instead.

## Breaking Changes

**None** - This release maintains full backward compatibility with v1.2.x while adding substantial new capabilities.

## Detailed Changes

### LoRA & Embedding Improvements

#### Inline LoRA Parsing (Opt-in System)
Previously, the system would scan all prompt nodes for inline `<lora:...>` tags, which could lead to false positives and performance issues. The new opt-in system:

- Added `inline_lora_candidate` flag to all shipped prompt captures (core + extensions)
- `Capture.get_inputs` now remembers which prompt nodes opt into inline parsing
- Scanner automatically tags new positive/negative prompt suggestions with the inline flag
- Added `inline_filter` gate and `should_attempt_inline` check to prevent false positives
- Differentiates between prompt-only workflows (scan entire graph) and mixed workflows (selective scanning)

**Impact:** More accurate LoRA detection, reduced false positives, better performance.

#### Enhanced LoRA Manager
The LoRA manager has been completely overhauled to handle modern LoRA loader patterns:

- Inspects structured fields first: `lora_stack`, `loras`, `loaded_loras`, etc.
- Falls back to plain text parsing only when structured data unavailable
- Caching now tracks originating field to avoid stale data
- Per-slot strength values correctly preserved across node instances
- Supports string-fed syntax from LoRA Loader/Text Loader nodes

**Fixed:** LoRA Loader/Text Loader stacks now properly surface names, hashes, and strengths.

#### PCLazyLoraLoader Improvements
Special handling for PCLazy nodes that use different strength values for model vs CLIP:

- Separate model/CLIP strength lists sourced from `parse_lora_syntax`
- Dedicated clip-strength selector exposed in CAPTURE rules
- Fixed "Schedule LoRAs" clip duplication where CLIP strengths appeared twice in metadata

**Tests Added:**
- `test_lora_manager_selectors.py`: Regression cases for stack sources, JSON strings, clip strength handling
- `test_pclazy_hashes.py`: Hash calculation accuracy for PCLazy nodes
- `test_capture_core.py`: Inline opt-in behavior, per-node strength preservation

### User Rule System Enhancements

#### Selective Rule Merging
The rule loading system now supports intelligent filtering:

```python
# Old: Always load all user rules
definitions = load_user_definitions()

# New: Load only requested/forced classes
definitions = load_user_definitions(required_classes={'KSampler', 'CheckpointLoader'})
```

**Benefits:**
- Test runs with coverage requirements only load relevant rules
- Unrequested brand-new user-only nodes are skipped
- Targeted overrides for existing nodes still apply
- Forced includes always honored
- Legacy global loads unchanged (scanner, migrations)

**Implementation:**
- `allowed_user_classes` parameter threads through `_merge_user_capture_entry` and `_merge_user_sampler_entry`
- When `required_classes` provided, user JSON entries merged only for explicitly requested or forced classes
- Ensures coverage-satisfied runs ignore unrelated user-only nodes

#### Version Tracking
New `version.py` module provides:

- `RULES_VERSION` constant stamped into generated modules
- `LOADED_RULES_VERSION` tracking in defs loader
- One-time warning when saved rules missing or outdated
- Prompts users to re-run scanner + saver after updates

**User Impact:** Clear guidance when rules need refreshing after node pack updates.

### Scanner Improvements

#### Priority Keywords
Scanner now accepts `priority_keywords` list to influence rule generation order:

- Keywords matched against node class names
- Matching nodes prioritized in suggestions
- Better control over rule organization
- Tests verify priority keyword handling

#### Enhanced Heuristics
Improved detection algorithms:

- Better sampler selection logic
- More accurate metadata field detection
- Fixed LoRA and embedding hash resolution bugs
- Improved handling of edge cases

#### Hash Caching
Scanner now uses cached embedding hashes:

- Significant performance improvement for large sets
- Consistent with capture hash caching approach
- Tests verify hash accuracy

### Testing & Quality Assurance

#### New Test Suites

**test_lora_manager_selectors.py**
- Tests structured field inspection
- JSON string handling
- Clip strength separation
- Stack source tracking

**test_pclazy_hashes.py**
- Hash calculation accuracy
- Strength list handling
- Selector correctness

**test_capture_core.py additions**
- `test_inline_prompt_text_not_recorded_without_opt_in`: Verifies opt-in enforcement
- `test_collect_lora_records_preserves_strengths_per_node`: Validates strength alignment

**test_loader_merge_behavior.py**
- Selective rule merging
- Coverage-aware behavior
- Forced include interaction

#### CLI Validation Tools

**run_efficiency_validation.py**
- `--launch-extra` now preserves env-driven flags like `COMFY_RUN_BACKGROUND=1`
- Honors `workflow_dir` parameter throughout validation pipeline
- Derives validation directory from first workflow's parent
- Logs reasons for `/object_info` polling failures
- Wired up module logger for better diagnostics

**validate_metadata.py**
- Verbose mode for detailed tracing
- Metadata dump capabilities
- Comprehensive field validation
- Validation check counters
- Workflow tracing with complete graph analysis

**run_dev_workflows.py**
- Removed stale commented defaults
- Parser matches actual behavior
- Better error messages

#### CI & Infrastructure
- Python 3.13 added to `unimeta-ci.yml` matrix
- Updated test isolation
- Better artifact handling
- Cleaned up obsolete test files

### Documentation Improvements

#### Comprehensive Docstrings
Every Python file now includes:

- Purpose and responsibility description
- Parameter documentation (types, meanings)
- Return value documentation
- Side effects and state changes
- Environment flag dependencies
- Example usage where helpful
- Cross-references to related modules

#### Enhanced Instructions
`.github/copilot-instructions.md` and related files:

- Updated architecture overview
- Expanded data flow documentation
- Better runtime contract explanations
- More examples of correct patterns
- Clearer guidance on common pitfalls

#### Inline Documentation
- Explained empty except clauses (BOM trimming, etc.)
- Documented complex heuristics
- Clarified function contracts
- Fixed incorrect docstrings (e.g., `coerce_first`)

### Code Quality Improvements

#### Exception Handling
- Replaced silent `pass` statements with structured logging
- Narrowed broad `Exception` catches to specific types
- Added diagnostic context to error logs
- `_append_loras_from_text` now logs parsing errors

#### Type Safety
- Mypy fixes throughout codebase
- Better type hints
- Removed type: ignore where possible
- Added missing type annotations

#### Code Organization
- Moved tools to `tests/tools` directory
- Better module separation
- Clearer function boundaries
- Removed obsolete code

#### Logging
- Structured module-level loggers
- Appropriate log levels (debug, info, warning)
- Contextual information in log messages
- Eliminated redundant logging

### Bug Fixes

#### Critical Fixes

**Repeating Startup Banner**
- Session-based deduplication using logging registry
- Banner only prints once per session
- Test: `test_startup_message.py`

**LoRA Hash Calculation**
- Fixed hash resolution bugs
- Corrected caching behavior
- Accurate hash display

**Metadata Value Bugs**
- Fixed `selectors.py` value generation
- Corrected `capture.py` processing
- Fixed `__init__.py` export handling

**Validation Script Bugs**
- Fixed critical validation failures
- Corrected workflow tracing logic
- Improved error reporting

#### Test Fixes

**test_validate_metadata_integration.py**
- Fixed errors preventing test execution
- Corrected mocking behavior
- Proper cleanup

**CI Issues**
- Fixed cookiecutter template problems
- Corrected Jinja boolean expressions
- Proper post-generation hooks

**Linting**
- Fixed various ruff violations
- Corrected formatting inconsistencies
- Removed invalid noqa comments

### Cleanup & Maintenance

#### Repository Cleanup
- Deleted all `__pycache__` directories
- Updated `.gitignore` to exclude build artifacts
- Removed test output files from tracking
- Cleaned up obsolete documentation

#### Removed Obsolete Code
- Stale commented-out defaults
- Unused imports
- Redundant helper functions
- Mjsk-specific test references

#### Better Organization
- Logical test file grouping
- Clear workflow examples
- Organized documentation structure

## Migration Guide

### For Users

**No action required** - This is a drop-in replacement for v1.2.x.

### Recommended Actions

1. **Update rule definitions** - Re-run the scanner and save custom metadata rules workflow to take advantage of new features:
   ```
   Use: example_workflows/refresh-rules.json
   Or: example_workflows/scan-and-save-custom-metadata-rules-simple.png
   ```

2. **Review LoRA metadata** - If you use LoRA loaders extensively, check that inline LoRA tags in prompts are being captured as expected. The new opt-in system is more selective.

3. **Test workflows** - Run a few test generations to verify metadata is captured correctly, especially if you use:
   - Multiple LoRA loaders
   - PCLazy/Schedule LoRAs nodes  
   - Custom prompt encoders
   - Inline LoRA tags in prompts

### For Developers

**New APIs Available:**

```python
# Selective rule loading
from saveimage_unimeta.defs import load_user_definitions
definitions = load_user_definitions(required_classes={'KSampler', 'MyCustomNode'})

# Version checking
from saveimage_unimeta import version
print(f"Rules version: {version.RULES_VERSION}")
```

**Testing Patterns:**

```python
# Test inline LoRA opt-in
def test_inline_lora_requires_opt_in():
    # Prompts without inline_lora_candidate flag should not be scanned
    assert not inline_loras_detected

# Test selective merging
def test_selective_rule_merge():
    definitions = load_user_definitions(required_classes={'KSampler'})
    assert 'KSampler' in definitions
    assert 'UnrequestedNode' not in definitions
```

## Environment Variables

No new environment variables in this release. Existing flags remain:

- `METADATA_TEST_MODE`: Enable test mode for deterministic output
- `METADATA_DEBUG_PROMPTS`: Log prompt aliasing and capture details
- `METADATA_NO_HASH_DETAIL`: Suppress detailed hash information
- `METADATA_NO_LORA_SUMMARY`: Suppress LoRA summary section
- `METADATA_FORCE_REHASH`: Force recomputation of all hashes
- `METADATA_HASH_LOG_MODE`: Control hash logging verbosity
- `METADATA_HASH_LOG_PROPAGATE`: Control hash log propagation
- `METADATA_DUMP_LORA_INDEX`: Dump LoRA index for debugging
- `METADATA_ENABLE_TEST_NODES`: Enable test node stubs

## Testing Results

### Test Statistics
```
289 tests passed
5 tests skipped  
0 tests failed
Coverage: Maintained from previous release
```

### CI Matrix
- Python 3.10, 3.11, 3.12, 3.13
- Ubuntu Latest
- All tests passing
- Linting: ruff (strict mode)
- Security: CodeQL (0 alerts)

### Manual Validation
- Tested with SD1.5, SDXL, FLUX workflows
- Validated LoRA stack handling
- Confirmed inline LoRA opt-in behavior
- Verified PCLazy clip strength separation
- Tested rule scanner with 50+ node types

## Known Issues

- None specific to this release
- See GitHub Issues for general project status

## Performance Impact

- **Improved:** Cached embedding hashes reduce redundant calculations
- **Improved:** Opt-in inline LoRA scanning reduces unnecessary prompt parsing
- **Improved:** Selective rule merging speeds up coverage-aware test runs
- **Negligible:** Additional validation and logging overhead is minimal
- **Overall:** Performance improvements across the board

## Upgrade Path

### From v1.2.x

1. **Update installation:**
   ```bash
   cd ComfyUI/custom_nodes/ComfyUI_SaveImageWithMetaDataUniversal
   git pull origin master
   git checkout v1.3.0
   ```

2. **Restart ComfyUI**

3. **Refresh rule definitions** (recommended):
   - Load `example_workflows/refresh-rules.json`
   - Execute workflow
   - Rules updated automatically

4. **Test workflow** - Generate a few test images to verify metadata

### From v1.1.x or earlier

1. First upgrade to v1.2.0
2. Then follow steps above for v1.2.x → v1.3.0

## Contributors & Acknowledgments

This release consolidates work from:
- 219 commits across multiple development branches
- Extensive code review and refinement
- Community feedback and bug reports
- AI-assisted development and documentation

Special thanks to all who reported issues, suggested improvements, and tested pre-release versions.

## Next Steps

Version 1.3.0 establishes a solid foundation for future development:

### Planned for v1.4.x
- Additional metadata capture capabilities
- Enhanced error reporting and diagnostics
- Performance profiling and optimization
- More comprehensive workflow examples

### Under Consideration
- Advanced LoRA merging scenarios
- Custom metadata validation rules
- Batch processing optimizations
- Additional file format support

## Support & Resources

- **Documentation**: README.md, docs/ directory
- **Issues**: [GitHub Issues](https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/issues)
- **Discussions**: [GitHub Discussions](https://github.com/xxmjskxx/ComfyUI_SaveImageWithMetaDataUniversal/discussions)
- **Examples**: example_workflows/ directory
- **Testing Guide**: docs/ and tests/ directories

---

**Full Changelog**: See [CHANGELOG.md](../../CHANGELOG.md) for complete details of all changes.
