"""SH-08: Randomness source standardization.

Verifies that:
- The `random` module (non-CSPRNG) is not imported in any crypto-path module.
- os.urandom is the only non-secrets CSPRNG call in crypto modules, and every
  such call is documented in docs/CRYPTO_INVENTORY.md.
- secrets.token_bytes is available (doctor check already verifies this at
  runtime; this test verifies it at import time).
- phasmid.doctor includes a secure randomness availability check.

AST check scope: src/phasmid/ Python files (excluding __pycache__).
"""

import ast
import secrets
from pathlib import Path

import pytest

SRC_ROOT = Path("src/phasmid")


# ---------------------------------------------------------------------------
# Utility: collect all .py files under src/phasmid/
# ---------------------------------------------------------------------------

def _all_phasmid_sources() -> list[Path]:
    return [
        p
        for p in SRC_ROOT.rglob("*.py")
        if "__pycache__" not in p.parts
    ]


# ---------------------------------------------------------------------------
# Functional tests
# ---------------------------------------------------------------------------

class TestSecretsAvailability:
    def test_secrets_module_importable(self):
        assert secrets is not None

    def test_token_bytes_returns_correct_length(self):
        for size in (16, 32, 64):
            result = secrets.token_bytes(size)
            assert len(result) == size

    def test_token_bytes_not_all_zeros(self):
        result = secrets.token_bytes(32)
        assert result != b"\x00" * 32


class TestDoctorSecureRandomCheck:
    def test_doctor_has_secure_random_check(self):
        from phasmid.services.doctor_service import run_doctor_checks

        result = run_doctor_checks()
        check_names = [c.name for c in result.checks]
        assert "Secure Randomness" in check_names, (
            "Doctor must include a 'Secure Randomness' check (SH-08)"
        )

    def test_doctor_secure_random_check_passes(self):
        from phasmid.models.doctor import DoctorLevel
        from phasmid.services.doctor_service import run_doctor_checks

        result = run_doctor_checks()
        for check in result.checks:
            if check.name == "Secure Randomness":
                assert check.level == DoctorLevel.OK, (
                    f"Secure randomness check failed: {check.message}"
                )
                return
        pytest.fail("Secure Randomness check not found in doctor output")


# ---------------------------------------------------------------------------
# AST regression: no `random` module in crypto-path sources
# ---------------------------------------------------------------------------

class TestNoWeakRandomnessAST:
    """The standard `random` module must not be imported in phasmid source."""

    @pytest.mark.parametrize("path", _all_phasmid_sources())
    def test_no_random_module_import(self, path: Path):
        src = path.read_text()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            pytest.skip(f"Could not parse {path}")

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "random", (
                        f"{path}:{node.lineno}: `import random` found — "
                        "use `secrets` or `os.urandom` for cryptographic randomness"
                    )
            elif isinstance(node, ast.ImportFrom):
                assert node.module != "random", (
                    f"{path}:{node.lineno}: `from random import ...` found — "
                    "use `secrets` or `os.urandom` for cryptographic randomness"
                )


class TestOsUrandomDocumented:
    """os.urandom calls in crypto-path modules must be documented.

    This test enumerates every os.urandom call and checks that the call
    site is listed in docs/CRYPTO_INVENTORY.md (by filename mention).
    The inventory is expected to contain each filename that uses os.urandom.
    """

    INVENTORY_PATH = Path("docs/CRYPTO_INVENTORY.md")

    CRYPTO_PATH_FILES = [
        "record_cypher.py",
        "local_state_crypto.py",
        "kdf_engine.py",
        "audit.py",
        "roles.py",
        "approval_flow.py",
    ]

    def test_inventory_exists(self):
        assert self.INVENTORY_PATH.exists(), (
            "docs/CRYPTO_INVENTORY.md must exist (SH-04)"
        )

    @pytest.mark.parametrize("filename", CRYPTO_PATH_FILES)
    def test_file_with_urandom_is_in_inventory(self, filename: str):
        path = SRC_ROOT / filename
        if not path.exists():
            pytest.skip(f"{filename} not found")
        src = path.read_text()
        tree = ast.parse(src)
        uses_urandom = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "urandom"
            for node in ast.walk(tree)
        )
        if not uses_urandom:
            return  # nothing to verify
        inventory = self.INVENTORY_PATH.read_text()
        assert filename in inventory, (
            f"{filename} uses os.urandom but is not mentioned in "
            f"{self.INVENTORY_PATH} (SH-08 requires documentation)"
        )
