from __future__ import annotations

import re
from dataclasses import dataclass

from .process_launcher import ProcessLauncher
from .state_manager import NativeInstance, NativeModeStateManager


APP_ID_BITCRAFT = 3454650


class NativeProcessControlError(RuntimeError):
    pass


@dataclass
class LaunchResult:
    steam_pid: int
    instance_id: str
    local_username: str


class NativeProcessController:
    """High-level launch/restart/relogin flow for Native Mode instances."""

    def __init__(self, state: NativeModeStateManager | None = None, launcher: ProcessLauncher | None = None) -> None:
        self._state = state or NativeModeStateManager()
        self._launcher = launcher or ProcessLauncher()

    def _resolve_instance(self, instance_ref: str) -> NativeInstance:
        instance = self._state.get_instance(instance_ref)
        if instance is None:
            instance = self._state.get_instance_by_username(instance_ref)
        if instance is None:
            raise NativeProcessControlError(f"Unknown native instance: {instance_ref}")
        if not instance.steam_exe_path:
            raise NativeProcessControlError(
                f"Native instance '{instance.instance_id}' has no steam_exe_path. Run setup/reconcile first."
            )
        return instance

    @staticmethod
    def _master_override_name(instance_id: str) -> str:
        match = re.search(r"(\d+)$", instance_id)
        if match:
            return f"steam{match.group(1)}"
        safe = re.sub(r"[^a-zA-Z0-9]", "", instance_id) or "steam"
        return f"steam{safe}"

    def _launch(self, instance: NativeInstance, *, relogin_mode: bool, restart_mode: bool) -> LaunchResult:
        password = self._state.get_plain_password(instance.instance_id)

        if restart_mode or relogin_mode:
            # Mandatory pre-kill before restart/relogin to avoid stale Steam/CEF state.
            self._launcher.taskkill_for_user(username=instance.local_username, password=password)

        override = self._master_override_name(instance.instance_id)
        if relogin_mode:
            args = f"-master_ipc_name_override {override}"
            steam_pid = self._launcher.launch_foreground(
                username=instance.local_username,
                password=password,
                exe_path=instance.steam_exe_path,
                args=args,
            )
        else:
            args = f"-master_ipc_name_override {override} -silent -applaunch {APP_ID_BITCRAFT}"
            steam_pid = self._launcher.launch_silent(
                username=instance.local_username,
                password=password,
                exe_path=instance.steam_exe_path,
                args=args,
            )

        return LaunchResult(
            steam_pid=steam_pid,
            instance_id=instance.instance_id,
            local_username=instance.local_username,
        )

    def launch_instance(self, instance_ref: str) -> LaunchResult:
        instance = self._resolve_instance(instance_ref)
        return self._launch(instance, relogin_mode=False, restart_mode=False)

    def restart_instance(self, instance_ref: str) -> LaunchResult:
        instance = self._resolve_instance(instance_ref)
        return self._launch(instance, relogin_mode=False, restart_mode=True)

    def relogin_instance(self, instance_ref: str) -> LaunchResult:
        instance = self._resolve_instance(instance_ref)
        return self._launch(instance, relogin_mode=True, restart_mode=True)
