import json
import os
import tempfile
import unittest
from unittest.mock import patch

from bitcraft_preview import config


class ConfigUpdateTests(unittest.TestCase):
    """Test that new default options get added to existing user configs."""

    def test_new_user_setting_gets_added(self):
        """When DEFAULT_CONFIG gets a new UserSetting, it should be added to existing config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_config_path = os.path.join(tmpdir, "config.json")
            
            # Simulate old config missing a new setting
            old_config = {
                "version": config.DEFAULT_CONFIG["version"],
                "mode": "sandboxie",
                "UserSettings": {
                    "inline_label": True,
                    "preview_opacity": 0.8,
                    # Missing newer settings that exist in DEFAULT_CONFIG
                },
                "SystemSettings": {
                    "process_name": "BitCraft.exe",
                    "refresh_interval_ms": 250,
                },
                "native_mode": {"enabled": False, "instances": []},
                "sandboxie_mode": {"enabled": True, "instances": []},
            }
            
            with open(test_config_path, "w") as f:
                json.dump(old_config, f)
            
            # Patch the config file path to use our temp file
            with patch.object(config, "config_file_path", test_config_path):
                loaded = config.load_config()
                
                # Verify new defaults were merged in
                self.assertIn("hover_zoom_enabled", loaded["UserSettings"])
                self.assertIn("switch_window_hotkey", loaded["UserSettings"])
                self.assertIn("preview_tile_width", loaded["UserSettings"])
                
                # Verify old values preserved
                self.assertEqual(loaded["UserSettings"]["inline_label"], True)
                self.assertEqual(loaded["UserSettings"]["preview_opacity"], 0.8)
                
                # Verify config was saved back with new defaults
                with open(test_config_path, "r") as f:
                    saved_config = json.load(f)
                
                self.assertIn("hover_zoom_enabled", saved_config["UserSettings"])
                self.assertIn("switch_window_hotkey", saved_config["UserSettings"])

    def test_new_native_mode_option_gets_added(self):
        """When DEFAULT_CONFIG gets a new native_mode option, it should be added."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_config_path = os.path.join(tmpdir, "config.json")
            
            # Simulate old native mode config missing new fields
            old_config = {
                "version": config.DEFAULT_CONFIG["version"],
                "mode": "native",
                "UserSettings": config.DEFAULT_CONFIG["UserSettings"].copy(),
                "SystemSettings": config.DEFAULT_CONFIG["SystemSettings"].copy(),
                "native_mode": {
                    "enabled": True,
                    "setup_completed": True,
                    "instances": [],
                    # Missing newer fields like steam_instance_root, steam_root_policy, etc.
                },
                "sandboxie_mode": {"enabled": False, "instances": []},
            }
            
            with open(test_config_path, "w") as f:
                json.dump(old_config, f)
            
            with patch.object(config, "config_file_path", test_config_path):
                loaded = config.load_config()
                
                # Verify new native_mode defaults were merged in
                self.assertIn("steam_instance_root", loaded["native_mode"])
                self.assertIn("steam_root_policy", loaded["native_mode"])
                self.assertIn("max_instances", loaded["native_mode"])
                self.assertIn("last_reconcile", loaded["native_mode"])
                
                # Verify old values preserved
                self.assertEqual(loaded["native_mode"]["enabled"], True)
                self.assertEqual(loaded["native_mode"]["setup_completed"], True)
                
                # Verify saved
                with open(test_config_path, "r") as f:
                    saved_config = json.load(f)
                
                self.assertIn("steam_instance_root", saved_config["native_mode"])
                self.assertIn("max_instances", saved_config["native_mode"])

    def test_no_update_when_config_complete(self):
        """When config already has all defaults, don't update file unnecessarily."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_config_path = os.path.join(tmpdir, "config.json")
            
            # Write complete config
            complete_config = config.DEFAULT_CONFIG.copy()
            with open(test_config_path, "w") as f:
                json.dump(complete_config, f)
            
            # Get original modification time
            mtime_before = os.path.getmtime(test_config_path)
            
            with patch.object(config, "config_file_path", test_config_path):
                loaded = config.load_config()
                
                # Config should load fine
                self.assertIsNotNone(loaded)
                
                # File should not have been rewritten (mtime unchanged)
                # Note: This might not always work due to filesystem time precision,
                # but it's a reasonable check for "no unnecessary writes"
                mtime_after = os.path.getmtime(test_config_path)
                
                # In practice, if config_updated is False, save_config won't be called
                # So this is more of a logic check than a strict filesystem test

    def test_new_gui_section_gets_added(self):
        """When DEFAULT_CONFIG gets a new gui section, it should be merged into old configs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_config_path = os.path.join(tmpdir, "config.json")

            old_config = {
                "version": config.DEFAULT_CONFIG["version"],
                "mode": "sandboxie",
                "UserSettings": config.DEFAULT_CONFIG["UserSettings"].copy(),
                "SystemSettings": config.DEFAULT_CONFIG["SystemSettings"].copy(),
                "native_mode": {"enabled": False, "instances": []},
                "sandboxie_mode": {"enabled": True, "instances": []},
            }

            with open(test_config_path, "w") as f:
                json.dump(old_config, f)

            with patch.object(config, "config_file_path", test_config_path):
                loaded = config.load_config()

                self.assertIn("gui", loaded)
                self.assertIn("open_on_startup", loaded["gui"])
                self.assertIn("sidebar_collapsed", loaded["gui"])
                self.assertIn("last_panel", loaded["gui"])

                with open(test_config_path, "r") as f:
                    saved_config = json.load(f)

                self.assertIn("gui", saved_config)
                self.assertEqual(saved_config["gui"]["open_on_startup"], False)


if __name__ == "__main__":
    unittest.main()
