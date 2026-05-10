from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _read_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _extract_runtime_requirements(req_lines: list[str]) -> dict[str, str]:
    deps: dict[str, str] = {}
    for line in req_lines:
        marker_split = line.split(";", 1)[0].strip()
        match = re.match(r"^([A-Za-z0-9_.-]+)==(.+)$", marker_split)
        if not match:
            continue
        deps[match.group(1).lower()] = match.group(2).strip()
    return deps


def _extract_pyproject_deps(pyproject_text: str) -> dict[str, str]:
    deps: dict[str, str] = {}
    in_deps = False
    for raw in pyproject_text.splitlines():
        line = raw.strip()
        if line == "dependencies = [":
            in_deps = True
            continue
        if in_deps and line == "]":
            break
        if not in_deps or not line.startswith('"'):
            continue
        dep = line.strip(",").strip('"')
        marker_split = dep.split(";", 1)[0].strip()
        match = re.match(r"^([A-Za-z0-9_.-]+)==(.+)$", marker_split)
        if not match:
            continue
        deps[match.group(1).lower()] = match.group(2).strip()
    return deps


class DependencyPolicyTests(unittest.TestCase):
    def test_runtime_requirements_are_pinned(self):
        reqs = _read_lines(ROOT / "requirements.txt")
        for line in reqs:
            marker_split = line.split(";", 1)[0].strip()
            self.assertRegex(
                marker_split,
                r"^[A-Za-z0-9_.-]+==.+$",
                msg=f"requirement must be pinned: {line}",
            )

    def test_critical_crypto_dependencies_are_fully_pinned(self):
        runtime = _extract_runtime_requirements(_read_lines(ROOT / "requirements.txt"))
        self.assertIn("cryptography", runtime)
        self.assertIn("argon2-cffi", runtime)
        self.assertRegex(runtime["cryptography"], r"^\d")
        self.assertRegex(runtime["argon2-cffi"], r"^\d")

    def test_pyproject_and_requirements_runtime_sets_match(self):
        runtime = _extract_runtime_requirements(_read_lines(ROOT / "requirements.txt"))
        pyproject_runtime = _extract_pyproject_deps(
            (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(runtime, pyproject_runtime)

    def test_dependency_policy_docs_exist(self):
        self.assertTrue((ROOT / "docs" / "DEPENDENCIES.md").exists())
        self.assertTrue((ROOT / "docs" / "REPRODUCIBLE_BUILDS.md").exists())
        self.assertTrue((ROOT / "docs" / "VERSIONING.md").exists())
        self.assertTrue((ROOT / "CHANGELOG.md").exists())


if __name__ == "__main__":
    unittest.main()
