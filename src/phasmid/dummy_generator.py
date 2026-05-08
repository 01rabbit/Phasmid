"""
Plausible dummy dataset generator for coercion-safe disclosure.

Generates a locally-consistent set of benign files adapted to a selected
context profile. The generator does NOT:

  - forge forensic artifacts
  - fake kernel logs or system events
  - perform timestamp forgery
  - tamper with filesystem metadata for anti-forensic purposes
  - claim to produce content indistinguishable under expert forensic analysis

Generated content is advisory plausibility material only.
"""

from __future__ import annotations

import os
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence, TypeVar

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
        status = b"active" if (int.from_bytes(os.urandom(1), "little") > 76) else b"inactive"
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


def generate_dummy_dataset(config: DummyGeneratorConfig) -> GeneratedDummyReport:
    """
    Generate a plausible dummy dataset in `config.output_dir`.

    Creates directories and files consistent with the selected context profile.
    Does not forge metadata, timestamps, or forensic artifacts.
    """
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    profile = config.profile
    effective_size = config.effective_dummy_size_bytes()

    extensions = list(profile.dummy_content_types)
    directories = list(profile.typical_directories)

    dirs_to_create = [output_dir]
    for d in directories:
        subdir = output_dir / d
        subdir.mkdir(parents=True, exist_ok=True)
        dirs_to_create.append(subdir)

    if effective_size > 0 and profile.min_file_count > 0:
        avg_file_size = effective_size // profile.min_file_count
    else:
        avg_file_size = 8 * 1024

    remaining_bytes = effective_size
    files_created = 0
    total_bytes_written = 0
    ext_dist: dict[str, int] = {}

    for _ in range(max(profile.min_file_count, 1)):
        if remaining_bytes <= 0:
            break

        ext = _urandom_choice(extensions)
        parent = _urandom_choice(dirs_to_create)
        fname = _random_filename(ext)
        fpath = parent / fname

        size = min(remaining_bytes, max(512, avg_file_size))
        content = _generate_file_content(ext, size)
        try:
            fpath.write_bytes(content)
        except OSError:
            continue

        files_created += 1
        total_bytes_written += len(content)
        remaining_bytes -= len(content)
        ext_dist[ext] = ext_dist.get(ext, 0) + 1

    container_size_bytes = config.target_size_bytes
    plausibility = validate_against_profile(
        profile=profile,
        container_size_bytes=container_size_bytes,
        dummy_size_bytes=total_bytes_written,
        file_count=files_created,
        extension_distribution=ext_dist,
    )

    warnings = list(plausibility.warnings)
    if files_created < profile.min_file_count:
        warnings.append(
            f"only {files_created} files created; profile minimum is {profile.min_file_count}"
        )
    if total_bytes_written == 0:
        warnings.append("no bytes were written — dataset is empty")

    return GeneratedDummyReport(
        output_dir=str(output_dir),
        profile_name=profile.profile_name,
        files_created=files_created,
        total_bytes_written=total_bytes_written,
        directory_count=len(dirs_to_create),
        extension_distribution=ext_dist,
        plausibility=plausibility,
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
            dest_file.write_bytes(item.read_bytes())
            files_copied += 1
            bytes_copied += size
        except OSError as exc:
            warnings.append(f"could not copy {item.name}: {exc}")

    return files_copied, bytes_copied, warnings


def _random_filename(ext: str) -> str:
    length = _urandom_int(6, 14)
    stem = _random_alnum_bytes(length).decode()
    return f"{stem}.{ext}"
