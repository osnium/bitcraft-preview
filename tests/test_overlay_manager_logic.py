import unittest
from unittest.mock import patch

from bitcraft_preview.ui.overlay_manager import OverlayManager


class _FakeOverlay:
    def __init__(self, visible=True, dragging=False, hwnd=9001, label_text="steam1"):
        self._visible = visible
        self.dragging = dragging
        self._hwnd = hwnd
        self.label_text = label_text
        self.hidden_calls = 0
        self.shown_calls = 0
        self.update_calls = 0
        self.sync_calls = 0

    def sync_size(self):
        self.sync_calls += 1

    def isVisible(self):
        return self._visible

    def hide(self):
        self._visible = False
        self.hidden_calls += 1

    def show(self):
        self._visible = True
        self.shown_calls += 1

    def update_thumbnail_rect(self):
        self.update_calls += 1

    def winId(self):
        return self._hwnd


class OverlayManagerLogicTests(unittest.TestCase):
    def _manager(self):
        manager = OverlayManager.__new__(OverlayManager)
        manager.overlays = {}
        manager._overlay_windows = {}
        manager._live_refresh_queued = False
        manager._refresh_hotkey_binding = lambda: None
        manager.get_active_window = lambda: 0
        manager._is_target_process_foreground = lambda: False
        return manager

    def test_should_show_overlays_when_focus_only_disabled(self):
        manager = self._manager()
        with patch("bitcraft_preview.ui.overlay_manager.get_show_overlay_only_when_focused", return_value=False):
            self.assertTrue(manager._should_show_overlays())

    def test_should_show_overlays_while_dragging_even_when_unfocused(self):
        manager = self._manager()
        manager.overlays = {123: _FakeOverlay(dragging=True)}
        with patch("bitcraft_preview.ui.overlay_manager.get_show_overlay_only_when_focused", return_value=True):
            self.assertTrue(manager._should_show_overlays(active_hwnd=0))

    def test_apply_live_settings_hides_when_focus_only_unfocused(self):
        manager = self._manager()
        overlay = _FakeOverlay(visible=True, dragging=False)
        manager.overlays = {111: overlay}

        with (
            patch("bitcraft_preview.ui.overlay_manager.get_overlay_enabled", return_value=True),
            patch("bitcraft_preview.ui.overlay_manager.get_show_overlay_only_when_focused", return_value=True),
            patch("bitcraft_preview.ui.overlay_manager.get_hide_active_window_overlay", return_value=False),
        ):
            manager._apply_live_settings()

        self.assertEqual(overlay.sync_calls, 1)
        self.assertEqual(overlay.hidden_calls, 1)
        self.assertFalse(overlay.isVisible())

    def test_apply_live_settings_shows_overlay_when_refocused(self):
        manager = self._manager()
        overlay = _FakeOverlay(visible=False, dragging=False)
        manager.overlays = {111: overlay}
        manager._is_target_process_foreground = lambda: True

        with (
            patch("bitcraft_preview.ui.overlay_manager.get_overlay_enabled", return_value=True),
            patch("bitcraft_preview.ui.overlay_manager.get_show_overlay_only_when_focused", return_value=True),
            patch("bitcraft_preview.ui.overlay_manager.get_hide_active_window_overlay", return_value=False),
        ):
            manager._apply_live_settings()

        self.assertEqual(overlay.sync_calls, 1)
        self.assertEqual(overlay.shown_calls, 1)
        self.assertEqual(overlay.update_calls, 1)
        self.assertTrue(overlay.isVisible())


if __name__ == "__main__":
    unittest.main()
