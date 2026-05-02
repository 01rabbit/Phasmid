import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

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
    def test_manifest_and_sbom_generation_exclude_runtime_files(self):
        module = load_release_script()
        tmpdir = Path(tempfile.mkdtemp())
        output_dir = tmpdir / "out"
        (tmpdir / "src" / "phantasm").mkdir(parents=True)
        (tmpdir / "src" / "phantasm" / "example.py").write_text(
            "print('ok')\n",
            encoding="utf-8",
        )
        (tmpdir / ".state").mkdir()
        (tmpdir / ".state" / "access.bin").write_bytes(b"local")
        (tmpdir / "vault.bin").write_bytes(b"vault")
        (tmpdir / "pyproject.toml").write_text(
            '[project]\ndependencies = [\n    "cryptography==46.0.4",\n]\n',
            encoding="utf-8",
        )

        summary = module.generate(tmpdir, output_dir, archive=True)

        manifest = (output_dir / "MANIFEST.sha256").read_text(encoding="utf-8")
        self.assertIn("src/phantasm/example.py", manifest)
        self.assertNotIn(".state/access.bin", manifest)
        self.assertNotIn("vault.bin", manifest)
        self.assertEqual(summary["archive"], "phantasm-release.tar.gz")

        sbom = json.loads(
            (output_dir / "sbom.cyclonedx.json").read_text(encoding="utf-8")
        )
        self.assertEqual(sbom["bomFormat"], "CycloneDX")
        self.assertEqual(sbom["components"][0]["name"], "cryptography")

    def test_dependency_parser_handles_unpinned_values(self):
        module = load_release_script()
        tmpdir = Path(tempfile.mkdtemp())
        pyproject = tmpdir / "pyproject.toml"
        pyproject.write_text(
            '[project]\ndependencies = [\n    "fastapi",\n]\n',
            encoding="utf-8",
        )

        self.assertEqual(module.read_project_dependencies(pyproject), ["fastapi"])


if __name__ == "__main__":
    unittest.main()
