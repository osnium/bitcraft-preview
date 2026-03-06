from __future__ import annotations

import ctypes
import os
import secrets
import shutil
import string
import subprocess
from ctypes import wintypes


class LocalUserError(RuntimeError):
    pass


advapi32 = ctypes.windll.advapi32
kernel32 = ctypes.windll.kernel32


def _run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, capture_output=True, text=True)


def _generate_password(length: int = 24) -> str:
    # Keep password parser-friendly for net.exe while still satisfying common complexity rules.
    base = "Aa1!"
    if length <= len(base):
        return base[:length]
    alphabet = string.ascii_letters + string.digits
    return base + "".join(secrets.choice(alphabet) for _ in range(length - len(base)))


def _create_user_with_powershell(username: str, password: str) -> subprocess.CompletedProcess[str]:
    escaped_user = username.replace("'", "''")
    escaped_password = password.replace("'", "''")
    command = (
        f"$pw = ConvertTo-SecureString '{escaped_password}' -AsPlainText -Force; "
        f"New-LocalUser -Name '{escaped_user}' -Password $pw -PasswordNeverExpires:$true -AccountNeverExpires:$true; "
        f"Add-LocalGroupMember -Group 'Users' -Member '{escaped_user}'"
    )
    return _run_command(["powershell", "-NoProfile", "-NonInteractive", "-Command", command])


def _lookup_account_sid(account_name: str) -> str:
    name = account_name

    sid_size = wintypes.DWORD(0)
    domain_size = wintypes.DWORD(0)
    sid_use = wintypes.DWORD(0)

    advapi32.LookupAccountNameW(
        None,
        name,
        None,
        ctypes.byref(sid_size),
        None,
        ctypes.byref(domain_size),
        ctypes.byref(sid_use),
    )

    if sid_size.value == 0:
        raise LocalUserError(f"Could not resolve SID size for account: {account_name}")

    sid_buffer = ctypes.create_string_buffer(sid_size.value)
    domain_buffer = ctypes.create_unicode_buffer(domain_size.value + 1)

    ok = advapi32.LookupAccountNameW(
        None,
        name,
        sid_buffer,
        ctypes.byref(sid_size),
        domain_buffer,
        ctypes.byref(domain_size),
        ctypes.byref(sid_use),
    )
    if not ok:
        raise ctypes.WinError()

    sid_str = wintypes.LPWSTR()
    ok = advapi32.ConvertSidToStringSidW(sid_buffer, ctypes.byref(sid_str))
    if not ok:
        raise ctypes.WinError()

    try:
        return sid_str.value
    finally:
        kernel32.LocalFree(sid_str)


class LocalUserManager:
    """Admin-required local user lifecycle helper for Native Mode setup."""

    def user_exists(self, username: str) -> bool:
        result = _run_command(["net", "user", username])
        return result.returncode == 0

    def get_user_sid(self, username: str) -> str:
        if not self.user_exists(username):
            raise LocalUserError(f"User does not exist: {username}")
        return _lookup_account_sid(username)

    def create_user(self, username: str, password: str | None = None) -> str:
        if self.user_exists(username):
            raise LocalUserError(f"User already exists: {username}")

        final_password = password or _generate_password()
        result = _run_command(["net", "user", username, final_password, "/add"])
        if result.returncode != 0:
            # Some environments return "No valid response was provided." from net.exe.
            fallback = _create_user_with_powershell(username, final_password)
            if fallback.returncode == 0:
                return final_password

            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            detail = stderr or stdout or f"exit code {result.returncode}"
            fb_stderr = (fallback.stderr or "").strip()
            fb_stdout = (fallback.stdout or "").strip()
            if fb_stderr or fb_stdout:
                detail = f"{detail}; PowerShell fallback: {fb_stderr or fb_stdout}"
            raise LocalUserError(f"Failed to create user {username}: {detail}")

        # Ensure the account is a standard local user.
        _run_command(["net", "localgroup", "Users", username, "/add"])

        return final_password

    def delete_user(self, username: str) -> None:
        if not self.user_exists(username):
            return

        result = _run_command(["net", "user", username, "/delete"])
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            detail = stderr or stdout or f"exit code {result.returncode}"
            raise LocalUserError(f"Failed to delete user {username}: {detail}")

        # Delete user profile folder if it exists.
        # Windows does not automatically remove C:\Users\username when deleting the account.
        profile_path = os.path.join(r"C:\Users", username)
        if os.path.isdir(profile_path):
            try:
                shutil.rmtree(profile_path)
            except Exception:
                # Profile deletion is best-effort; don't fail cleanup if it's locked.
                pass

    def ensure_user(self, username: str, password: str | None = None) -> tuple[bool, str]:
        """Return (created, password)."""
        if self.user_exists(username):
            return False, password or ""
        created_password = self.create_user(username, password)
        return True, created_password

    @staticmethod
    def generate_password(length: int = 24) -> str:
        return _generate_password(length)
