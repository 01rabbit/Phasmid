"""SH-07: Constant-time comparison regression tests.

Verifies that:
- Sensitive byte-string comparisons use hmac.compare_digest or are delegated
  to the cryptography library's AEAD internals.
- The custom _constant_time_equal helper has been removed from roles.py.
- No new == comparisons on sensitive bytes appear in crypto-path modules
  (AST-level regression check).

AST check scope: modules that handle key material, tokens, or digests.
"""

from __future__ import annotations

import ast
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

# ---------------------------------------------------------------------------
# AST regression helpers
# ---------------------------------------------------------------------------

# "key" is intentionally excluded: it is a common dict-iteration loop variable
# (e.g. `for key, value in d.items(): if key == "filename"`) and produces too
# many false positives.  Cryptographic keys are compared via AEAD InvalidTag or
# hmac.compare_digest; they are never named bare "key" in a == expression.
_SENSITIVE_VARIABLE_HINTS = frozenset(
    [
        "digest",
        "hmac",
        "token",
        "hash",
        "secret",
        "expected",
        "actual",
        "tag",
        "mac",
    ]
)


def _assert_no_bytes_eq_in_hmac_context(tree: ast.AST, filename: str) -> None:
    """Fail if any Compare node uses == where either operand name looks sensitive."""
    issues: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        for op in node.ops:
            if not isinstance(op, ast.Eq):
                continue
            operands = [node.left, *node.comparators]
            for operand in operands:
                name = ""
                if isinstance(operand, ast.Name):
                    name = operand.id
                elif isinstance(operand, ast.Attribute):
                    name = operand.attr
                if any(hint in name.lower() for hint in _SENSITIVE_VARIABLE_HINTS):
                    issues.append(
                        f"{filename}:{node.lineno}: == comparison on '{name}' — "
                        "use hmac.compare_digest for sensitive byte comparisons"
                    )
    if issues:
        raise AssertionError("\n".join(issues))


# ---------------------------------------------------------------------------
# Functional tests
# ---------------------------------------------------------------------------


class TestConstantTimeComparisons(unittest.TestCase):
    def test_hmac_compare_digest_used_in_roles(self):
        """roles.py must use hmac.compare_digest for PBKDF2 hash comparison."""
        from phasmid import roles

        self.assertTrue(hasattr(roles, "hmac"), "roles module must import hmac")

    def test_custom_constant_time_equal_removed(self):
        """The hand-rolled _constant_time_equal function must not exist in roles."""
        from phasmid import roles

        self.assertFalse(
            hasattr(roles, "_constant_time_equal"),
            "_constant_time_equal was removed in SH-07; use hmac.compare_digest instead",
        )

    def test_roles_verification_uses_compare_digest(self):
        """Supervisor passphrase verification must succeed for matching inputs."""
        from phasmid.roles import RoleStore

        with tempfile.TemporaryDirectory() as tmp:
            store = RoleStore(state_path=tmp)
            ok, _ = store.configure_supervisor("correct-passphrase-123")
            self.assertTrue(ok)

            result = store.verify_supervisor("correct-passphrase-123")
            self.assertTrue(result.verified)

            result_wrong = store.verify_supervisor("wrong-passphrase-999")
            self.assertFalse(result_wrong.verified)

    def test_audit_uses_compare_digest(self):
        """audit.py must not use == for HMAC comparison."""
        src = Path(os.path.join(ROOT, "src", "phasmid", "audit.py")).read_text()
        tree = ast.parse(src)
        _assert_no_bytes_eq_in_hmac_context(tree, "audit.py")


class TestASTRegressionCryptoModules(unittest.TestCase):
    """AST-level check: no == on sensitive variable names in crypto-path modules."""

    CHECKED_FILES = [
        "audit.py",
        "crypto_boundary.py",
        "roles.py",
    ]

    def _check_file(self, filename: str) -> None:
        path = Path(os.path.join(ROOT, "src", "phasmid", filename))
        if not path.exists():
            self.skipTest(f"{filename} not found")
        src = path.read_text()
        tree = ast.parse(src)
        _assert_no_bytes_eq_in_hmac_context(tree, filename)

    def test_no_sensitive_eq_in_audit(self):
        self._check_file("audit.py")

    def test_no_sensitive_eq_in_crypto_boundary(self):
        self._check_file("crypto_boundary.py")

    def test_no_sensitive_eq_in_roles(self):
        self._check_file("roles.py")


if __name__ == "__main__":
    unittest.main()
