import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "generate_release_artifacts.py"


def load_release_script():
    spec = importlib.util.spec_from_file_location(
        "generate_release_artifacts",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseArtifactTests(unittest.TestCase):
    def _sha256_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        digest.update(path.read_bytes())
        return digest.hexdigest()

    def test_manifest_and_sbom_generation_exclude_runtime_files(self):
        module = load_release_script()
        tmpdir = Path(tempfile.mkdtemp())
        output_dir = tmpdir / "out"
        (tmpdir / "src" / "phasmid").mkdir(parents=True)
        (tmpdir / "src" / "phasmid" / "example.py").write_text(
            "print('ok')\n",
            encoding="utf-8",
        )
        (tmpdir / ".state").mkdir()
        (tmpdir / ".state" / "access.bin").write_bytes(b"local")
        (tmpdir / "vault.bin").write_bytes(b"vault")
        (tmpdir / "pyproject.toml").write_text(
            '[project]\ndependencies = [\n    "cryptography==46.0.7",\n]\n',
            encoding="utf-8",
        )

        summary = module.generate(tmpdir, output_dir, archive=True)

        manifest = (output_dir / "MANIFEST.sha256").read_text(encoding="utf-8")
        self.assertIn("src/phasmid/example.py", manifest)
        self.assertNotIn(".state/access.bin", manifest)
        self.assertNotIn("vault.bin", manifest)
        self.assertEqual(summary["archive"], "phasmid-release.tar.gz")

        sbom = json.loads(
            (output_dir / "sbom.cyclonedx.json").read_text(encoding="utf-8")
        )
        self.assertEqual(sbom["bomFormat"], "CycloneDX")
        self.assertEqual(sbom["components"][0]["name"], "cryptography")
        self.assertEqual(
            sbom["metadata"]["timestamp"],
            "1970-01-01T00:00:00+00:00",
        )

    def test_dependency_parser_handles_unpinned_values(self):
        module = load_release_script()
        tmpdir = Path(tempfile.mkdtemp())
        pyproject = tmpdir / "pyproject.toml"
        pyproject.write_text(
            '[project]\ndependencies = [\n    "fastapi",\n]\n',
            encoding="utf-8",
        )

        self.assertEqual(module.read_project_dependencies(pyproject), ["fastapi"])

    def test_manifest_signature_is_generated_and_verifiable(self):
        module = load_release_script()
        tmpdir = Path(tempfile.mkdtemp())
        output_dir = tmpdir / "out"
        (tmpdir / "src").mkdir()
        (tmpdir / "src" / "sample.py").write_text("print('ok')\n", encoding="utf-8")

        private_key = Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        private_key_path = tmpdir / "signing-private.pem"
        public_key_path = tmpdir / "signing-public.pem"
        private_key_path.write_bytes(private_pem)
        public_key_path.write_bytes(public_pem)

        summary = module.generate(tmpdir, output_dir, signing_key=private_key_path)
        self.assertEqual(summary["manifest_signature"], "MANIFEST.sha256.sig")

        module.verify_manifest_signature(
            output_dir / "MANIFEST.sha256",
            output_dir / "MANIFEST.sha256.sig",
            public_key_path,
        )

    def test_generate_release_artifacts_is_bit_reproducible(self):
        module = load_release_script()
        tmpdir = Path(tempfile.mkdtemp())
        (tmpdir / "src" / "phasmid").mkdir(parents=True)
        (tmpdir / "src" / "phasmid" / "example.py").write_text(
            "print('ok')\n",
            encoding="utf-8",
        )
        (tmpdir / "README.md").write_text("phasmid\n", encoding="utf-8")
        (tmpdir / "pyproject.toml").write_text(
            '[project]\ndependencies = [\n    "cryptography==46.0.7",\n]\n',
            encoding="utf-8",
        )

        out1 = Path(tempfile.mkdtemp()) / "out1"
        out2 = Path(tempfile.mkdtemp()) / "out2"
        module.generate(tmpdir, out1, archive=True, source_date_epoch=1700000000)
        module.generate(tmpdir, out2, archive=True, source_date_epoch=1700000000)

        files = [
            "MANIFEST.sha256",
            "sbom.cyclonedx.json",
            "release-summary.json",
            "phasmid-release.tar.gz",
        ]
        for name in files:
            self.assertEqual(
                self._sha256_file(out1 / name),
                self._sha256_file(out2 / name),
                msg=f"non-reproducible artifact: {name}",
            )


if __name__ == "__main__":
    unittest.main()
