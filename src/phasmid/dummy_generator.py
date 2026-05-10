"""
Plausible dummy dataset generator for coercion-safe disclosure.

Generates a locally-consistent set of benign files adapted to a selected
context profile. The generator does NOT:

  - forge forensic artifacts
  - fake kernel logs or system events
  - tamper with filesystem metadata for anti-forensic purposes
  - claim to produce content indistinguishable under expert forensic analysis

Generated content is advisory plausibility material only.
"""

from __future__ import annotations

import json
import os
import string
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence, TypeVar

from . import config
from .context_profile import (
    ContextProfile,
    ProfileValidationResult,
    validate_against_profile,
)


@dataclass
class DummyGeneratorConfig:
    target_size_bytes: int
    occupancy_ratio: float
    profile: ContextProfile
    output_dir: str | Path

    def effective_dummy_size_bytes(self) -> int:
        return max(0, int(self.target_size_bytes * self.occupancy_ratio))


@dataclass
class GeneratedDummyReport:
    output_dir: str
    profile_name: str
    files_created: int
    total_bytes_written: int
    directory_count: int
    extension_distribution: dict[str, int]
    plausibility: ProfileValidationResult
    container_size_bytes: int
    occupancy_ratio: float
    size_distribution: dict[str, int]
    evaluation_report_path: str
    warnings: list[str] = field(default_factory=list)


_BENIGN_TEXT_FRAGMENTS = [
    b"Meeting notes from the field visit.\n",
    b"Checklist item completed.\n",
    b"Status: nominal.\n",
    b"Location: on-site.\n",
    b"Reference document enclosed.\n",
    b"See attached for details.\n",
    b"Review and confirm.\n",
    b"No issues observed.\n",
    b"Scheduled maintenance complete.\n",
    b"Observations noted for follow-up.\n",
    b"Local copy archived.\n",
    b"Version: current.\n",
    b"Last updated: see file date.\n",
    b"Contact local coordinator.\n",
    b"Standard operating procedure applies.\n",
]

_LOG_LINE_FRAGMENTS = [
    b"[INFO] Service check passed\n",
    b"[INFO] Connection nominal\n",
    b"[INFO] Configuration loaded\n",
    b"[WARN] Retry attempt 1 of 3\n",
    b"[INFO] Cache cleared\n",
    b"[INFO] Background task complete\n",
    b"[INFO] Initialization complete\n",
    b"[INFO] Shutdown sequence started\n",
    b"[INFO] Device ready\n",
    b"[INFO] Health check OK\n",
]


T = TypeVar("T")


def _urandom_choice(items: Sequence[T]) -> T:
    """Pick a uniformly random item using os.urandom."""
    if not items:
        raise ValueError("cannot choose from empty sequence")
    n = len(items)
    idx = int.from_bytes(os.urandom(4), "little") % n
    return items[idx]


def _urandom_int(low: int, high: int) -> int:
    """Return a random integer in [low, high] using os.urandom."""
    span = high - low + 1
    raw = int.from_bytes(os.urandom(4), "little")
    return low + (raw % span)


def _generate_text_content(target_bytes: int) -> bytes:
    parts: list[bytes] = []
    total = 0
    while total < target_bytes:
        frag = _urandom_choice(_BENIGN_TEXT_FRAGMENTS)
        parts.append(frag)
        total += len(frag)
    return b"".join(parts)[:target_bytes]


def _generate_log_content(target_bytes: int) -> bytes:
    parts: list[bytes] = []
    total = 0
    while total < target_bytes:
        frag = _urandom_choice(_LOG_LINE_FRAGMENTS)
        parts.append(frag)
        total += len(frag)
    return b"".join(parts)[:target_bytes]


def _generate_json_content(target_bytes: int) -> bytes:
    keys = [b"status", b"version", b"item", b"ref", b"note", b"count", b"id"]
    entries: list[bytes] = []
    total = 0
    while total < target_bytes:
        k = _urandom_choice(keys)
        v = _random_alnum_bytes(8)
        entry = b'  "' + k + b'": "' + v + b'"'
        entries.append(entry)
        total += len(entry)
    body = b"{\n" + b",\n".join(entries) + b"\n}"
    return body[:target_bytes]


def _generate_csv_content(target_bytes: int) -> bytes:
    header = b"id,name,status,value\n"
    rows: list[bytes] = [header]
    total = len(header)
    while total < target_bytes:
        row_id = str(_urandom_int(1, 9999)).encode()
        name = b"item_" + _random_alnum_bytes(6)
        status = (
            b"active" if (int.from_bytes(os.urandom(1), "little") > 76) else b"inactive"
        )
        value = f"{_urandom_int(0, 100000) / 100:.2f}".encode()
        row = row_id + b"," + name + b"," + status + b"," + value + b"\n"
        rows.append(row)
        total += len(row)
    return b"".join(rows)[:target_bytes]


def _generate_binary_stub(target_bytes: int) -> bytes:
    chunk_size = min(target_bytes, 512)
    data = os.urandom(chunk_size)
    if len(data) < target_bytes:
        data = data + b"\x00" * (target_bytes - len(data))
    return data[:target_bytes]


def _random_alnum_bytes(length: int) -> bytes:
    alphabet = string.ascii_lowercase + string.digits
    return bytes(_urandom_choice(alphabet.encode()) for _ in range(length))


def _random_filename(ext: str) -> str:
    stem_len = _urandom_int(8, 16)
    stem = _random_alnum_bytes(stem_len).decode("ascii", errors="ignore")
    return f"{stem}.{ext.lstrip('.')}"


def _bucket_file_sizes(file_sizes: list[int]) -> dict[str, int]:
    buckets = {
        "lt_64kb": 0,
        "64kb_to_256kb": 0,
        "256kb_to_1mb": 0,
        "1mb_to_4mb": 0,
        "gte_4mb": 0,
    }
    for size in file_sizes:
        if size < 64 * 1024:
            buckets["lt_64kb"] += 1
        elif size < 256 * 1024:
            buckets["64kb_to_256kb"] += 1
        elif size < 1024 * 1024:
            buckets["256kb_to_1mb"] += 1
        elif size < 4 * 1024 * 1024:
            buckets["1mb_to_4mb"] += 1
        else:
            buckets["gte_4mb"] += 1
    return buckets


def _apply_mtime_variation(file_paths: list[Path]) -> None:
    if not file_paths:
        return
    base_ns = time.time_ns()
    # Keep mtime near write time but avoid uniform timestamps across generated files.
    for idx, fpath in enumerate(file_paths):
        delta_ns = (idx + 1) * 1_000_000 + int.from_bytes(os.urandom(2), "little")
        ts_ns = base_ns - delta_ns
        try:
            os.utime(fpath, ns=(ts_ns, ts_ns))
        except OSError:
            continue


def _resolve_container_size(target_size_bytes: int) -> int:
    container_path = Path(config.dummy_container_path())
    try:
        return container_path.stat().st_size
    except OSError:
        return max(0, int(target_size_bytes))


def _write_local_evaluation_report(
    *,
    output_dir: Path,
    profile_name: str,
    container_size_bytes: int,
    dummy_size_bytes: int,
    occupancy_ratio: float,
    file_count: int,
    size_distribution: dict[str, int],
) -> Path:
    report_path = output_dir / "dummy_profile_eval.json"
    payload = {
        "profile_name": profile_name,
        "container_size_bytes": container_size_bytes,
        "dummy_size_bytes": dummy_size_bytes,
        "occupancy_ratio": occupancy_ratio,
        "file_count": file_count,
        "size_distribution": size_distribution,
    }
    report_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8"
    )
    return report_path


_TEXT_EXTENSIONS = {"txt", "md", "bib", "html", "yaml", "xml"}
_LOG_EXTENSIONS = {"log"}
_JSON_EXTENSIONS = {"json"}
_CSV_EXTENSIONS = {"csv"}


def _generate_file_content(ext: str, target_bytes: int) -> bytes:
    ext = ext.lower().lstrip(".")
    if target_bytes <= 0:
        return b""
    if ext in _TEXT_EXTENSIONS:
        return _generate_text_content(target_bytes)
    if ext in _LOG_EXTENSIONS:
        return _generate_log_content(target_bytes)
    if ext in _JSON_EXTENSIONS:
        return _generate_json_content(target_bytes)
    if ext in _CSV_EXTENSIONS:
        return _generate_csv_content(target_bytes)
    return _generate_binary_stub(target_bytes)


def generate_dummy_dataset(config_data: DummyGeneratorConfig) -> GeneratedDummyReport:
    """
    Generate a plausible dummy dataset in `config.output_dir`.

    Creates directories and files consistent with the selected context profile.
    """
    output_dir = Path(config_data.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    profile = config_data.profile
    effective_size = config_data.effective_dummy_size_bytes()

    extensions = list(profile.dummy_content_types)
    directories = list(profile.typical_directories)

    dirs_to_create = [output_dir]
    for d in directories:
        subdir = output_dir / d
        subdir.mkdir(parents=True, exist_ok=True)
        dirs_to_create.append(subdir)

    configured_min_size_bytes = config.dummy_min_size_mb() * 1024 * 1024
    configured_min_file_count = config.dummy_min_file_count()
    occupancy_warn_threshold = config.dummy_occupancy_warn()

    required_bytes = effective_size
    required_file_count = profile.min_file_count

    remaining_bytes = required_bytes
    files_created = 0
    total_bytes_written = 0
    ext_dist: dict[str, int] = {}
    file_sizes: list[int] = []
    written_paths: list[Path] = []

    if effective_size > 0 and profile.min_file_count > 0:
        avg_file_size = max(512, effective_size // profile.min_file_count)
    else:
        avg_file_size = 8 * 1024

    while remaining_bytes > 0:
        ext = _urandom_choice(extensions)
        parent = _urandom_choice(dirs_to_create)
        fname = _random_filename(ext)
        fpath = parent / fname

        if remaining_bytes > 0:
            size = min(remaining_bytes, max(512, avg_file_size))
        else:
            size = max(512, avg_file_size)

        content = _generate_file_content(ext, size)
        try:
            fpath.write_bytes(content)
        except OSError:
            break

        files_created += 1
        bytes_written = len(content)
        total_bytes_written += bytes_written
        remaining_bytes = max(0, remaining_bytes - bytes_written)
        ext_dist[ext] = ext_dist.get(ext, 0) + 1
        file_sizes.append(bytes_written)
        written_paths.append(fpath)

    _apply_mtime_variation(written_paths)

    container_size_bytes = _resolve_container_size(config_data.target_size_bytes)
    occupancy_ratio = 0.0
    if container_size_bytes > 0:
        occupancy_ratio = total_bytes_written / float(container_size_bytes)

    plausibility = validate_against_profile(
        profile=profile,
        container_size_bytes=container_size_bytes,
        dummy_size_bytes=total_bytes_written,
        file_count=files_created,
        extension_distribution=ext_dist,
    )

    size_distribution = _bucket_file_sizes(file_sizes)
    report_path = _write_local_evaluation_report(
        output_dir=output_dir,
        profile_name=profile.profile_name,
        container_size_bytes=container_size_bytes,
        dummy_size_bytes=total_bytes_written,
        occupancy_ratio=occupancy_ratio,
        file_count=files_created,
        size_distribution=size_distribution,
    )

    warnings = list(plausibility.warnings)
    if files_created < required_file_count:
        warnings.append(
            f"only {files_created} files created; profile minimum is {required_file_count}"
        )
    if files_created < configured_min_file_count:
        warnings.append(
            f"only {files_created} files created; configured minimum is {configured_min_file_count}"
        )
    if total_bytes_written < configured_min_size_bytes:
        warnings.append(
            f"dummy size {total_bytes_written} bytes is below configured minimum {configured_min_size_bytes} bytes"
        )
    if container_size_bytes > 0 and occupancy_ratio < occupancy_warn_threshold:
        warnings.append(
            "dummy profile size is disproportionately small relative to the local container"
        )
    if total_bytes_written == 0:
        warnings.append("no bytes were written - dataset is empty")

    return GeneratedDummyReport(
        output_dir=str(output_dir),
        profile_name=profile.profile_name,
        files_created=files_created,
        total_bytes_written=total_bytes_written,
        directory_count=len(dirs_to_create),
        extension_distribution=ext_dist,
        plausibility=plausibility,
        container_size_bytes=container_size_bytes,
        occupancy_ratio=occupancy_ratio,
        size_distribution=size_distribution,
        evaluation_report_path=str(report_path),
        warnings=warnings,
    )


def import_sample_directory(
    source_dir: str | Path,
    output_dir: str | Path,
    *,
    allowed_extensions: Sequence[str] | None = None,
    max_bytes: int | None = None,
) -> tuple[int, int, list[str]]:
    """
    Import benign files from `source_dir` into `output_dir`.

    Returns (files_copied, bytes_copied, warnings).
    Only copies regular files; does not follow symlinks.
    If `allowed_extensions` is provided, only matching files are copied.
    If `max_bytes` is provided, stops when the limit is reached.
    """
    src = Path(source_dir)
    dst = Path(output_dir)

    if not src.exists() or not src.is_dir():
        return 0, 0, [f"source directory does not exist or is not a directory: {src}"]

    dst.mkdir(parents=True, exist_ok=True)

    ext_filter = (
        {e.lower().lstrip(".") for e in allowed_extensions}
        if allowed_extensions
        else None
    )

    files_copied = 0
    bytes_copied = 0
    warnings: list[str] = []

    for item in src.rglob("*"):
        if not item.is_file() or item.is_symlink():
            continue
        ext = item.suffix.lower().lstrip(".")
        if ext_filter is not None and ext not in ext_filter:
            continue
        try:
            size = item.stat().st_size
        except OSError:
            continue
        if max_bytes is not None and bytes_copied + size > max_bytes:
            warnings.append(f"max_bytes limit reached; {item.name} skipped")
            break

        rel = item.relative_to(src)
        dest_file = dst / rel
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = item.read_bytes()
            dest_file.write_bytes(data)
        except OSError:
            continue

        files_copied += 1
        bytes_copied += len(data)

    return files_copied, bytes_copied, warnings
