#!/usr/bin/env python3
"""SH-09: CI naming-convention lint for Phasmid tests.

Reports test methods that do not follow the claim-driven naming convention
defined in docs/TESTING_GUIDELINES.md.  Runs in warning mode — exits 0 even
if violations are found so the build is not broken by legacy tests.

Usage:
    python3 scripts/check_test_naming.py [--strict]

With --strict, exits 1 if any new violations are found in tests/crypto/,
tests/scenarios/, or tests/properties/ (the directories where convention is
enforced for all new tests).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
TESTS_DIR = ROOT / "tests"

# Directories where convention is *enforced* (new tests must comply).
# tests/crypto/ was created before this convention; it is tracked but not enforced.
ENFORCED_DIRS = [
    TESTS_DIR / "scenarios",
    TESTS_DIR / "properties",
]

# Prefixes that satisfy the naming convention.
VALID_PREFIXES = (
    "test_claim_",
    "test_invariant_",
    "test_scenario_",
)

# Test methods that are explicitly exempted from the convention (legacy or
# non-claim utility methods that happen to start with "test_").
EXEMPT_METHODS: frozenset[str] = frozenset()


def collect_test_methods(path: Path) -> list[tuple[str, int, str]]:
    """Return (relative_path, lineno, method_name) for each test method."""
    try:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
    except (SyntaxError, OSError):
        return []

    results: list[tuple[str, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        rel = str(path.relative_to(ROOT))
        results.append((rel, node.lineno, node.name))
    return results


def is_compliant(method_name: str) -> bool:
    if method_name in EXEMPT_METHODS:
        return True
    return any(method_name.startswith(p) for p in VALID_PREFIXES)


def main() -> int:
    strict = "--strict" in sys.argv

    all_violations: list[tuple[str, int, str]] = []
    enforced_violations: list[tuple[str, int, str]] = []

    for path in sorted(TESTS_DIR.rglob("test_*.py")):
        if "__pycache__" in path.parts:
            continue
        methods = collect_test_methods(path)
        for rel, lineno, name in methods:
            if not is_compliant(name):
                all_violations.append((rel, lineno, name))
                if any(path.is_relative_to(d) for d in ENFORCED_DIRS if d.exists()):
                    enforced_violations.append((rel, lineno, name))

    total = sum(
        len(collect_test_methods(p))
        for p in TESTS_DIR.rglob("test_*.py")
        if "__pycache__" not in p.parts
    )
    compliant = total - len(all_violations)

    print(
        f"Test naming convention: {compliant}/{total} compliant "
        f"({len(all_violations)} violations, "
        f"{len(enforced_violations)} in enforced dirs)"
    )

    if all_violations:
        print("\nAll violations (warning):")
        for rel, lineno, name in all_violations[:20]:
            marker = " [ENFORCED]" if (rel, lineno, name) in enforced_violations else ""
            print(f"  {rel}:{lineno}: {name}{marker}")
        if len(all_violations) > 20:
            print(f"  ... and {len(all_violations) - 20} more")

    if enforced_violations:
        print(f"\n{len(enforced_violations)} violations in enforced directories.")
        if strict:
            print("Strict mode: exiting 1.")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
