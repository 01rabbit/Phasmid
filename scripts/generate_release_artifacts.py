#!/usr/bin/env python3
"""Generate local release review artifacts without network access."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import tarfile
from datetime import datetime, timezone
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".state",
    ".venv",
    "__pycache__",
    "release",
}
EXCLUDED_FILES = {"vault.bin"}
INCLUDED_SUFFIXES = {
    ".html",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".service",
    ".sh",
    ".toml",
    ".txt",
    ".yml",
    ".yaml",
}
INCLUDED_NAMES = {".gitignore", "LICENSE", "README.md"}


def _source_date_epoch(explicit: int | None = None) -> int:
    if explicit is not None:
        return max(0, int(explicit))
    value = os.environ.get("SOURCE_DATE_EPOCH", "0")
    try:
        return max(0, int(value))
    except ValueError:
        return 0


def should_include(path: Path, base_dir: Path):
    relative = path.relative_to(base_dir)
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return False
    if path.name in EXCLUDED_FILES:
        return False
    if path.name in INCLUDED_NAMES:
        return True
    return path.suffix in INCLUDED_SUFFIXES


def collect_release_files(base_dir: Path, excluded_roots: list[Path] | None = None):
    excluded_roots = [root.resolve() for root in (excluded_roots or [])]
    files = []
    for path in base_dir.rglob("*"):
        resolved = path.resolve()
        if any(resolved.is_relative_to(root) for root in excluded_roots):
            continue
        if path.is_file() and should_include(path, base_dir):
            files.append(path.relative_to(base_dir))
    return sorted(files, key=lambda item: item.as_posix())


def sha256_file(path: Path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(base_dir: Path, output_path: Path, files):
    lines = []
    for relative in files:
        digest = sha256_file(base_dir / relative)
        lines.append(f"{digest}  {relative.as_posix()}")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lines


def read_project_dependencies(pyproject_path: Path):
    if not pyproject_path.exists():
        return []
    dependencies = []
    in_dependencies = False
    for raw_line in pyproject_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "dependencies = [":
            in_dependencies = True
            continue
        if in_dependencies and line == "]":
            break
        if not in_dependencies or not line.startswith('"'):
            continue
        value = line.strip(",").strip('"')
        if value:
            dependencies.append(value)
    return sorted(set(dependencies))


def dependency_component(dependency: str):
    normalized = dependency.split(";", 1)[0].strip()
    if "==" in normalized:
        name, version = normalized.split("==", 1)
    else:
        name, version = normalized, None
    component = {
        "type": "library",
        "name": name,
        "purl": f"pkg:pypi/{name}",
    }
    if version:
        component["version"] = version
        component["purl"] = f"pkg:pypi/{name}@{version}"
    return component


def write_sbom(base_dir: Path, output_path: Path, source_date_epoch: int):
    dependencies = read_project_dependencies(base_dir / "pyproject.toml")
    timestamp = datetime.fromtimestamp(source_date_epoch, tz=timezone.utc).isoformat()
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": timestamp,
            "component": {
                "type": "application",
                "name": "phasmid-vault",
            },
        },
        "components": [dependency_component(dependency) for dependency in dependencies],
    }
    output_path.write_text(
        json.dumps(sbom, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return sbom


def write_archive(base_dir: Path, output_path: Path, files, source_date_epoch: int):
    with open(output_path, "wb") as raw:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=raw,
            mtime=source_date_epoch,
            compresslevel=9,
        ) as gz:
            with tarfile.open(fileobj=gz, mode="w") as archive:
                for relative in files:
                    abs_path = base_dir / relative
                    data = abs_path.read_bytes()
                    info = tarfile.TarInfo(name=relative.as_posix())
                    info.size = len(data)
                    info.mtime = source_date_epoch
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mode = 0o644
                    archive.addfile(info, io.BytesIO(data))


def sign_manifest(manifest_path: Path, signature_path: Path, key_path: Path):
    private_key = serialization.load_pem_private_key(
        key_path.read_bytes(),
        password=None,
    )
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("signing key must be an Ed25519 private key")
    signature = private_key.sign(manifest_path.read_bytes())
    signature_path.write_bytes(signature)


def verify_manifest_signature(
    manifest_path: Path, signature_path: Path, key_path: Path
):
    public_key = serialization.load_pem_public_key(key_path.read_bytes())
    if not isinstance(public_key, Ed25519PublicKey):
        raise ValueError("verify key must be an Ed25519 public key")
    try:
        public_key.verify(signature_path.read_bytes(), manifest_path.read_bytes())
    except InvalidSignature as exc:
        raise ValueError("manifest signature verification failed") from exc


def generate(
    base_dir: Path,
    output_dir: Path,
    archive: bool = False,
    signing_key: Path | None = None,
    source_date_epoch: int | None = None,
):
    base_dir = base_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    files = collect_release_files(base_dir, excluded_roots=[output_dir])
    epoch = _source_date_epoch(source_date_epoch)

    manifest_path = output_dir / "MANIFEST.sha256"
    manifest_sig_path = output_dir / "MANIFEST.sha256.sig"
    sbom_path = output_dir / "sbom.cyclonedx.json"
    summary_path = output_dir / "release-summary.json"

    manifest_lines = write_manifest(base_dir, manifest_path, files)
    sbom = write_sbom(base_dir, sbom_path, epoch)
    if signing_key is not None:
        sign_manifest(manifest_path, manifest_sig_path, signing_key)
    archive_path = None
    if archive:
        archive_path = output_dir / "phasmid-release.tar.gz"
        write_archive(base_dir, archive_path, files, epoch)

    summary = {
        "archive": archive_path.name if archive_path else None,
        "excluded_runtime_dirs": sorted(EXCLUDED_DIRS),
        "excluded_runtime_files": sorted(EXCLUDED_FILES),
        "files": len(files),
        "manifest": manifest_path.name,
        "manifest_entries": len(manifest_lines),
        "manifest_signature": manifest_sig_path.name if signing_key else None,
        "sbom": sbom_path.name,
        "sbom_components": len(sbom["components"]),
        "source_date_epoch": epoch,
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate local release review artifacts"
    )
    parser.add_argument("--base-dir", default=".", help="repository root")
    parser.add_argument(
        "--output-dir", default="release/local", help="artifact output directory"
    )
    parser.add_argument(
        "--archive", action="store_true", help="also write a local release archive"
    )
    parser.add_argument(
        "--signing-key",
        default=None,
        help="optional Ed25519 private key PEM for manifest signing",
    )
    parser.add_argument(
        "--source-date-epoch",
        type=int,
        default=None,
        help=(
            "UNIX epoch to stamp reproducible artifacts "
            "(default: SOURCE_DATE_EPOCH env or 0)"
        ),
    )
    args = parser.parse_args(argv)

    summary = generate(
        base_dir=Path(args.base_dir),
        output_dir=Path(args.output_dir),
        archive=args.archive,
        signing_key=Path(args.signing_key) if args.signing_key else None,
        source_date_epoch=args.source_date_epoch,
    )
    print(f"release artifacts generated: {summary['manifest']}, {summary['sbom']}")


if __name__ == "__main__":
    main()
