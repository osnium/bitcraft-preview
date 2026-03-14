"""Application version helpers.

App release version is sourced from pyproject metadata.
"""

from __future__ import annotations

from importlib import metadata
from pathlib import Path
import sys


def _version_from_pyproject() -> str | None:
    """Read version from pyproject.toml when available."""
    try:
        import tomllib
    except ModuleNotFoundError:
        return None

    candidates = [Path(__file__).resolve().parent.parent / "pyproject.toml"]
    if getattr(sys, "frozen", False):
        candidates.append(Path(getattr(sys, "_MEIPASS", "")) / "pyproject.toml")
        candidates.append(Path(sys.executable).resolve().parent / "pyproject.toml")

    for pyproject_path in candidates:
        if not pyproject_path.exists():
            continue

        try:
            data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        project = data.get("project")
        if isinstance(project, dict):
            value = project.get("version")
            if isinstance(value, str) and value.strip():
                return value.strip()

    return None


def get_app_version() -> str:
    """Return application version.

    Prefer pyproject.toml so version bumps are sourced from a single place.
    """
    pyproject_version = _version_from_pyproject()
    if pyproject_version:
        return pyproject_version

    try:
        return metadata.version("bitcraft_preview")
    except metadata.PackageNotFoundError:
        return "0.0.0+unknown"