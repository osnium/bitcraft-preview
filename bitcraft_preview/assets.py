"""Helpers for resolving bundled asset paths in dev and frozen builds."""

from __future__ import annotations

import os
import sys


def get_asset_path(*parts: str) -> str:
    """Return absolute path to an asset under bitcraft_preview/assets."""
    if getattr(sys, "frozen", False):
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        return os.path.join(base_path, "assets", *parts)

    package_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(package_dir, "assets", *parts)
