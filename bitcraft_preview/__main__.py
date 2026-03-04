import sys
import signal
import ctypes
from ctypes import wintypes
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from bitcraft_preview.ui.overlay_manager import OverlayManager
from bitcraft_preview.logging_setup import init_logging
from bitcraft_preview.config import DEBUG

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
    app = QApplication(sys.argv)
    
    # Handle CTRL+C if DEBUG is enabled
    if DEBUG:
        signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    # Configure system tray icon so the user can quit the app
    app.setQuitOnLastWindowClosed(False)
    
    tray_icon = QSystemTrayIcon()
    # It's best practice to use an actual icon file. Since we don't have one readily available,
    # we can use a built-in standard icon or just text if icon is missing, but QSystemTrayIcon
    # requires a valid icon to show up. We will use a standard icon.
    fallback_icon =  app.style().standardIcon(app.style().StandardPixmap.SP_ComputerIcon)
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
