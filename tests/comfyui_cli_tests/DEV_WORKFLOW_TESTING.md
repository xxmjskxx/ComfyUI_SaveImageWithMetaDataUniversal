# Development Workflow Testing Guide

This guide explains how to use the `run_dev_workflows.py` script to test workflows locally without committing them to the repository.

## Overview

The `run_dev_workflows.py` script allows you to:
- Execute multiple ComfyUI workflows from the command line
- Test workflows with local model paths that shouldn't be committed
- Automate workflow testing without using the web UI

## Setup

### 1. Use the Test Script

The script `run_dev_workflows.py` is included in the repository root. Simply use it directly from the repository.

### 2. Create the Workflow Directory

Create a `dev_test_workflows` folder in the root of this custom node pack:

```
ComfyUI_SaveImageWithMetaDataUniversal/
├── dev_test_workflows/        # Your local test workflows (not committed)
│   ├── test_workflow_1.json
│   ├── test_workflow_2.json
│   └── ...
├── run_dev_workflows.py        # Test runner script (not committed)
├── example_workflows/          # Example workflows (committed)
└── ...
```

### 3. Prepare Workflow Files

Workflows must be in **API JSON format**, not the standard UI format.

To convert workflows to API format:
1. Open ComfyUI web UI
2. Go to Settings → Enable "Dev Mode"
3. Load your workflow
4. Click "Save (API format)" button
5. Save to `dev_test_workflows/` folder

You can use workflows from `example_workflows/` as templates, but update the model paths to match your local environment.

## Usage

### Basic Usage (Windows)

Single line command:

```bash
python tests/comfyui_cli_tests/run_dev_workflows.py --comfyui-path "C:\StableDiffusion\StabilityMatrix-win-x64\Data\Packages\ComfyUI_windows_portable" --python-exe "C:\StableDiffusion\StabilityMatrix-win-x64\Data\Packages\ComfyUI_windows_portable\python_embeded\python.exe" --temp-dir "F:\StableDiffusion\ComfyUI" --output-folder "C:\StableDiffusion\StabilityMatrix-win-x64\Data\Packages\ComfyUI\output\Test" --extra-args="--windows-standalone-build"
```

Using the command format from your environment:

```bash
python tests/comfyui_cli_tests/run_dev_workflows.py ^
  --comfyui-path "C:\StableDiffusion\StabilityMatrix-win-x64\Data\Packages\ComfyUI_windows_portable" ^
  --python-exe "C:\StableDiffusion\StabilityMatrix-win-x64\Data\Packages\ComfyUI_windows_portable\python_embeded\python.exe" ^
  --temp-dir "F:\StableDiffusion\ComfyUI" ^
  --extra-args="--windows-standalone-build"
```

### Basic Usage (Linux/Mac)

```bash
python tests/comfyui_cli_tests/run_dev_workflows.py --comfyui-path "/path/to/ComfyUI"
```

### Use Existing Running Server

If ComfyUI is already running:

```bash
python tests/comfyui_cli_tests/run_dev_workflows.py --comfyui-path "." --no-start-server
```

### Keep Server Running After Tests

By default, the script stops the server after execution. To keep it running:

```bash
python tests/comfyui_cli_tests/run_dev_workflows.py --comfyui-path "/path/to/ComfyUI" --keep-server
```

### Fast Metadata Stub Mode

If you only need to exercise metadata saving (and not full image generation), enable the lightweight
stub nodes and use the bundled `metadata-stub-basic.json` workflow. This avoids loading large
checkpoints by producing synthetic black images while still yielding full metadata output.

```bash
python tests/comfyui_cli_tests/run_dev_workflows.py --comfyui-path "/path/to/ComfyUI" \
  --enable-test-stubs --workflow-dir "tests/comfyui_cli_tests/dev_test_workflows"
```

The flag sets `METADATA_ENABLE_TEST_NODES=1` before ComfyUI starts so the optional
`MetadataTestSampler` node becomes available. Any workflow built around this node finishes quickly
and records the metadata fields supplied through its parameters.

## Command-Line Options

### run_dev_workflows.py Options

| Option | Description | Default |
|--------|-------------|---------|
| `--comfyui-path` | Path to ComfyUI installation (containing main.py) | *Required* |
| `--python-exe` | Path to Python executable | Current Python |
| `--workflow-dir` | Directory containing workflow JSON files | `dev_test_workflows` |
| `--host` | ComfyUI server host | `127.0.0.1` |
| `--port` | ComfyUI server port | `8188` |
| `--temp-dir` | Temporary directory for ComfyUI | None |
| `--extra-args` | Extra arguments to pass to ComfyUI | None |
| `--wait-between` | Seconds to wait between workflow executions | `2.0` |
| `--no-start-server` | Don't start server, assume it's already running | `False` |
| `--keep-server` | Don't stop server after execution | `False` |
| `--output-folder` | Path to output Test folder to clean before running | None |
| `--no-clean` | Skip cleaning the output folder | `False` |

### validate_metadata.py Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output-folder` | Path to ComfyUI output Test folder with generated images | *Required* |
| `--workflow-dir` | Directory containing workflow JSON files | `dev_test_workflows` |

## Example Workflows

The `dev_test_workflows/` folder contains test workflows.

## Troubleshooting

### "Server did not start"
- Check that `--comfyui-path` points to the correct directory containing `main.py`
- Verify the Python executable path is correct
- Check if port 8188 is already in use
- Try increasing wait time or starting server manually first

### "Invalid JSON" errors
- Ensure workflows are in API format (not UI format)
- Use "Save (API format)" in ComfyUI Dev Mode
- Validate JSON syntax in a JSON validator

### Workflows not found
- Verify `dev_test_workflows/` folder exists
- Check that workflow files have `.json` extension
- Use `--workflow-dir` to specify a different directory

### Model path errors
- Update model paths in workflows to match your local environment
- Check that models exist at the specified paths
- Verify model file permissions

## Notes

- The `dev_test_workflows/` folder is excluded from git via `.gitignore`
- This allows you to keep local test workflows with machine-specific paths
- The script only queues workflows; it doesn't wait for completion or check results
- For detailed workflow execution, monitor the ComfyUI server console output
- Workflows are executed sequentially with a 2-second delay between them (configurable)

## Cleaning Test Output

The script can automatically clean the output Test folder before running workflows to ensure a clean testing environment.

### Automatic Cleanup

Use the `--output-folder` option to specify the Test folder to clean:

**Windows:**
```bash
python tests/comfyui_cli_tests/run_dev_workflows.py ^
  --comfyui-path "C:\StableDiffusion\ComfyUI" ^
  --output-folder "C:\StableDiffusion\StabilityMatrix-win-x64\Data\Packages\ComfyUI\output\Test"
```

**Linux/Mac:**
```bash
python tests/comfyui_cli_tests/run_dev_workflows.py \
  --comfyui-path "/path/to/ComfyUI" \
  --output-folder "/path/to/ComfyUI/output/Test"
```

### Skip Cleanup

If you want to keep existing files, use `--no-clean`:

```bash
python tests/comfyui_cli_tests/run_dev_workflows.py --comfyui-path "." --output-folder "./output/Test" --no-clean
```

**Note:** The cleanup feature requires the `send2trash` package. Install it with:

```bash
pip install send2trash
```

Files are moved to the recycle bin/trash instead of being permanently deleted, so you can recover them if needed.

## Validating Metadata

After running workflows, you can validate that the generated images contain the expected metadata using the `validate_metadata.py` script.

### Basic Usage

**Windows:**
```bash
"C:\StableDiffusion\StabilityMatrix-win-x64\Data\Packages\ComfyUI_windows_portable\python_embeded\python.exe" validate_metadata.py ^
  --output-folder "C:\StableDiffusion\StabilityMatrix-win-x64\Data\Packages\ComfyUI\output\Test"
```

**Linux/Mac:**
```bash
python tests/comfyui_cli_tests/validate_metadata.py \
  --output-folder "/path/to/ComfyUI/output/Test"
```

### What Gets Validated

The validation script:
- Reads metadata from PNG, JPEG, and WebP images
- Parses the workflow JSON files to extract expected metadata values
- Compares actual metadata against expected values
- Reports validation results with pass/fail status

### Validation Checks

For each image, the script checks:
- **Required Fields:** Steps, Sampler, CFG scale, Seed (based on workflow configuration)
- **File Format:** Matches the workflow's specified output format
- **Metadata Fallback:** Detects and reports if JPEG metadata fallback occurred

### Complete Testing Workflow

A typical testing workflow looks like this:

**Windows:**
```batch
@echo off
REM Step 1: Clean output folder and run workflows
python tests/comfyui_cli_tests/run_dev_workflows.py ^
  --comfyui-path "C:\StableDiffusion\ComfyUI" ^
  --python-exe "C:\StableDiffusion\python_embeded\python.exe" ^
  --temp-dir "F:\StableDiffusion\ComfyUI" ^
  --extra-args "--windows-standalone-build" ^
  --output-folder "C:\StableDiffusion\StabilityMatrix-win-x64\Data\Packages\ComfyUI\output\Test"

REM Step 2: Wait for workflows to complete (adjust timing as needed)
timeout /t 120

REM Step 3: Validate the generated images
python tests/comfyui_cli_tests/validate_metadata.py ^
  --output-folder "C:\StableDiffusion\StabilityMatrix-win-x64\Data\Packages\ComfyUI\output\Test"
```

**Linux/Mac:**
```bash
#!/bin/bash

# Step 1: Clean output folder and run workflows
python tests/comfyui_cli_tests/run_dev_workflows.py \
  --comfyui-path "/path/to/ComfyUI" \
  --output-folder "/path/to/ComfyUI/output/Test"

# Step 2: Wait for workflows to complete (adjust timing as needed)
sleep 120

# Step 3: Validate the generated images
python tests/comfyui_cli_tests/validate_metadata.py \
  --output-folder "/path/to/ComfyUI/output/Test"
```

## Advanced Usage

### Custom Workflow Directory

```bash
python tests/comfyui_cli_tests/run_dev_workflows.py --comfyui-path "." --workflow-dir "my_custom_tests"
python tests/comfyui_cli_tests/validate_metadata.py --output-folder "./output/Test" --workflow-dir "my_custom_tests"
```

### Multiple Environments

Create different workflow folders for different test scenarios:

```
dev_test_workflows/
├── flux_tests/
├── sd15_tests/
└── sdxl_tests/
```

Then run:

```bash
python tests/comfyui_cli_tests/run_dev_workflows.py --comfyui-path "." --workflow-dir "tests/comfyui_cli_tests/dev_test_workflows/flux_tests"
python tests/comfyui_cli_tests/validate_metadata.py --output-folder "./output/Test" --workflow-dir "tests/comfyui_cli_tests/dev_test_workflows/flux_tests"
```

### Batch Testing

Create a batch file (Windows) or shell script (Linux/Mac) to run multiple test suites:

**test_all.bat (Windows):**
```batch
@echo off
python tests/comfyui_cli_tests/run_dev_workflows.py --comfyui-path "%COMFYUI_PATH%" --workflow-dir "tests/comfyui_cli_tests/dev_test_workflows/flux_tests" --output-folder "%OUTPUT_PATH%"
timeout /t 120
python tests/comfyui_cli_tests/validate_metadata.py --output-folder "%OUTPUT_PATH%" --workflow-dir "tests/comfyui_cli_tests/dev_test_workflows/flux_tests"

python tests/comfyui_cli_tests/run_dev_workflows.py --comfyui-path "%COMFYUI_PATH%" --workflow-dir "tests/comfyui_cli_tests/dev_test_workflows/sd15_tests" --no-start-server --output-folder "%OUTPUT_PATH%"
timeout /t 120
python tests/comfyui_cli_tests/validate_metadata.py --output-folder "%OUTPUT_PATH%" --workflow-dir "tests/comfyui_cli_tests/dev_test_workflows/sd15_tests"
```

**test_all.sh (Linux/Mac):**
```bash
#!/bin/bash
python tests/comfyui_cli_tests/run_dev_workflows.py --comfyui-path "$COMFYUI_PATH" --workflow-dir "tests/comfyui_cli_tests/dev_test_workflows/flux_tests" --output-folder "$OUTPUT_PATH"
sleep 120
python tests/comfyui_cli_tests/validate_metadata.py --output-folder "$OUTPUT_PATH" --workflow-dir "tests/comfyui_cli_tests/dev_test_workflows/flux_tests"

python tests/comfyui_cli_tests/run_dev_workflows.py --comfyui-path "$COMFYUI_PATH" --workflow-dir "tests/comfyui_cli_tests/dev_test_workflows/sd15_tests" --no-start-server --output-folder "$OUTPUT_PATH"
sleep 120
python tests/comfyui_cli_tests/validate_metadata.py --output-folder "$OUTPUT_PATH" --workflow-dir "tests/comfyui_cli_tests/dev_test_workflows/sd15_tests"
```
