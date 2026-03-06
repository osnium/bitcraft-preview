import sys
import os
import signal
import ctypes
from ctypes import wintypes
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from bitcraft_preview.ui.overlay_manager import OverlayManager
from bitcraft_preview.logging_setup import init_logging
from bitcraft_preview.config import DEBUG, ensure_config_exists, get_config_file_path

def get_asset_path(asset_name):
    """Get the path to an asset file, handling both dev and packaged modes."""
    if getattr(sys, "frozen", False):
        # Running as compiled executable - assets are in _MEIPASS/assets/
        base_path = sys._MEIPASS
        return os.path.join(base_path, "assets", asset_name)
    else:
        # Running in development - assets are relative to this file
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, "bitcraft_preview", "assets", asset_name)

def main():
    # Mutex check to prevent multiple instances
    mutex_name = "Global\\BitCraftPreview_SingleInstanceMutex"
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    last_error = kernel32.GetLastError()
    if last_error == 183:  # ERROR_ALREADY_EXISTS
        print("BitCraftPreview is already running. Exiting.")
        return

    logger = init_logging()
    logger.info("Starting BitCraft Preview application")
    if ensure_config_exists():
        logger.info("Using config file: %s", get_config_file_path())
    else:
        logger.error("Failed to create config file: %s", get_config_file_path())

    app = QApplication(sys.argv)
    
    # Handle CTRL+C if DEBUG is enabled
    if DEBUG:
        signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    # Configure system tray icon so the user can quit the app
    app.setQuitOnLastWindowClosed(False)
    
    # Icons created by XATE Media (xate.eu)
    tray_icon = QSystemTrayIcon()
    systemtray_icon_path = get_asset_path("systemtray.ico")
    if os.path.exists(systemtray_icon_path):
        tray_icon.setIcon(QIcon(systemtray_icon_path))
    else:
        logger.warning(f"System tray icon not found at: {systemtray_icon_path}")
        fallback_icon = app.style().standardIcon(app.style().StandardPixmap.SP_ComputerIcon)
        tray_icon.setIcon(fallback_icon)
    tray_icon.setToolTip("BitCraft Preview")
    
    tray_menu = QMenu()
    quit_action = QAction("Quit", app)
    quit_action.triggered.connect(app.quit)
    tray_menu.addAction(quit_action)
    
    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()

    # Replacing MainWindow with OverlayManager
    manager = OverlayManager()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
