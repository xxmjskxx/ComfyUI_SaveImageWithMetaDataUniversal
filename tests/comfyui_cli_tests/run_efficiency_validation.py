#!/usr/bin/env python3
"""Automate efficiency workflow validation via comfy-cli.

This script orchestrates the full regression loop for the efficiency workflows:

1. Start a ComfyUI server through ``comfy launch`` (foreground) while teeing
   stdout/stderr into ``hash_logs.txt`` so the Save node's ``model_hash_log``
   entries are preserved.
2. Queue the metadata-rule refresh workflow followed by the
   ``efficiency-nodes-debug-hash.json`` workflow with ``comfy run`` to ensure the
   latest capture rules and debug hash logging are in effect.
3. Once the workflows finish, execute the validator, metadata dump, and hash
   comparison utilities so every run produces a consistent triad of artifacts.

The defaults target the portable ComfyUI bundle shipped alongside this repo,
 but everything is configurable through CLI flags.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from contextlib import nullcontext
from pathlib import Path
from collections.abc import Iterable
from typing import TextIO

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_WORKFLOW_DIR = SCRIPT_DIR / "dev_test_workflows"
DEFAULT_SCAN_WORKFLOW = DEFAULT_WORKFLOW_DIR / "1-scan-and-save-custom-metadata-rules.json"
DEFAULT_EFFICIENCY_WORKFLOW = DEFAULT_WORKFLOW_DIR / "efficiency-nodes-debug-hash.json"
DEFAULT_LOG_DIR = SCRIPT_DIR / "Test"
DEFAULT_COMFY_CLI = Path(os.environ.get("COMFY_CLI", "comfy"))
DEFAULT_WORKSPACE = Path(
    os.environ.get(
        "COMFY_WORKSPACE",
        r"C:\StableDiffusion\StabilityMatrix-win-x64\Data\Packages\ComfyUI_windows_portable\ComfyUI",
    )
)
DEFAULT_COMFY_EXTRA = ["--background"] if os.environ.get("COMFY_RUN_BACKGROUND") == "1" else []
DEFAULT_SERVER_EXTRA = ["--windows-standalone-build", "--listen", "127.0.0.1", "--port", "8188"]
DEFAULT_ENV = {
    "METADATA_HASH_LOG_MODE": "debug",
    "METADATA_HASH_LOG_PROPAGATE": "0",
    "METADATA_TEST_MODE": "1",
    "METADATA_ENABLE_TEST_NODES": "1",
}
DEFAULT_REQUIRED_NODES = ["MetadataRuleScanner"]

logger = logging.getLogger(__name__)


def parse_kv_pairs(pairs: Iterable[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in pairs:
        if "=" not in item:
            raise argparse.ArgumentTypeError(f"Environment override '{item}' is missing '='")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise argparse.ArgumentTypeError(f"Environment override '{item}' has an empty key")
        result[key] = value
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comfy-cli", type=Path, default=DEFAULT_COMFY_CLI, help="Path to comfy executable")
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE, help="ComfyUI workspace directory")
    parser.add_argument(
        "--scan-workflow",
        type=Path,
        default=DEFAULT_SCAN_WORKFLOW,
        help="Workflow JSON used to refresh metadata capture rules",
    )
    parser.add_argument(
        "--workflows",
        type=Path,
        nargs="+",
        default=[DEFAULT_EFFICIENCY_WORKFLOW],
        help="One or more workflow JSON files to queue after the scan workflow",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=DEFAULT_LOG_DIR,
        help="Directory for hash/validation/metadata logs",
    )
    parser.add_argument(
        "--output-folder",
        type=Path,
        help="ComfyUI output/Test directory; defaults to <workspace>/output/Test",
    )
    parser.add_argument(
        "--workflow-timeout",
        type=int,
        default=600,
        help="Seconds to wait for each workflow before aborting",
    )
    parser.add_argument(
        "--workflow-retries",
        type=int,
        default=1,
        help="Number of automatic retries per workflow when comfy-cli returns a failure",
    )
    parser.add_argument(
        "--workflow-retry-delay",
        type=int,
        default=30,
        help="Seconds to wait between workflow retry attempts",
    )
    parser.add_argument(
        "--server-start-timeout",
        type=int,
        default=180,
        help="Seconds to wait for the ComfyUI server to report healthy",
    )
    parser.add_argument(
        "--launch-extra",
        action="append",
        default=None,
        help=(
            "Extra flags passed to 'comfy launch' before the '--' separator "
            "(COMFY_RUN_BACKGROUND=1 automatically adds --background)."
        ),
    )
    parser.add_argument(
        "--server-extra",
        action="append",
        default=DEFAULT_SERVER_EXTRA.copy(),
        help="Arguments appended after the '--' when launching the ComfyUI server",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Environment overrides propagated to comfy-cli and helper scripts",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validate_metadata/read_exif/compare_hash_logs steps",
    )
    parser.add_argument(
        "--echo-server",
        action="store_true",
        help="Mirror ComfyUI stdout/stderr to the console while still capturing logs",
    )
    parser.add_argument(
        "--reuse-server",
        action="store_true",
        help="Reuse an already running ComfyUI instance instead of launching a new one (hash log capture is disabled)",
    )
    parser.add_argument(
        "--required-node",
        dest="required_nodes",
        action="append",
        default=None,
        help=(
            "Node class name that must be registered before workflows run. "
            "Repeat the flag for multiple nodes; default waits for MetadataRuleScanner."
        ),
    )
    parser.add_argument(
        "--node-ready-timeout",
        type=int,
        default=120,
        help="Seconds to wait for required nodes to appear in /object_info",
    )
    parser.add_argument(
        "--node-ready-mode",
        choices=["object-info", "health-only", "skip"],
        default="object-info",
        help=(
            "Strategy for verifying node readiness: 'object-info' polls /object_info, "
            "'health-only' waits for /system_stats only, and 'skip' trusts that nodes are available."
        ),
    )
    parser.add_argument(
        "--node-ready-request-timeout",
        type=int,
        default=15,
        help="Seconds to wait for each /object_info response before retrying (object-info mode only)",
    )
    parser.add_argument(
        "--node-ready-delay",
        type=int,
        default=0,
        help=(
            "Additional seconds to wait after the readiness check passes. Use this when heavy "
            "custom nodes keep registering even though the server health endpoint is up."
        ),
    )
    parser.add_argument(
        "--skip-auto-stop",
        action="store_true",
        help="Do not issue comfy stop before launching a new server",
    )
    parser.add_argument(
        "--auto-stop-timeout",
        type=int,
        default=60,
        help="Seconds to wait for an existing server to shut down after comfy stop",
    )
    return parser


class ServerController:
    """Manage a comfy-cli launch process and stream logs to disk."""

    def __init__(
        self,
        command: list[str],
        log_file: Path,
        env: dict[str, str],
        start_timeout: int,
        echo: bool,
        health_url: str,
    ) -> None:
        self._command = command
        self._log_file_path = log_file
        self._env = env
        self._start_timeout = start_timeout
        self._echo = echo
        self._health_url = health_url
        self._proc: subprocess.Popen[bytes] | None = None
        self._threads: list[threading.Thread] = []
        self._log_handle: TextIO | None = None

    def __enter__(self) -> ServerController:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    def start(self) -> None:
        if self._proc is not None:
            raise RuntimeError("Server already started")
        log_file = self._log_file_path
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handle = log_file.open("w", encoding="utf-8", errors="replace")
        self._log_handle = handle
        try:
            self._proc = subprocess.Popen(
                self._command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=REPO_ROOT,
                env=self._env,
            )
        except FileNotFoundError as exc:  # pragma: no cover - depends on local CLI path
            handle.close()
            raise RuntimeError(f"Unable to launch comfy-cli binary '{self._command[0]}': {exc}") from exc
        assert self._proc.stdout and self._proc.stderr
        self._threads = [
            threading.Thread(
                target=self._pump_stream,
                args=(self._proc.stdout, "STDOUT"),
                daemon=True,
            ),
            threading.Thread(
                target=self._pump_stream,
                args=(self._proc.stderr, "STDERR"),
                daemon=True,
            ),
        ]
        for thread in self._threads:
            thread.start()
        if not wait_for_server(self._health_url, self._start_timeout):
            exit_code = self._proc.poll()
            self.stop()
            log_hint = f" See {self._log_file_path} for details."
            if exit_code is not None:
                raise RuntimeError(
                    f"ComfyUI server failed to start (exit code {exit_code})." + log_hint,
                )
            raise RuntimeError(
                f"ComfyUI server did not become healthy within {self._start_timeout} seconds." + log_hint,
            )

    def stop(self) -> None:
        if not self._proc:
            return
        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
        for thread in self._threads:
            thread.join(timeout=1)
        if self._log_handle:
            self._log_handle.close()
        self._proc = None

    def _pump_stream(self, stream, label: str) -> None:
        assert self._log_handle is not None
        while True:
            chunk = stream.readline()
            if not chunk:
                break
            text = chunk.decode("utf-8", errors="replace")
            self._log_handle.write(f"[{label}] {text}")
            self._log_handle.flush()
            if self._echo:
                sys.stdout.write(f"[server/{label.lower()}] {text}")
                sys.stdout.flush()


def wait_for_server(url: str, timeout: int) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            time.sleep(1)
    return False


def wait_for_server_shutdown(url: str, timeout: int) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                time.sleep(1)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            return True
    return False


def wait_for_nodes(
    url: str,
    required_nodes: list[str],
    timeout: int,
    request_timeout: int,
) -> set[str]:
    """Poll /object_info until the required node classes are registered."""
    deadline = time.time() + timeout
    missing = set(required_nodes)
    while missing and time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=request_timeout) as response:
                payload = json.load(response)
            available = set(payload.get("nodes", {}).keys())
            missing -= available
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as err:
            logger.debug("Failed to poll object_info for required nodes: %s", err)
        time.sleep(1)
    return missing


def run_command(cmd: list[str], env: dict[str, str], timeout: int | None = None) -> None:
    completed = subprocess.run(cmd, cwd=REPO_ROOT, env=env, timeout=timeout)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(cmd)}")


def run_workflow(cli: Path, workspace: Path, workflow: Path, env: dict[str, str], timeout: int) -> None:
    cmd = [
        str(cli),
        f"--workspace={workspace}",
        "run",
        "--workflow",
        str(workflow),
        "--wait",
        "--timeout",
        str(timeout),
        "--verbose",
    ]
    run_command(cmd, env)


def run_workflow_with_retry(
    cli: Path,
    workspace: Path,
    workflow: Path,
    env: dict[str, str],
    timeout: int,
    retries: int,
    retry_delay: int,
) -> None:
    attempts = max(1, retries + 1)
    workflow_name = workflow.name
    for attempt in range(1, attempts + 1):
        try:
            run_workflow(cli, workspace, workflow, env, timeout)
            return
        except RuntimeError as exc:
            if attempt == attempts:
                raise
            print(
                f"Workflow '{workflow_name}' failed (attempt {attempt}/{attempts}) with: {exc}. "
                f"Retrying in {retry_delay} second(s)..."
            )
            time.sleep(retry_delay)


def run_validation_steps(
    output_folder: Path,
    log_dir: Path,
    env: dict[str, str],
    workflow_dir: Path,
) -> None:
    validation_log = log_dir / "validation_log.txt"
    metadata_dump = log_dir / "metadata_dump.txt"
    hash_compare = log_dir / "hash_compare.txt"

    validate_script = SCRIPT_DIR / "validate_metadata.py"
    dump_script = SCRIPT_DIR / "read_exif_all_folder_write_to_txt.py"
    compare_script = REPO_ROOT / "tools" / "compare_hash_logs.py"

    run_command(
        [
            sys.executable,
            str(validate_script),
            "--output-folder",
            str(output_folder),
            "--workflow-dir",
            str(workflow_dir),
            "--log-file",
            str(validation_log),
        ],
        env,
    )
    run_command(
        [
            sys.executable,
            str(dump_script),
            "--img-folder",
            str(output_folder),
            "--output",
            str(metadata_dump),
        ],
        env,
    )
    run_command(
        [
            sys.executable,
            str(compare_script),
            "--metadata",
            str(metadata_dump),
            "--hashlogs",
            str(log_dir / "hash_logs.txt"),
            "--output",
            str(hash_compare),
        ],
        env,
    )


def stop_existing_server(cli: Path, workspace: Path, env: dict[str, str], health_url: str, timeout: int) -> None:
    cmd = [
        str(cli),
        f"--workspace={workspace}",
        "stop",
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, env=env)
    if completed.returncode not in (0, 1):
        raise RuntimeError(f"Failed to stop existing ComfyUI server (exit code {completed.returncode}).")
    if not wait_for_server_shutdown(health_url, timeout):
        raise RuntimeError(
            "Timed out waiting for the previous ComfyUI server to stop. "
            "Stop it manually or rerun with --skip-auto-stop / --reuse-server.",
        )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    output_folder = args.output_folder or args.workspace / "output" / "Test"
    log_dir = args.log_dir.resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    hash_log = log_dir / "hash_logs.txt"

    server_extra: list[str] = []
    for chunk in args.server_extra or []:
        server_extra.extend(chunk.split()) if isinstance(chunk, str) else server_extra.extend(chunk)
    if not server_extra:
        server_extra = DEFAULT_SERVER_EXTRA.copy()

    launch_extra: list[str] = DEFAULT_COMFY_EXTRA.copy()
    for chunk in args.launch_extra or []:
        launch_extra.extend(chunk.split()) if isinstance(chunk, str) else launch_extra.extend(chunk)

    comfy_cmd = [str(args.comfy_cli), f"--workspace={args.workspace}", "launch"]
    comfy_cmd.extend(launch_extra)
    comfy_cmd.append("--")
    comfy_cmd.extend(server_extra)

    env = os.environ.copy()
    env.update(DEFAULT_ENV)
    env.update(parse_kv_pairs(args.env))

    server_base_url = "http://127.0.0.1:8188"
    health_url = f"{server_base_url}/system_stats"
    object_info_url = f"{server_base_url}/object_info"
    initial_health = wait_for_server(health_url, timeout=1)

    auto_stop_enabled = not args.reuse_server and not args.skip_auto_stop
    if auto_stop_enabled and initial_health:
        print("Stopping existing ComfyUI server before launching a new one...")
        stop_existing_server(args.comfy_cli, args.workspace, env, health_url, args.auto_stop_timeout)

    quick_health = wait_for_server(health_url, timeout=1)

    workflows = [args.scan_workflow] + list(args.workflows)
    workflow_dir_for_validation = DEFAULT_WORKFLOW_DIR
    if args.workflows:
        try:
            workflow_dir_for_validation = args.workflows[0].resolve().parent
        except Exception:
            workflow_dir_for_validation = DEFAULT_WORKFLOW_DIR

    if quick_health and not args.reuse_server:
        raise RuntimeError(
            "Detected an existing ComfyUI server on http://127.0.0.1:8188. "
            "Stop it before running this script or rerun with --reuse-server (hash logs will be stale).",
        )

    reused_server = args.reuse_server
    if reused_server and not quick_health:
        if not wait_for_server(health_url, args.server_start_timeout):
            raise RuntimeError(
                "--reuse-server was specified but no healthy ComfyUI instance became available "
                f"within {args.server_start_timeout} seconds.",
            )

    server_context = (
        nullcontext()
        if reused_server
        else ServerController(comfy_cmd, hash_log, env, args.server_start_timeout, args.echo_server, health_url)
    )

    with server_context:
        if reused_server:
            print("Reusing existing ComfyUI server; hash_logs.txt will not capture new output in this mode.")
        required_nodes = args.required_nodes or DEFAULT_REQUIRED_NODES.copy()
        node_ready_mode = args.node_ready_mode
        if node_ready_mode == "object-info":
            missing_nodes = wait_for_nodes(
                object_info_url,
                required_nodes,
                args.node_ready_timeout,
                args.node_ready_request_timeout,
            )
            if missing_nodes:
                missing = ", ".join(sorted(missing_nodes))
                raise RuntimeError(
                    "Required node(s) did not register within the allotted time: "
                    f"{missing}. If your environment has heavy custom nodes, rerun with "
                    "--node-ready-mode=health-only or --node-ready-mode=skip.",
                )
        elif node_ready_mode == "health-only":
            if not wait_for_server(health_url, args.node_ready_timeout):
                raise RuntimeError(
                    "The ComfyUI health endpoint stopped responding while waiting for nodes. "
                    "Check the server logs or rerun with --node-ready-mode=object-info.",
                )
        else:
            print("Skipping node readiness checks per --node-ready-mode=skip.")
        if args.node_ready_delay > 0:
            print(
                f"Waiting an extra {args.node_ready_delay} second(s) for heavy custom nodes to finish registering..."
            )
            time.sleep(args.node_ready_delay)
        for wf in workflows:
            run_workflow_with_retry(
                args.comfy_cli,
                args.workspace,
                wf,
                env,
                args.workflow_timeout,
                args.workflow_retries,
                args.workflow_retry_delay,
            )

    if not args.skip_validation:
        run_validation_steps(output_folder, log_dir, env, workflow_dir_for_validation)

    print("=" * 70)
    print("Artifacts written to:")
    if reused_server:
        print(f"  Hash log:        {hash_log} (unchanged; reuse-server mode)")
    else:
        print(f"  Hash log:        {hash_log}")
    if not args.skip_validation:
        print(f"  Validation log:  {log_dir / 'validation_log.txt'}")
        print(f"  Metadata dump:   {log_dir / 'metadata_dump.txt'}")
        print(f"  Hash comparison: {log_dir / 'hash_compare.txt'}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted by user")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
