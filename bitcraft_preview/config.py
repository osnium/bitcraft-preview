import os
import json
import logging
import copy
import sys

logger = logging.getLogger("bitcraft_preview")

# Default values
DEFAULT_CONFIG = {
    "version": "2.1",
    "mode": "sandboxie",
    "UserSettings": {
        "inline_label": True,                 # Needs Restart
        "preview_opacity": 0.8,               # Live
        "hover_zoom_enabled": True,           # Live
        "hover_zoom_percent": 200,            # Live (100-500)
        "hide_active_window_overlay": False,  # Live
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
    }
}

def _resolve_config_file_path() -> str:
    # In packaged builds, keep config next to the executable.
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        # In dev, keep config at repository/workspace root.
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_dir, "config.json")


config_file_path = _resolve_config_file_path()


def get_config_file_path() -> str:
    return config_file_path

def load_config():
    merged_config = copy.deepcopy(DEFAULT_CONFIG)
    if os.path.exists(config_file_path):
        try:
            with open(config_file_path, "r") as f:
                user_config = json.load(f)

                # Preserve any custom top-level keys, then apply default sections.
                if isinstance(user_config, dict):
                    merged_config = copy.deepcopy(user_config)

                if "UserSettings" not in merged_config or not isinstance(merged_config["UserSettings"], dict):
                    merged_config["UserSettings"] = {}
                if "SystemSettings" not in merged_config or not isinstance(merged_config["SystemSettings"], dict):
                    merged_config["SystemSettings"] = {}

                if "native_mode" not in merged_config or not isinstance(merged_config["native_mode"], dict):
                    merged_config["native_mode"] = {}
                if "sandboxie_mode" not in merged_config or not isinstance(merged_config["sandboxie_mode"], dict):
                    merged_config["sandboxie_mode"] = {}

                # Merge known sections while retaining unknown fields from disk.
                default_user = DEFAULT_CONFIG["UserSettings"]
                default_system = DEFAULT_CONFIG["SystemSettings"]
                default_native = DEFAULT_CONFIG["native_mode"]
                default_sandboxie = DEFAULT_CONFIG["sandboxie_mode"]

                merged_user = copy.deepcopy(default_user)
                merged_user.update(merged_config["UserSettings"])
                merged_config["UserSettings"] = merged_user

                merged_system = copy.deepcopy(default_system)
                merged_system.update(merged_config["SystemSettings"])
                merged_config["SystemSettings"] = merged_system

                merged_native = copy.deepcopy(default_native)
                merged_native.update(merged_config["native_mode"])
                if not isinstance(merged_native.get("last_reconcile"), dict):
                    merged_native["last_reconcile"] = {}
                reconcile = copy.deepcopy(default_native["last_reconcile"])
                reconcile.update(merged_native["last_reconcile"])
                merged_native["last_reconcile"] = reconcile
                merged_config["native_mode"] = merged_native

                merged_sandboxie = copy.deepcopy(default_sandboxie)
                merged_sandboxie.update(merged_config["sandboxie_mode"])
                merged_config["sandboxie_mode"] = merged_sandboxie

                if "version" not in merged_config:
                    merged_config["version"] = DEFAULT_CONFIG["version"]
                if "mode" not in merged_config:
                    merged_config["mode"] = DEFAULT_CONFIG["mode"]
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
def get_hover_zoom_enabled(): return load_config()["UserSettings"]["hover_zoom_enabled"]
def get_hover_zoom_percent(): return load_config()["UserSettings"]["hover_zoom_percent"]
def get_hide_active_window_overlay(): return load_config()["UserSettings"]["hide_active_window_overlay"]
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
