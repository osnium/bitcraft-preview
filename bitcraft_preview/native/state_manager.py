from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any

from bitcraft_preview import config

from .dpapi import protect_text, unprotect_text


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class ReconcileSummary:
    run_at: str = ""
    users_reused: int = 0
    users_created: int = 0
    folders_reused: int = 0
    folders_created: int = 0
    folders_repaired: int = 0


@dataclass
class NativeInstance:
    instance_id: str
    local_username: str
    local_user_sid: str = ""
    managed_by_app: bool = True
    managed_created_at: str = field(default_factory=_utc_now_iso)
    password_encrypted: str = ""
    password_decryption_key: str = "DPAPI"
    steam_account_name: str = ""
    entity_id: str = ""
    overlay_nickname: str = ""
    instance_root: str = ""
    steam_exe_path: str = ""
    steamapps_link_path: str = ""
    steamapps_link_target: str = ""
    status: str = "provisioning"


class NativeModeStateManager:
    """Load and persist Native Mode state inside unified config.json."""

    SCHEMA_VERSION = "2.1"

    def __init__(self, machine_scope_passwords: bool = True) -> None:
        self._machine_scope_passwords = machine_scope_passwords

    def load_config(self) -> dict[str, Any]:
        cfg = config.load_config()

        if "version" not in cfg:
            cfg["version"] = self.SCHEMA_VERSION
        if "mode" not in cfg:
            cfg["mode"] = "sandboxie"

        native = cfg.setdefault("native_mode", {})
        native.setdefault("enabled", False)
        native.setdefault("setup_completed", False)
        native.setdefault("setup_date", "")
        native.setdefault("max_instances", 8)
        native.setdefault("steam_instance_root", r"C:\BitcraftPreview\SteamInstances")
        native.setdefault("steam_root_policy", "central_root")
        native.setdefault("instances", [])
        native.setdefault("last_reconcile", asdict(ReconcileSummary()))

        sandboxie = cfg.setdefault("sandboxie_mode", {})
        sandboxie.setdefault("enabled", True)
        sandboxie.setdefault("instances", [])

        return cfg

    def save_config(self, cfg: dict[str, Any]) -> None:
        config.save_config(cfg)

    def get_mode(self) -> str:
        cfg = self.load_config()
        mode = str(cfg.get("mode", "sandboxie")).strip().lower()
        return mode if mode in {"native", "sandboxie"} else "sandboxie"

    def set_mode(self, mode: str) -> None:
        normalized = mode.strip().lower()
        if normalized not in {"native", "sandboxie"}:
            raise ValueError(f"Unsupported mode: {mode}")
        cfg = self.load_config()
        cfg["mode"] = normalized
        self.save_config(cfg)

    def list_instances(self) -> list[NativeInstance]:
        cfg = self.load_config()
        raw_instances = cfg["native_mode"].get("instances", [])
        instances: list[NativeInstance] = []
        field_names = set(NativeInstance.__dataclass_fields__.keys())
        for item in raw_instances:
            if not isinstance(item, dict):
                continue
            payload = dict(item)
            payload.setdefault("instance_id", f"steam{len(instances) + 1}")
            payload.setdefault("local_username", "")
            normalized = {k: payload.get(k) for k in field_names if k in payload}
            instances.append(NativeInstance(**normalized))
        return instances

    def get_instance(self, instance_id: str) -> NativeInstance | None:
        for instance in self.list_instances():
            if instance.instance_id == instance_id:
                return instance
        return None

    def get_instance_by_username(self, local_username: str) -> NativeInstance | None:
        target = local_username.strip().lower()
        for instance in self.list_instances():
            if instance.local_username.strip().lower() == target:
                return instance
        return None

    def upsert_instance(
        self,
        *,
        instance_id: str,
        local_username: str,
        plain_password: str | None = None,
        steam_account_name: str = "",
        entity_id: str = "",
        overlay_nickname: str = "",
        local_user_sid: str = "",
        instance_root: str = "",
        steam_exe_path: str = "",
        steamapps_link_path: str = "",
        steamapps_link_target: str = "",
        status: str = "ready",
    ) -> NativeInstance:
        cfg = self.load_config()
        native = cfg["native_mode"]
        rows = native.setdefault("instances", [])

        idx = next((i for i, row in enumerate(rows) if row.get("instance_id") == instance_id), -1)
        existing = rows[idx] if idx >= 0 else {}

        password_encrypted = existing.get("password_encrypted", "")
        if plain_password is not None:
            password_encrypted = protect_text(plain_password, use_machine_scope=self._machine_scope_passwords)

        instance = NativeInstance(
            instance_id=instance_id,
            local_username=local_username,
            local_user_sid=local_user_sid or existing.get("local_user_sid", ""),
            managed_by_app=True,
            managed_created_at=existing.get("managed_created_at", _utc_now_iso()),
            password_encrypted=password_encrypted,
            password_decryption_key="DPAPI",
            steam_account_name=steam_account_name or existing.get("steam_account_name", ""),
            entity_id=entity_id or existing.get("entity_id", ""),
            overlay_nickname=overlay_nickname or existing.get("overlay_nickname", ""),
            instance_root=instance_root or existing.get("instance_root", ""),
            steam_exe_path=steam_exe_path or existing.get("steam_exe_path", ""),
            steamapps_link_path=steamapps_link_path or existing.get("steamapps_link_path", ""),
            steamapps_link_target=steamapps_link_target or existing.get("steamapps_link_target", ""),
            status=status or existing.get("status", "provisioning"),
        )

        data = asdict(instance)
        if idx >= 0:
            rows[idx] = data
        else:
            rows.append(data)

        if not native.get("setup_date"):
            native["setup_date"] = _utc_now_iso()
        native["setup_completed"] = True

        self.save_config(cfg)
        return instance

    def remove_instance(self, instance_id: str) -> bool:
        cfg = self.load_config()
        rows = cfg["native_mode"].get("instances", [])
        before = len(rows)
        rows = [row for row in rows if row.get("instance_id") != instance_id]
        cfg["native_mode"]["instances"] = rows
        removed = len(rows) != before
        if removed:
            self.save_config(cfg)
        return removed

    def get_plain_password(self, instance_id: str) -> str:
        cfg = self.load_config()
        for row in cfg["native_mode"].get("instances", []):
            if row.get("instance_id") == instance_id:
                encrypted = row.get("password_encrypted", "")
                if not encrypted:
                    raise ValueError(f"No password set for instance: {instance_id}")
                return unprotect_text(encrypted)
        raise KeyError(f"Unknown native instance: {instance_id}")

    def set_last_reconcile(self, summary: ReconcileSummary) -> None:
        cfg = self.load_config()
        cfg["native_mode"]["last_reconcile"] = asdict(summary)
        self.save_config(cfg)
