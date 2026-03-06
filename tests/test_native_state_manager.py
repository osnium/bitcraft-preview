import os
import tempfile
import unittest
from unittest.mock import patch

from bitcraft_preview import config
from bitcraft_preview.native.state_manager import NativeModeStateManager


class NativeStateManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        self._old_config_path = config.config_file_path
        config.config_file_path = os.path.join(self._tmp_dir.name, "config.json")

    def tearDown(self) -> None:
        config.config_file_path = self._old_config_path
        self._tmp_dir.cleanup()

    def test_load_config_adds_native_defaults(self) -> None:
        manager = NativeModeStateManager()
        cfg = manager.load_config()

        self.assertIn("native_mode", cfg)
        self.assertIn("sandboxie_mode", cfg)
        self.assertEqual(cfg["mode"], "sandboxie")
        self.assertEqual(cfg["native_mode"]["steam_instance_root"], r"C:\BitcraftPreview\SteamInstances")

    def test_upsert_and_decrypt_password_roundtrip(self) -> None:
        manager = NativeModeStateManager()

        with patch("bitcraft_preview.native.state_manager.protect_text", return_value="ENC123") as protect:
            instance = manager.upsert_instance(
                instance_id="steam1",
                local_username="bitcraft1",
                plain_password="secret-pass",
                steam_exe_path=r"C:\BitcraftPreview\SteamInstances\Steam1\steam.exe",
                instance_root=r"C:\BitcraftPreview\SteamInstances\Steam1",
                steamapps_link_path=r"C:\BitcraftPreview\SteamInstances\Steam1\steamapps",
                steamapps_link_target=r"D:\SteamLibrary\steamapps",
            )

        protect.assert_called_once()
        self.assertEqual(instance.instance_id, "steam1")

        with patch("bitcraft_preview.native.state_manager.unprotect_text", return_value="secret-pass") as unprotect:
            plain = manager.get_plain_password("steam1")

        self.assertEqual(plain, "secret-pass")
        unprotect.assert_called_once_with("ENC123")

    def test_get_instance_by_username(self) -> None:
        manager = NativeModeStateManager()
        with patch("bitcraft_preview.native.state_manager.protect_text", return_value="ENC"):
            manager.upsert_instance(
                instance_id="steam2",
                local_username="bitcraft2",
                plain_password="pw",
                steam_exe_path=r"C:\BitcraftPreview\SteamInstances\Steam2\steam.exe",
            )

        by_id = manager.get_instance("steam2")
        by_user = manager.get_instance_by_username("BITCRAFT2")
        self.assertIsNotNone(by_id)
        self.assertIsNotNone(by_user)
        self.assertEqual(by_id.instance_id, "steam2")
        self.assertEqual(by_user.local_username, "bitcraft2")

    def test_remove_instance(self) -> None:
        manager = NativeModeStateManager()
        with patch("bitcraft_preview.native.state_manager.protect_text", return_value="ENC"):
            manager.upsert_instance(
                instance_id="steam3",
                local_username="bitcraft3",
                plain_password="pw",
                steam_exe_path=r"C:\BitcraftPreview\SteamInstances\Steam3\steam.exe",
            )

        removed = manager.remove_instance("steam3")
        missing = manager.get_instance("steam3")

        self.assertTrue(removed)
        self.assertIsNone(missing)


if __name__ == "__main__":
    unittest.main()
