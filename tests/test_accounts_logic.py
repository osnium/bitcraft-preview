import unittest

from bitcraft_preview.native.state_manager import NativeInstance
from bitcraft_preview.ui.shell.accounts import (
    AccountsSelectionController,
    build_instance_update_payload,
    resolve_account_display_name,
    resolve_bulk_launch_targets,
)


class AccountsLogicTests(unittest.TestCase):
    def test_ctrl_click_toggles_selection(self) -> None:
        controller = AccountsSelectionController()

        self.assertEqual(controller.click("steam1", ctrl_pressed=True), {"steam1"})
        self.assertEqual(controller.click("steam2", ctrl_pressed=True), {"steam1", "steam2"})
        self.assertEqual(controller.click("steam1", ctrl_pressed=True), {"steam2"})

    def test_plain_click_replaces_selection(self) -> None:
        controller = AccountsSelectionController()
        controller.click("steam1", ctrl_pressed=True)
        controller.click("steam2", ctrl_pressed=True)

        self.assertEqual(controller.click("steam3", ctrl_pressed=False), {"steam3"})
        self.assertEqual(controller.clear(), set())

    def test_bulk_launch_targets_use_selection_when_present(self) -> None:
        all_ids = ["steam1", "steam2", "steam3"]

        self.assertEqual(resolve_bulk_launch_targets(all_ids, set()), all_ids)
        self.assertEqual(resolve_bulk_launch_targets(all_ids, {"steam2"}), all_ids)
        self.assertEqual(resolve_bulk_launch_targets(all_ids, {"steam2", "steam3"}), ["steam2", "steam3"])

    def test_display_name_falls_back_to_instance_id(self) -> None:
        instance = NativeInstance(instance_id="steam4", local_username="bitcraft4", overlay_nickname="")
        self.assertEqual(resolve_account_display_name(instance), "steam4")

        instance.overlay_nickname = "Main"
        self.assertEqual(resolve_account_display_name(instance), "Main")

    def test_update_payload_preserves_existing_instance_fields(self) -> None:
        instance = NativeInstance(
            instance_id="steam2",
            local_username="bitcraft2",
            local_user_sid="S-1-5-21-test",
            steam_account_name="test-account",
            entity_id="old-entity",
            overlay_nickname="Old Name",
            instance_root=r"C:\BitcraftPreview\SteamInstances\Steam2",
            steam_exe_path=r"C:\BitcraftPreview\SteamInstances\Steam2\steam.exe",
            steamapps_link_path=r"C:\BitcraftPreview\SteamInstances\Steam2\steamapps",
            steamapps_link_target=r"D:\SteamLibrary\steamapps",
            status="ready",
        )

        payload = build_instance_update_payload(instance, "New Name", "new-entity")

        self.assertEqual(payload["instance_id"], "steam2")
        self.assertEqual(payload["local_username"], "bitcraft2")
        self.assertIsNone(payload["plain_password"])
        self.assertEqual(payload["overlay_nickname"], "New Name")
        self.assertEqual(payload["entity_id"], "new-entity")
        self.assertEqual(payload["steam_exe_path"], instance.steam_exe_path)
        self.assertEqual(payload["steamapps_link_target"], instance.steamapps_link_target)
        self.assertEqual(payload["status"], "ready")


if __name__ == "__main__":
    unittest.main()
