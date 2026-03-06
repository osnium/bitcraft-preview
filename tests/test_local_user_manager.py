import subprocess
import unittest
from unittest.mock import patch

from bitcraft_preview.native.local_user_manager import LocalUserError, LocalUserManager


def _cp(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class LocalUserManagerTests(unittest.TestCase):
    def test_user_exists_true(self) -> None:
        mgr = LocalUserManager()
        with patch("bitcraft_preview.native.local_user_manager._run_command", return_value=_cp(0)):
            self.assertTrue(mgr.user_exists("bitcraft1"))

    def test_user_exists_false(self) -> None:
        mgr = LocalUserManager()
        with patch("bitcraft_preview.native.local_user_manager._run_command", return_value=_cp(2)):
            self.assertFalse(mgr.user_exists("missing"))

    def test_create_user_raises_if_exists(self) -> None:
        mgr = LocalUserManager()
        with patch.object(mgr, "user_exists", return_value=True):
            with self.assertRaises(LocalUserError):
                mgr.create_user("bitcraft1", "pw")

    def test_create_user_success_returns_password(self) -> None:
        mgr = LocalUserManager()
        with patch.object(mgr, "user_exists", return_value=False), patch(
            "bitcraft_preview.native.local_user_manager._run_command",
            side_effect=[_cp(0), _cp(0)],
        ):
            result = mgr.create_user("bitcraft1", "pw")
        self.assertEqual(result, "pw")

    def test_create_user_failure_raises(self) -> None:
        mgr = LocalUserManager()
        with patch.object(mgr, "user_exists", return_value=False), patch(
            "bitcraft_preview.native.local_user_manager._run_command",
            return_value=_cp(1, stderr="access denied"),
        ):
            with self.assertRaises(LocalUserError):
                mgr.create_user("bitcraft1", "pw")

    def test_get_user_sid(self) -> None:
        mgr = LocalUserManager()
        with patch.object(mgr, "user_exists", return_value=True), patch(
            "bitcraft_preview.native.local_user_manager._lookup_account_sid", return_value="S-1-5-21-123"
        ):
            sid = mgr.get_user_sid("bitcraft1")
        self.assertEqual(sid, "S-1-5-21-123")

    def test_ensure_user_created(self) -> None:
        mgr = LocalUserManager()
        with patch.object(mgr, "user_exists", return_value=False), patch.object(
            mgr, "create_user", return_value="newpw"
        ):
            created, password = mgr.ensure_user("bitcraft5")
        self.assertTrue(created)
        self.assertEqual(password, "newpw")

    def test_generate_password_length(self) -> None:
        password = LocalUserManager.generate_password(30)
        self.assertEqual(len(password), 30)


if __name__ == "__main__":
    unittest.main()
