from __future__ import annotations

from bitcraft_preview.ui.shell.styles import build_dark_stylesheet


def __getattr__(name: str):
	if name == "MainShellWindow":
		from bitcraft_preview.ui.shell.window import MainShellWindow

		return MainShellWindow
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["MainShellWindow", "build_dark_stylesheet"]
