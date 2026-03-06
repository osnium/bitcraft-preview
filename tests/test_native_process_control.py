import unittest
from unittest.mock import patch

from bitcraft_preview.native.process_control import NativeProcessController
from bitcraft_preview.native.state_manager import NativeInstance


class _FakeState:
    def __init__(self) -> None:
        self.instance = NativeInstance(
            instance_id="steam1",
            local_username="bitcraft1",
            steam_exe_path=r"C:\BitcraftPreview\SteamInstances\Steam1\steam.exe",
            status="ready",
        )

    def get_instance(self, instance_id: str):
        return self.instance if instance_id.lower() == "steam1" else None

    def get_instance_by_username(self, username: str):
        return self.instance if username.lower() == "bitcraft1" else None

    def get_plain_password(self, instance_id: str):
        return "pw"


class _Proc:
    def __init__(self, name: str, username: str):
        self.info = {"name": name, "username": username}


class NativeProcessControlTests(unittest.TestCase):
    def test_is_instance_running_true_for_matching_user_and_process_name(self) -> None:
        controller = NativeProcessController(state=_FakeState())
        procs = [
            _Proc("explorer.exe", "MACHINE\\user"),
            _Proc("BitCraft.exe", "MACHINE\\bitcraft1"),
        ]

        with patch("bitcraft_preview.native.process_control.psutil.process_iter", return_value=procs):
            self.assertTrue(controller.is_instance_running("steam1"))

    def test_is_instance_running_false_for_other_user(self) -> None:
        controller = NativeProcessController(state=_FakeState())
        procs = [
            _Proc("steam.exe", "MACHINE\\bitcraft2"),
        ]

        with patch("bitcraft_preview.native.process_control.psutil.process_iter", return_value=procs):
            self.assertFalse(controller.is_instance_running("steam1"))


if __name__ == "__main__":
    unittest.main()
