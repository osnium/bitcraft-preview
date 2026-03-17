"""Background GitHub release checker.

Fetches the latest release from the GitHub API in a worker thread and
emits ``update_available(current_version, latest_version)`` when a newer
release is found.  All network/parse errors are logged and silently
swallowed so startup is never affected.
"""

from __future__ import annotations

import json
import logging
import urllib.request

from PySide6.QtCore import QThread, Signal

from bitcraft_preview.version import get_app_version

GITHUB_API_URL = "https://api.github.com/repos/osnium/bitcraft-preview/releases/latest"
GITHUB_RELEASES_PAGE = "https://github.com/osnium/bitcraft-preview/releases"

_log = logging.getLogger(__name__)


def _parse_version(tag: str) -> tuple[int, ...]:
    """Strip leading V/v and return a comparable version tuple."""
    clean = tag.lstrip("Vv")
    try:
        return tuple(int(x) for x in clean.split("."))
    except ValueError:
        return ()


class UpdateChecker(QThread):
    """Worker thread that checks for a newer GitHub release once."""

    update_available: Signal = Signal(str, str)  # (current_version, latest_version)

    def run(self) -> None:  # noqa: D102
        try:
            req = urllib.request.Request(
                GITHUB_API_URL,
                headers={"Accept": "application/vnd.github+json", "User-Agent": "bitcraft-preview-update-checker"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            tag_name: str = data.get("tag_name", "")
            if not tag_name:
                _log.debug("Update check: no tag_name in response")
                return

            current = get_app_version()
            latest_clean = tag_name.lstrip("Vv")

            current_tuple = _parse_version(current)
            latest_tuple = _parse_version(latest_clean)

            if not current_tuple or not latest_tuple:
                _log.debug("Update check: could not parse versions current=%r latest=%r", current, latest_clean)
                return

            if latest_tuple > current_tuple:
                _log.info("Update available: %s -> %s", current, latest_clean)
                self.update_available.emit(current, latest_clean)
            else:
                _log.debug("Update check: up to date (current=%s, latest=%s)", current, latest_clean)

        except Exception:
            _log.debug("Update check failed (network/parse error)", exc_info=True)
