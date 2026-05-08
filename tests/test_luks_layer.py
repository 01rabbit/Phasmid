import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid import config
from phasmid.luks_key_store import LuksKeyStore
from phasmid.luks_layer import LuksConfig, LuksLayer, LuksMode


class LuksConfigTests(unittest.TestCase):
    def test_config_defaults_from_env(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = LuksConfig.from_env()
        self.assertEqual(cfg.mode, LuksMode.DISABLED)
        self.assertEqual(cfg.container_path, "/opt/phasmid/luks.img")
        self.assertEqual(cfg.mount_point, "/mnt/phasmid-vault")
        self.assertEqual(cfg.iter_time_ms, 2000)

    def test_config_parses_file_mode(self):
        with mock.patch.dict(
            os.environ,
            {
                "PHASMID_LUKS_MODE": "file",
                "PHASMID_LUKS_CONTAINER": "/tmp/phasmid.img",
                "PHASMID_LUKS_MOUNT_POINT": "/tmp/mnt",
                "PHASMID_LUKS_ITER_TIME_MS": "2500",
            },
            clear=True,
        ):
            cfg = LuksConfig.from_env()
        self.assertEqual(cfg.mode, LuksMode.FILE_CONTAINER)
        self.assertEqual(cfg.container_path, "/tmp/phasmid.img")
        self.assertEqual(cfg.mount_point, "/tmp/mnt")
        self.assertEqual(cfg.iter_time_ms, 2500)


class LuksLayerTests(unittest.TestCase):
    @mock.patch("phasmid.luks_layer.shutil.which")
    def test_is_available_false_when_disabled(self, which_mock):
        layer = LuksLayer(LuksConfig(mode=LuksMode.DISABLED))
        self.assertFalse(layer.is_available())
        which_mock.assert_not_called()

    @mock.patch("phasmid.luks_layer.shutil.which", return_value=None)
    def test_is_available_false_without_cryptsetup(self, _which_mock):
        layer = LuksLayer(LuksConfig(mode=LuksMode.FILE_CONTAINER))
        self.assertFalse(layer.is_available())

    @mock.patch("phasmid.luks_layer.shutil.which", return_value="/usr/sbin/cryptsetup")
    def test_is_available_true(self, _which_mock):
        layer = LuksLayer(LuksConfig(mode=LuksMode.FILE_CONTAINER))
        self.assertTrue(layer.is_available())

    @mock.patch("phasmid.luks_layer.subprocess.run")
    @mock.patch("phasmid.luks_layer.shutil.which", return_value="/usr/sbin/cryptsetup")
    def test_status_reports_mounted(self, _which_mock, run_mock):
        run_mock.return_value = mock.Mock(returncode=0)
        layer = LuksLayer(
            LuksConfig(mode=LuksMode.FILE_CONTAINER, mount_point="/mnt/phasmid-vault")
        )
        status = layer.status()
        self.assertTrue(status.success)
        self.assertTrue(status.mounted)
        self.assertEqual(status.mount_point, "/mnt/phasmid-vault")

    @mock.patch("phasmid.luks_layer.subprocess.run")
    @mock.patch("phasmid.luks_layer.shutil.which", return_value="/usr/sbin/cryptsetup")
    def test_status_reports_unmounted(self, _which_mock, run_mock):
        run_mock.return_value = mock.Mock(returncode=1)
        layer = LuksLayer(
            LuksConfig(mode=LuksMode.FILE_CONTAINER, mount_point="/mnt/phasmid-vault")
        )
        status = layer.status()
        self.assertTrue(status.success)
        self.assertFalse(status.mounted)

    @mock.patch("phasmid.luks_layer.subprocess.run")
    def test_status_disabled(self, run_mock):
        layer = LuksLayer(LuksConfig(mode=LuksMode.DISABLED))
        status = layer.status()
        self.assertTrue(status.success)
        self.assertFalse(status.mounted)
        run_mock.assert_not_called()


class LuksKeyStoreTests(unittest.TestCase):
    def test_path_resolution(self):
        ks = LuksKeyStore("/run/phasmid")
        self.assertEqual(ks.key_path, "/run/phasmid/luks.key")

    @mock.patch("phasmid.luks_key_store.os.urandom", return_value=b"a" * 32)
    def test_generate_and_store(self, _urandom):
        m = mock.mock_open()
        with mock.patch("phasmid.luks_key_store.open", m), mock.patch(
            "phasmid.luks_key_store.os.makedirs"
        ), mock.patch("phasmid.luks_key_store.os.chmod"):
            ks = LuksKeyStore("/run/phasmid")
            key = ks.generate_and_store()
        self.assertEqual(key, b"a" * 32)
        m.assert_called_once_with("/run/phasmid/luks.key", "wb")

    @mock.patch("phasmid.luks_key_store.os.path.exists", return_value=True)
    def test_destroy(self, _exists):
        with mock.patch("phasmid.luks_key_store.open", mock.mock_open()), mock.patch(
            "phasmid.luks_key_store.os.path.getsize", return_value=16
        ), mock.patch("phasmid.luks_key_store.os.urandom", return_value=b"b" * 32), mock.patch(
            "phasmid.luks_key_store.os.remove"
        ) as remove_mock:
            ks = LuksKeyStore("/run/phasmid")
            self.assertTrue(ks.destroy())
        remove_mock.assert_called_once_with("/run/phasmid/luks.key")


class ConfigConstantsTests(unittest.TestCase):
    def test_luks_constants_present(self):
        self.assertTrue(hasattr(config, "PHASMID_LUKS_MODE"))
        self.assertTrue(hasattr(config, "PHASMID_LUKS_CONTAINER"))
        self.assertTrue(hasattr(config, "PHASMID_LUKS_MOUNT_POINT"))
        self.assertTrue(hasattr(config, "PHASMID_LUKS_ITER_TIME_MS"))


if __name__ == "__main__":
    unittest.main()
