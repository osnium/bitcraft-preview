import os
import json
import logging
import copy
import sys

from bitcraft_preview.version import get_app_version

logger = logging.getLogger("bitcraft_preview")
APP_VERSION = get_app_version()

# Default values
DEFAULT_CONFIG = {
    "version": APP_VERSION,
    "mode": "sandboxie",
    "UserSettings": {
        "inline_label": True,                 # Needs Restart
        "overlay_enabled": True,              # Live
        "lock_overlay_tiles": False,         # Live
        "preview_opacity": 0.8,               # Live
        "hover_zoom_enabled": True,           # Live
        "hover_zoom_percent": 200,            # Live (100-500)
        "hide_active_window_overlay": False,  # Live
        "show_overlay_only_when_focused": False,  # Live
        "save_overlay_position_per_account": True,  # Live
        "switch_window_enabled": True,        # Live
        "switch_window_hotkey": "MOUSE5",    # Live
        "preview_tile_width": 300,            # Live
        "preview_tile_height": 200            # Live
    },
    "SystemSettings": {
        "warning": "Do not change these unless you know what you are doing!",
        "process_name": "BitCraft.exe",
        "refresh_interval_ms": 250,          # Needs Restart
        "log_dir_name": "BitCraftPreview",
        "log_file_name": "bitcraft_preview.log",
        "debug": False                        # Needs Restart
    },
    "native_mode": {
        "enabled": False,
        "setup_completed": False,
        "setup_date": "",
        "max_instances": 8,
        "steam_instance_root": r"C:\BitcraftPreview\SteamInstances",
        "steam_root_policy": "central_root",
        "instances": [],
        "last_reconcile": {
            "run_at": "",
            "users_reused": 0,
            "users_created": 0,
            "folders_reused": 0,
            "folders_created": 0,
            "folders_repaired": 0,
        },
    },
    "sandboxie_mode": {
        "enabled": True,
        "instances": [],
    },
    "gui": {
        "open_on_startup": True,
        "sidebar_collapsed": False,
        "last_panel": "settings",
    },
}

def _resolve_config_file_path() -> str:
    # In packaged builds, store config in LOCALAPPDATA to survive rebuilds/reinstalls.
    if getattr(sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if not local_app_data:
            # Fallback: next to executable if LOCALAPPDATA unavailable (unlikely).
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.join(local_app_data, "BitCraftPreview")
    else:
        # In dev, keep config at repository/workspace root.
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_dir, "config.json")


config_file_path = _resolve_config_file_path()


def get_config_file_path() -> str:
    return config_file_path

def load_config():
    merged_config = copy.deepcopy(DEFAULT_CONFIG)
    config_updated = False  # Track if we added new defaults
    
    if os.path.exists(config_file_path):
        try:
            with open(config_file_path, "r") as f:
                user_config = json.load(f)

                # Preserve any custom top-level keys, then apply default sections.
                if isinstance(user_config, dict):
                    merged_config = copy.deepcopy(user_config)

                if "UserSettings" not in merged_config or not isinstance(merged_config["UserSettings"], dict):
                    merged_config["UserSettings"] = {}
                    config_updated = True
                if "SystemSettings" not in merged_config or not isinstance(merged_config["SystemSettings"], dict):
                    merged_config["SystemSettings"] = {}
                    config_updated = True

                if "native_mode" not in merged_config or not isinstance(merged_config["native_mode"], dict):
                    merged_config["native_mode"] = {}
                    config_updated = True
                if "sandboxie_mode" not in merged_config or not isinstance(merged_config["sandboxie_mode"], dict):
                    merged_config["sandboxie_mode"] = {}
                    config_updated = True
                if "gui" not in merged_config or not isinstance(merged_config["gui"], dict):
                    merged_config["gui"] = {}
                    config_updated = True

                # Merge known sections while retaining unknown fields from disk.
                default_user = DEFAULT_CONFIG["UserSettings"]
                default_system = DEFAULT_CONFIG["SystemSettings"]
                default_native = DEFAULT_CONFIG["native_mode"]
                default_sandboxie = DEFAULT_CONFIG["sandboxie_mode"]
                default_gui = DEFAULT_CONFIG["gui"]

                merged_user = copy.deepcopy(default_user)
                user_settings_before = len(merged_config["UserSettings"])
                merged_user.update(merged_config["UserSettings"])
                if len(merged_user) > user_settings_before:
                    config_updated = True
                merged_config["UserSettings"] = merged_user

                merged_system = copy.deepcopy(default_system)
                system_settings_before = len(merged_config["SystemSettings"])
                merged_system.update(merged_config["SystemSettings"])
                if len(merged_system) > system_settings_before:
                    config_updated = True
                merged_config["SystemSettings"] = merged_system

                merged_native = copy.deepcopy(default_native)
                native_keys_before = set(merged_config["native_mode"].keys())
                merged_native.update(merged_config["native_mode"])
                if not isinstance(merged_native.get("last_reconcile"), dict):
                    merged_native["last_reconcile"] = {}
                reconcile = copy.deepcopy(default_native["last_reconcile"])
                reconcile_keys_before = len(merged_native.get("last_reconcile", {}))
                reconcile.update(merged_native["last_reconcile"])
                if len(reconcile) > reconcile_keys_before:
                    config_updated = True
                merged_native["last_reconcile"] = reconcile
                if set(merged_native.keys()) > native_keys_before:
                    config_updated = True
                merged_config["native_mode"] = merged_native

                merged_sandboxie = copy.deepcopy(default_sandboxie)
                sandboxie_keys_before = len(merged_config["sandboxie_mode"])
                merged_sandboxie.update(merged_config["sandboxie_mode"])
                if len(merged_sandboxie) > sandboxie_keys_before:
                    config_updated = True
                merged_config["sandboxie_mode"] = merged_sandboxie

                merged_gui = copy.deepcopy(default_gui)
                gui_keys_before = len(merged_config["gui"])
                merged_gui.update(merged_config["gui"])
                if len(merged_gui) > gui_keys_before:
                    config_updated = True
                merged_config["gui"] = merged_gui

                if merged_config.get("version") != APP_VERSION:
                    merged_config["version"] = APP_VERSION
                    config_updated = True
                if "mode" not in merged_config:
                    merged_config["mode"] = DEFAULT_CONFIG["mode"]
                    config_updated = True
                    
                # Persist merged config back to disk if new defaults were added.
                # This ensures users get new features/options automatically on upgrade.
                if config_updated:
                    logger.info("Config file updated with new default options")
                    save_config(merged_config)
        except Exception as e:
            logger.error(f"Error reading config file '{config_file_path}': {e}")
    else:
        # Create default config file if it doesn't exist
        save_config(merged_config)
    
    # Clamp zoom percentage
    zoom = merged_config["UserSettings"]["hover_zoom_percent"]
    merged_config["UserSettings"]["hover_zoom_percent"] = max(100, min(500, zoom))
    
    return merged_config

def save_config(config):
    try:
        os.makedirs(os.path.dirname(config_file_path), exist_ok=True)
        with open(config_file_path, "w") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logger.error(f"Error writing config file '{config_file_path}': {e}")


def ensure_config_exists() -> bool:
    if os.path.exists(config_file_path):
        return True

    save_config(copy.deepcopy(DEFAULT_CONFIG))
    return os.path.exists(config_file_path)

_current_config = load_config()

# Expose constants for backward compatibility (some will be static per run)
PROCESS_NAME = _current_config["SystemSettings"]["process_name"]
REFRESH_INTERVAL_MS = _current_config["SystemSettings"]["refresh_interval_ms"]
LOG_DIR_NAME = _current_config["SystemSettings"]["log_dir_name"]
LOG_FILE_NAME = _current_config["SystemSettings"]["log_file_name"]
DEBUG = _current_config["SystemSettings"]["debug"]
INLINE_LABEL = _current_config["UserSettings"]["inline_label"]

# Real-time getters for settings that should be checked actively
def get_preview_opacity(): return load_config()["UserSettings"]["preview_opacity"]
def get_overlay_enabled(): return bool(load_config()["UserSettings"].get("overlay_enabled", True))
def get_lock_overlay_tiles(): return bool(load_config()["UserSettings"].get("lock_overlay_tiles", False))
def get_hover_zoom_enabled(): return load_config()["UserSettings"]["hover_zoom_enabled"]
def get_hover_zoom_percent(): return load_config()["UserSettings"]["hover_zoom_percent"]
def get_hide_active_window_overlay(): return load_config()["UserSettings"]["hide_active_window_overlay"]
def get_show_overlay_only_when_focused():
    return bool(load_config()["UserSettings"].get("show_overlay_only_when_focused", False))
def get_save_overlay_position_per_account():
    return bool(load_config()["UserSettings"].get("save_overlay_position_per_account", True))
def get_switch_window_enabled():
    value = load_config()["UserSettings"].get("switch_window_enabled", True)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)

def get_switch_window_hotkey(): return str(load_config()["UserSettings"].get("switch_window_hotkey", "MOUSE5"))
def get_preview_tile_width(): return max(100, int(load_config()["UserSettings"]["preview_tile_width"]))
def get_preview_tile_height(): return max(60, int(load_config()["UserSettings"]["preview_tile_height"]))


def get_current_mode() -> str:
    mode = str(load_config().get("mode", "sandboxie")).strip().lower()
    return mode if mode in {"native", "sandboxie"} else "sandboxie"


def get_gui_settings() -> dict:
    gui = load_config().get("gui", {})
    defaults = DEFAULT_CONFIG["gui"]
    return {
        "open_on_startup": bool(gui.get("open_on_startup", defaults["open_on_startup"])),
        "sidebar_collapsed": bool(gui.get("sidebar_collapsed", defaults["sidebar_collapsed"])),
        "last_panel": str(gui.get("last_panel", defaults["last_panel"]) or defaults["last_panel"]).strip().lower(),
    }


def update_gui_settings(**kwargs) -> dict:
    allowed_keys = {"open_on_startup", "sidebar_collapsed", "last_panel"}
    cfg = load_config()
    gui = cfg.setdefault("gui", copy.deepcopy(DEFAULT_CONFIG["gui"]))

    for key, value in kwargs.items():
        if key not in allowed_keys:
            continue
        if key in {"open_on_startup", "sidebar_collapsed"}:
            gui[key] = bool(value)
        elif key == "last_panel":
            panel = str(value).strip().lower() if value is not None else ""
            gui[key] = panel or DEFAULT_CONFIG["gui"]["last_panel"]

    cfg["gui"] = gui
    save_config(cfg)
    return get_gui_settings()


def update_user_setting(key: str, value):
    cfg = load_config()
    user_settings = cfg.setdefault("UserSettings", copy.deepcopy(DEFAULT_CONFIG["UserSettings"]))
    if key not in user_settings:
        raise KeyError(f"Unknown user setting: {key}")
    user_settings[key] = value
    cfg["UserSettings"] = user_settings
    save_config(cfg)
