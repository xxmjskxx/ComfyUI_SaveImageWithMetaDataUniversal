#!/usr/bin/env python3
"""Compare LoRA hash entries between metadata dumps and hash logs."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_MODEL_EXTENSIONS = (
    ".safetensors",
    ".ckpt",
    ".pt",
    ".bin",
)
_FILENAME_PATTERN = re.compile(r".+\.(png|jpe?g|webp)$", re.IGNORECASE)
_HASH_LINE = re.compile(r"hash source=.*truncated=([0-9a-fA-F]{10})")
_RESOLVED_LINE = re.compile(r"resolved \((?P<kind>[a-z_]+)\)\s+(?P<token>.+?)\s+->", re.IGNORECASE)
_UNRESOLVED_LINE = re.compile(r"unresolved lora '([^']+)'", re.IGNORECASE)
_SKIPPED_LINE = re.compile(r"hash skipped reason=[^=]+token=([^\s]+)", re.IGNORECASE)
_LORA_NAME_PATTERN = re.compile(r"Lora_(\d+)\s+Model name:\s*([^,]+)")
_LORA_HASH_PATTERN = re.compile(r"Lora_(\d+)\s+Model hash:\s*([^,]+)")
_HASHES_PATTERN = re.compile(r"Hashes:\s*(\{.*?\})", re.DOTALL)
TOOLS_TEST_DIR = Path("tests/tools/Test")
CLI_COMPAT_TEST_DIR = Path("tests/comfyui_cli_tests/Test")


def _default_test_file(filename: str) -> Path:
    """Pick the preferred path for comparison artifacts."""

    for base in (TOOLS_TEST_DIR, CLI_COMPAT_TEST_DIR):
        candidate = base / filename
        if candidate.exists():
            return candidate
    return TOOLS_TEST_DIR / filename


@dataclass
class LoraRecord:
    """Container for LoRA metadata."""

    display_name: str
    hash_value: str | None


@dataclass
class SummaryRecord:
    """Container for LoRA entries inside the Hashes JSON block."""

    display_name: str
    hash_value: str


@dataclass
class HashLogRecord:
    """Captured information for a single LoRA token inside the hash log."""

    display_name: str
    hashes: set[str] = field(default_factory=set)
    reasons: list[str] = field(default_factory=list)


@dataclass
class MetadataEntry:
    """Metadata parsed for a single image filename."""

    loras: dict[str, LoraRecord]
    summary: dict[str, SummaryRecord]


@dataclass
class HashLogEntry:
    """Hash log parsed for a single image filename."""

    loras: dict[str, HashLogRecord]


def canonical_key(value: str) -> str:
    """Return a normalized key for a LoRA/embedding name."""

    cleaned = value.strip().strip("\"'").replace("\\", "/")
    base = cleaned.split("/")[-1]
    lower = base.lower()
    for ext in _MODEL_EXTENSIONS:
        if lower.endswith(ext):
            lower = lower[: -len(ext)]
            break
    return lower


def looks_like_filename(line: str) -> bool:
    """Return True when the line resembles an output filename."""

    return bool(_FILENAME_PATTERN.match(line.strip()))


def read_sectioned_file(path: Path) -> dict[str, str]:
    """Parse files that follow the metadata/hash log structure."""

    entries: dict[str, str] = {}
    current_name: str | None = None
    current_lines: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    total = len(lines)
    for idx, raw_line in enumerate(lines):
        line = raw_line.rstrip("\n")
        trimmed = line.strip()
        if current_name is None:
            if trimmed:
                current_name = trimmed
                current_lines = []
            continue
        if not trimmed:
            next_line = next((lines[j].strip() for j in range(idx + 1, total) if lines[j].strip()), None)
            if next_line and looks_like_filename(next_line):
                entries[current_name] = "\n".join(current_lines).strip()
                current_name = None
                current_lines = []
            else:
                current_lines.append(line)
            continue
        current_lines.append(line)
    if current_name is not None:
        entries[current_name] = "\n".join(current_lines).strip()
    return entries


def parse_metadata_block(block: str) -> MetadataEntry:
    """Extract LoRA fields and Hashes JSON data."""

    lora_names: dict[int, str] = {}
    lora_hashes: dict[int, str] = {}
    summary: dict[str, SummaryRecord] = {}

    for match in _LORA_NAME_PATTERN.finditer(block):
        idx = int(match.group(1))
        lora_names[idx] = match.group(2).strip()

    for match in _LORA_HASH_PATTERN.finditer(block):
        idx = int(match.group(1))
        lora_hashes[idx] = match.group(2).strip()

    for match in _HASHES_PATTERN.finditer(block):
        data = match.group(1)
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        for key, hash_value in payload.items():
            if not isinstance(key, str) or not isinstance(hash_value, str):
                continue
            if key.lower().startswith("lora:"):
                display = key.split(":", 1)[1]
                ckey = canonical_key(display)
                summary[ckey] = SummaryRecord(display_name=display, hash_value=hash_value)

    loras: dict[str, LoraRecord] = {}
    for idx, name in lora_names.items():
        display = name
        hash_value = lora_hashes.get(idx)
        ckey = canonical_key(display)
        loras[ckey] = LoraRecord(display_name=display, hash_value=hash_value)

    return MetadataEntry(loras=loras, summary=summary)


def parse_hashlog_block(block: str) -> HashLogEntry:
    """Build a mapping of LoRA names to their hashed values and errors."""

    entries: dict[str, HashLogRecord] = {}
    current_key: str | None = None
    current_display: str | None = None
    current_kind: str | None = None
    for line in block.splitlines():
        resolved_match = _RESOLVED_LINE.search(line)
        if resolved_match:
            current_kind = resolved_match.group("kind").lower()
            current_display = resolved_match.group("token").strip()
            current_key = canonical_key(current_display)
            if current_kind == "lora":
                entries.setdefault(
                    current_key,
                    HashLogRecord(display_name=current_display),
                )
            continue
        hash_match = _HASH_LINE.search(line)
        if hash_match and current_kind == "lora" and current_key:
            entries.setdefault(
                current_key,
                HashLogRecord(display_name=current_display or current_key),
            ).hashes.add(hash_match.group(1))
            continue
        unresolved_match = _UNRESOLVED_LINE.search(line)
        if unresolved_match:
            token = unresolved_match.group(1).strip()
            ckey = canonical_key(token)
            entries.setdefault(
                ckey,
                HashLogRecord(display_name=token),
            ).reasons.append("unresolved token")
            continue
        skipped_match = _SKIPPED_LINE.search(line)
        if skipped_match:
            token = skipped_match.group(1).strip()
            ckey = canonical_key(token)
            entries.setdefault(
                ckey,
                HashLogRecord(display_name=token),
            ).reasons.append("hash skipped")
            continue
    return HashLogEntry(loras=entries)


def collect_all_keys(entry: MetadataEntry, log_entry: HashLogEntry) -> list[str]:
    """Return the sorted union of canonical keys for a file."""

    keys = set(entry.loras.keys()) | set(entry.summary.keys()) | set(log_entry.loras.keys())
    return sorted(keys)


def describe_hashes(hashes: set[str]) -> str:
    if not hashes:
        return "-"
    if len(hashes) == 1:
        return next(iter(hashes))
    return ", ".join(sorted(hashes))


def compare_file(filename: str, entry: MetadataEntry, log_entry: HashLogEntry) -> list[str]:
    """Produce a formatted report for a single filename."""

    lines = [f"=== {filename} ==="]
    header = f"{'LoRA':30} | {'Log hash':15} | {'Metadata hash':15} | {'Hashes entry':15} | Notes"
    lines.append(header)
    lines.append("-" * len(header))
    for key in collect_all_keys(entry, log_entry):
        meta = entry.loras.get(key)
        summary = entry.summary.get(key)
        log = log_entry.loras.get(key)
        if meta:
            display = meta.display_name
        elif log:
            display = log.display_name
        elif summary:
            display = summary.display_name
        else:
            display = key
        log_hashes = describe_hashes(log.hashes) if log else "-"
        meta_hash = meta.hash_value if meta else None
        summary_hash = summary.hash_value if summary else None
        notes: list[str] = []
        cleaned_meta_hash = (meta_hash or "").strip()
        if not meta:
            notes.append("missing from metadata")
        elif not cleaned_meta_hash or cleaned_meta_hash.lower() in {"n/a", "none"}:
            notes.append("metadata hash missing")
        if log is None:
            notes.append("not in hash log")
        elif not log.hashes:
            notes.append("no log hash")
        if summary_hash is None and summary is None:
            notes.append("no Hashes entry")
        if log and cleaned_meta_hash and log.hashes and cleaned_meta_hash not in log.hashes:
            notes.append("metadata != log")
        if log and summary_hash and summary_hash not in log.hashes:
            notes.append("Hashes entry != log")
        if summary_hash and cleaned_meta_hash and summary_hash != cleaned_meta_hash:
            notes.append("metadata != Hashes entry")
        if log and log.reasons:
            notes.extend(log.reasons)
        lines.append(
            f"{display:30} | {log_hashes:15} | {cleaned_meta_hash or '-':15} | {summary_hash or '-':15} | "
            + (", ".join(notes) if notes else "OK")
        )
    return lines


def run(metadata_path: Path, hashlog_path: Path) -> str:
    """Generate the full comparison report."""

    metadata_sections = read_sectioned_file(metadata_path)
    hash_sections = read_sectioned_file(hashlog_path)
    shared = sorted(set(metadata_sections) & set(hash_sections))
    if not shared:
        return "No overlapping filenames between metadata dump and hash logs."
    reports: list[str] = []
    for filename in shared:
        metadata_entry = parse_metadata_block(metadata_sections[filename])
        hashlog_entry = parse_hashlog_block(hash_sections[filename])
        reports.extend(compare_file(filename, metadata_entry, hashlog_entry))
        reports.append("")
    return "\n".join(reports).rstrip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare LoRA hashes between metadata dumps and hash logs.")
    parser.add_argument(
        "--metadata",
        type=Path,
        default=_default_test_file("metadata_dump.txt"),
        help="Path to metadata_dump.txt (defaults to tests/tools/Test/metadata_dump.txt, falls back to tests/comfyui_cli_tests/Test)",
    )
    parser.add_argument(
        "--hashlogs",
        type=Path,
        default=_default_test_file("hash_logs.txt"),
        help="Path to hash_logs.txt (defaults to tests/tools/Test/hash_logs.txt, falls back to tests/comfyui_cli_tests/Test)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional destination file for the report. When omitted, prints to stdout.",
    )
    args = parser.parse_args()
    report = run(args.metadata, args.hashlogs)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
    else:
        print(report)


if __name__ == "__main__":
    main()
