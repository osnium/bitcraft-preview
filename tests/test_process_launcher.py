import unittest
from unittest.mock import patch

from bitcraft_preview.native import process_launcher
from bitcraft_preview.native.process_launcher import ProcessLaunchError, ProcessLauncher


class _FakeAdvapiOk:
    def __init__(self, pid: int = 1234) -> None:
        self.pid = pid

    def CreateProcessWithLogonW(self, username, domain, password, logon_flags, app_name, cmd_line, creation_flags, env, cwd, startup_info, proc_info):
        # proc_info is a byref(PROCESS_INFORMATION), write into the underlying object.
        proc = proc_info._obj
        proc.dwProcessId = self.pid
        proc.hThread = 111
        proc.hProcess = 222
        return 1


class _FakeAdvapiFail:
    def CreateProcessWithLogonW(self, *args, **kwargs):
        return 0


class _FakeKernel32:
    def __init__(self) -> None:
        self.closed = []

    def CloseHandle(self, handle):
        self.closed.append(handle)
        return 1


class ProcessLauncherTests(unittest.TestCase):
    def test_launch_silent_returns_pid_and_closes_handles(self) -> None:
        launcher = ProcessLauncher()
        fake_advapi = _FakeAdvapiOk(pid=7777)
        fake_kernel = _FakeKernel32()

        with patch.object(process_launcher, "advapi32", fake_advapi), patch.object(process_launcher, "kernel32", fake_kernel):
            pid = launcher.launch_silent(
                username="bitcraft1",
                password="pw",
                exe_path=r"C:\BitcraftPreview\SteamInstances\Steam1\steam.exe",
                args="-silent",
            )

        self.assertEqual(pid, 7777)
        self.assertIn(111, fake_kernel.closed)
        self.assertIn(222, fake_kernel.closed)

    def test_launch_foreground_failure_raises(self) -> None:
        launcher = ProcessLauncher()
        fake_advapi = _FakeAdvapiFail()
        fake_kernel = _FakeKernel32()

        with patch.object(process_launcher, "advapi32", fake_advapi), patch.object(process_launcher, "kernel32", fake_kernel):
            with self.assertRaises(ProcessLaunchError):
                launcher.launch_foreground(
                    username="bitcraft1",
                    password="badpw",
                    exe_path=r"C:\BitcraftPreview\SteamInstances\Steam1\steam.exe",
                    args="",
                )


if __name__ == "__main__":
    unittest.main()
