#!/usr/bin/env python3
"""Generate local release review artifacts without network access."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tarfile

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


def should_include(path: Path, base_dir: Path):
    relative = path.relative_to(base_dir)
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return False
    if path.name in EXCLUDED_FILES:
        return False
    if path.name in INCLUDED_NAMES:
        return True
    return path.suffix in INCLUDED_SUFFIXES


def collect_release_files(base_dir: Path):
    files = []
    for path in base_dir.rglob("*"):
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
    return dependencies


def dependency_component(dependency: str):
    if "==" in dependency:
        name, version = dependency.split("==", 1)
    else:
        name, version = dependency, None
    component = {
        "type": "library",
        "name": name,
        "purl": f"pkg:pypi/{name}",
    }
    if version:
        component["version"] = version
        component["purl"] = f"pkg:pypi/{name}@{version}"
    return component


def write_sbom(base_dir: Path, output_path: Path):
    dependencies = read_project_dependencies(base_dir / "pyproject.toml")
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": {
                "type": "application",
                "name": "phantasm-vault",
            },
        },
        "components": [dependency_component(dependency) for dependency in dependencies],
    }
    output_path.write_text(
        json.dumps(sbom, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return sbom


def write_archive(base_dir: Path, output_path: Path, files):
    with tarfile.open(output_path, "w:gz") as archive:
        for relative in files:
            archive.add(base_dir / relative, arcname=relative.as_posix())


def generate(base_dir: Path, output_dir: Path, archive: bool = False):
    base_dir = base_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    files = collect_release_files(base_dir)

    manifest_path = output_dir / "MANIFEST.sha256"
    sbom_path = output_dir / "sbom.cyclonedx.json"
    summary_path = output_dir / "release-summary.json"

    manifest_lines = write_manifest(base_dir, manifest_path, files)
    sbom = write_sbom(base_dir, sbom_path)
    archive_path = None
    if archive:
        archive_path = output_dir / "phantasm-release.tar.gz"
        write_archive(base_dir, archive_path, files)

    summary = {
        "archive": archive_path.name if archive_path else None,
        "excluded_runtime_dirs": sorted(EXCLUDED_DIRS),
        "excluded_runtime_files": sorted(EXCLUDED_FILES),
        "files": len(files),
        "manifest": manifest_path.name,
        "manifest_entries": len(manifest_lines),
        "sbom": sbom_path.name,
        "sbom_components": len(sbom["components"]),
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
    args = parser.parse_args(argv)

    summary = generate(
        base_dir=Path(args.base_dir),
        output_dir=Path(args.output_dir),
        archive=args.archive,
    )
    print(f"release artifacts generated: {summary['manifest']}, {summary['sbom']}")


if __name__ == "__main__":
    main()
