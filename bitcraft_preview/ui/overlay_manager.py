# bitcraft_preview/ui/overlay_manager.py
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import QTimer
import ctypes
import psutil
from bitcraft_preview.win32.window_discovery import enumerate_windows
from bitcraft_preview.ui.tile import LivePreviewTile
from bitcraft_preview.config import PROCESS_NAME, REFRESH_INTERVAL_MS, get_hide_active_window_overlay, get_preview_tile_width, get_switch_window_enabled, get_switch_window_hotkey
from bitcraft_preview.win32.title_parse import display_label
from bitcraft_preview.win32.activation import activate_window
from bitcraft_preview.win32.hotkey_monitor import GlobalHotkeyMonitor
import logging

logger = logging.getLogger("bitcraft_preview")
user32 = ctypes.windll.user32
HOTKEY_POLL_INTERVAL_MS = 25

class OverlayManager:
    def __init__(self):
        self.overlays = {}  # target_hwnd -> LivePreviewTile overlay
        self.hotkey_monitor = GlobalHotkeyMonitor()
        self._current_hotkey_spec = ""
        self._last_switched_hwnd = None
        # Always keep a valid binding to avoid a non-functional hotkey if config is malformed.
        self.hotkey_monitor.set_hotkey("MOUSE5")
        self._current_hotkey_spec = "MOUSE5"
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_windows)
        self.timer.start(REFRESH_INTERVAL_MS)

        # Poll hotkey separately from expensive overlay refresh so switching stays responsive.
        self.hotkey_timer = QTimer()
        self.hotkey_timer.timeout.connect(self.poll_hotkey)
        self.hotkey_timer.start(HOTKEY_POLL_INTERVAL_MS)

        self.refresh_windows()

    def get_active_window(self):
        return user32.GetForegroundWindow()

    def _refresh_hotkey_binding(self):
        configured_spec = get_switch_window_hotkey().strip()
        if not configured_spec:
            configured_spec = "MOUSE5"

        if configured_spec == self._current_hotkey_spec:
            return

        if self.hotkey_monitor.set_hotkey(configured_spec):
            self._current_hotkey_spec = configured_spec

    def _sorted_windows(self, windows):
        return sorted(windows, key=lambda w: ((w.sandbox_name or "").lower(), int(w.hwnd)))

    def _normalize_hwnd(self, hwnd):
        try:
            return int(hwnd)
        except (TypeError, ValueError):
            return None

    def _is_target_process_foreground(self):
        active_hwnd = self._normalize_hwnd(self.get_active_window())
        if not active_hwnd:
            return False

        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(active_hwnd, ctypes.byref(pid))
        if not pid.value:
            return False

        try:
            active_name = psutil.Process(pid.value).name().lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False

        return active_name == PROCESS_NAME.lower()

    def _switch_to_next_window(self, windows):
        if not windows:
            return

        ordered = self._sorted_windows(windows)
        active_hwnd = self._normalize_hwnd(self.get_active_window())
        hwnds = [self._normalize_hwnd(w.hwnd) for w in ordered]
        hwnds = [hwnd for hwnd in hwnds if hwnd is not None]
        if not hwnds:
            return

        last_switched = self._normalize_hwnd(self._last_switched_hwnd)

        # Prefer our own cursor (last switched hwnd) so presses always advance,
        # even if foreground-window reporting is stale or focus was denied.
        if last_switched in hwnds:
            current_index = hwnds.index(last_switched)
            next_hwnd = hwnds[(current_index + 1) % len(hwnds)]
        elif active_hwnd in hwnds:
            current_index = hwnds.index(active_hwnd)
            next_hwnd = hwnds[(current_index + 1) % len(hwnds)]
        else:
            next_hwnd = hwnds[0]

        activate_window(next_hwnd)
        self._last_switched_hwnd = next_hwnd
        logger.info("Hotkey switch: activated window %s", next_hwnd)

    def poll_hotkey(self):
        self._refresh_hotkey_binding()
        if not get_switch_window_enabled():
            return

        if not self._is_target_process_foreground():
            return

        if self.hotkey_monitor.poll_triggered():
            self._switch_to_next_window(enumerate_windows())

    def refresh_windows(self):
        self._refresh_hotkey_binding()
        windows = enumerate_windows()

        current_hwnds = {w.hwnd: w for w in windows}
        active_hwnd = self.get_active_window()

        # Remove closed windows
        for hwnd in list(self.overlays.keys()):
            if hwnd not in current_hwnds:
                overlay = self.overlays.pop(hwnd)
                overlay.close()
                overlay.deleteLater()
                logger.info(f"Removed overlay for window {hwnd}")

        # Add or update windows
        for window in windows:
            label_text = display_label(window.title, window.pid)
            if window.hwnd not in self.overlays:
                overlay = LivePreviewTile(window.hwnd, label_text)
                self.overlays[window.hwnd] = overlay
                
                # Default position (top-left offset)
                offset = 50 + (len(self.overlays) - 1) * get_preview_tile_width()
                overlay.move(offset, 50)
                
                logger.info(f"Added overlay for window {window.hwnd} [{label_text}]")
                
            else:
                overlay = self.overlays[window.hwnd]
                # Re-compute label in case config changed
                label_text = display_label(window.title, window.pid)
                if overlay.label_text != label_text:
                    overlay.label_text = label_text
                    overlay.label.setText(label_text)
                overlay.sync_size()

            # Hide overlay if this client is active and config enables it
            if get_hide_active_window_overlay() and window.hwnd == active_hwnd:
                if overlay.isVisible():
                    overlay.hide()
            elif not overlay.isVisible():
                overlay.show()
                overlay.update_thumbnail_rect()
