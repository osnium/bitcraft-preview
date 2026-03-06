from __future__ import annotations

import os
import re
import winreg
from dataclasses import dataclass


BITCRAFT_APP_ID = "3454650"


class SteamLocatorError(RuntimeError):
    pass


@dataclass
class SteamInstallInfo:
    steam_root: str
    library_path: str
    bitcraft_path: str


def get_primary_steam_path() -> str:
    """Read Steam install root from HKCU\\Software\\Valve\\Steam\\SteamPath."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            value, _ = winreg.QueryValueEx(key, "SteamPath")
    except OSError as e:
        raise SteamLocatorError("Unable to read SteamPath from HKCU registry") from e

    steam_path = os.path.normpath(str(value))
    if not os.path.isdir(steam_path):
        raise SteamLocatorError(f"Steam path from registry does not exist: {steam_path}")
    return steam_path


def _default_bitcraft_path(library_root: str) -> str:
    return os.path.join(
        library_root,
        "steamapps",
        "common",
        "BitCraft Online",
        "BitCraft.exe",
    )


def _extract_library_paths(vdf_text: str) -> list[str]:
    # Supports both old and newer libraryfolders.vdf styles with indexed entries.
    paths: list[str] = []
    for match in re.finditer(r'"path"\s+"([^"]+)"', vdf_text):
        raw = match.group(1)
        path = raw.replace(r"\\", "\\")
        paths.append(os.path.normpath(path))
    return paths


def _library_contains_app(vdf_text: str, app_id: str) -> bool:
    return bool(re.search(rf'"{re.escape(app_id)}"\s+"\d+"', vdf_text))


def find_bitcraft_install(steam_root: str, app_id: str = BITCRAFT_APP_ID) -> SteamInstallInfo:
    """Find BitCraft install by checking default path, then libraryfolders.vdf."""
    steam_root = os.path.normpath(steam_root)

    default_path = _default_bitcraft_path(steam_root)
    if os.path.isfile(default_path):
        return SteamInstallInfo(
            steam_root=steam_root,
            library_path=steam_root,
            bitcraft_path=default_path,
        )

    libraryfolders_path = os.path.join(steam_root, "steamapps", "libraryfolders.vdf")
    if not os.path.isfile(libraryfolders_path):
        raise SteamLocatorError(f"Could not find BitCraft and libraryfolders.vdf is missing: {libraryfolders_path}")

    with open(libraryfolders_path, "r", encoding="utf-8", errors="ignore") as f:
        vdf_text = f.read()

    for library in _extract_library_paths(vdf_text):
        candidate = _default_bitcraft_path(library)
        if os.path.isfile(candidate):
            return SteamInstallInfo(
                steam_root=steam_root,
                library_path=library,
                bitcraft_path=candidate,
            )

    # Fallback: if app id appears in VDF but executable path differs unexpectedly, report a clear error.
    if _library_contains_app(vdf_text, app_id):
        raise SteamLocatorError(
            f"BitCraft app id {app_id} found in library metadata, but BitCraft.exe path was not resolved."
        )

    raise SteamLocatorError(f"BitCraft app id {app_id} was not found in any Steam library.")
