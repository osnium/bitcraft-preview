# bitcraft_preview/ui/overlay_manager.py
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import QTimer
import ctypes
from bitcraft_preview.win32.window_discovery import enumerate_windows
from bitcraft_preview.ui.tile import LivePreviewTile
from bitcraft_preview.config import REFRESH_INTERVAL_MS
from bitcraft_preview.win32.title_parse import display_label
import logging

logger = logging.getLogger("bitcraft_preview")
user32 = ctypes.windll.user32

class OverlayManager:
    def __init__(self):
        self.overlays = {}  # target_hwnd -> LivePreviewTile overlay
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_windows)
        self.timer.start(REFRESH_INTERVAL_MS)
        self.refresh_windows()

    def get_active_window(self):
        return user32.GetForegroundWindow()

    def refresh_windows(self):
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
            label_text = display_label(window.title)
            if window.hwnd not in self.overlays:
                overlay = LivePreviewTile(window.hwnd, label_text)
                self.overlays[window.hwnd] = overlay
                
                # Default position (top-left offset)
                offset = 50 + (len(self.overlays) - 1) * 300
                overlay.move(offset, 50)
                
                logger.info(f"Added overlay for window {window.hwnd} [{label_text}]")
                
            else:
                overlay = self.overlays[window.hwnd]
                if overlay.label_text != label_text:
                    overlay.label_text = label_text
                    overlay.label.setText(label_text)

            # Hide overlay if this client is active
            if window.hwnd == active_hwnd:
                if overlay.isVisible():
                    overlay.hide()
                    logger.debug(f"Hiding overlay for active window {window.hwnd}")
            else:
                if not overlay.isVisible():
                    overlay.show()
                    logger.debug(f"Showing overlay for inactive window {window.hwnd}")
