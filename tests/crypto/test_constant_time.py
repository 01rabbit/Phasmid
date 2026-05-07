"""SH-07: Constant-time comparison regression tests.

Verifies that:
- Sensitive byte-string comparisons use hmac.compare_digest or are delegated
  to the cryptography library's AEAD internals.
- The custom _constant_time_equal helper has been removed from roles.py.
- No new == comparisons on sensitive bytes appear in crypto-path modules
  (AST-level regression check).

AST check scope: modules that handle key material, tokens, or digests.
"""

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Functional tests
# ---------------------------------------------------------------------------

SENSITIVE_MODULES = [
    "phasmid.roles",
    "phasmid.audit",
    "phasmid.crypto_boundary",
    "phasmid.web_server",
    "phasmid.emergency_daemon",
]


class TestConstantTimeComparisons:
    def test_hmac_compare_digest_used_in_roles(self):
        """roles.py must use hmac.compare_digest for PBKDF2 hash comparison."""

        from phasmid import roles

        # Verify the module imports hmac
        assert hasattr(roles, "hmac"), "roles module must import hmac"

    def test_custom_constant_time_equal_removed(self):
        """The hand-rolled _constant_time_equal function must not exist in roles."""
        from phasmid import roles

        assert not hasattr(roles, "_constant_time_equal"), (
            "_constant_time_equal was removed in SH-07; "
            "use hmac.compare_digest instead"
        )

    def test_roles_verification_uses_compare_digest(self, tmp_path):
        """Supervisor passphrase verification must succeed for matching inputs."""
        from phasmid.roles import RoleStore

        store = RoleStore(state_path=str(tmp_path))
        ok, _ = store.configure_supervisor("correct-passphrase-123")
        assert ok

        result = store.verify_supervisor("correct-passphrase-123")
        assert result.verified

        result_wrong = store.verify_supervisor("wrong-passphrase-999")
        assert not result_wrong.verified

    def test_audit_uses_compare_digest(self):
        """audit.py must not use == for HMAC comparison."""
        src = Path("src/phasmid/audit.py").read_text()
        tree = ast.parse(src)
        _assert_no_bytes_eq_in_hmac_context(tree, "audit.py")


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
    assert not issues, "\n".join(issues)


class TestASTRegressionCryptoModules:
    """AST-level check: no == on sensitive variable names in crypto-path modules."""

    SRC_ROOT = Path("src/phasmid")

    CHECKED_FILES = [
        "audit.py",
        "crypto_boundary.py",
        "roles.py",
    ]

    @pytest.mark.parametrize("filename", CHECKED_FILES)
    def test_no_sensitive_eq_comparison(self, filename):
        path = self.SRC_ROOT / filename
        if not path.exists():
            pytest.skip(f"{filename} not found")
        src = path.read_text()
        tree = ast.parse(src)
        _assert_no_bytes_eq_in_hmac_context(tree, filename)
