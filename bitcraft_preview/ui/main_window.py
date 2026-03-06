from PySide6.QtWidgets import QMainWindow, QGridLayout, QWidget, QLabel
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QIcon

from bitcraft_preview.win32.window_discovery import enumerate_windows
from bitcraft_preview.ui.tile import LivePreviewTile
from bitcraft_preview.config import REFRESH_INTERVAL_MS
from bitcraft_preview.win32.title_parse import display_label

import logging
logger = logging.getLogger("bitcraft_preview")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BitCraft Preview")
        self.resize(800, 600)
        self.tiles = {} # mapping of hwnd to LivePreviewTile
        self.init_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_windows)
        self.timer.start(REFRESH_INTERVAL_MS)
        self.refresh_windows()

    def init_ui(self):
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        self.grid_layout = QGridLayout(self.central_widget)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_layout.setSpacing(10)
        
        self.empty_label = QLabel("No BitCraft clients found", self)
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.grid_layout.addWidget(self.empty_label, 0, 0)

    def refresh_windows(self):
        windows = enumerate_windows()
        
        # update current hwnds
        current_hwnds = {w.hwnd: w for w in windows}
        
        # remove missing windows
        for hwnd in list(self.tiles.keys()):
            if hwnd not in current_hwnds:
                tile = self.tiles.pop(hwnd)
                self.grid_layout.removeWidget(tile)
                tile.close()
                tile.deleteLater()
                # log removal
                logger.info(f"Removed window {hwnd}")
                
        # sort explicitly by sandbox name to remain stable
        windows.sort(key=lambda w: w.sandbox_name or "")
        
        # add or update window
        for index, window in enumerate(windows):
            if window.hwnd not in self.tiles:
                # Add new
                label_text = display_label(window.title, window.pid)
                tile = LivePreviewTile(window.hwnd, label_text)
                self.tiles[window.hwnd] = tile
                row = index // 2
                col = index % 2
                self.grid_layout.addWidget(tile, row, col)
                # log addition
                logger.info(f"Added tile for window {window.hwnd} [{label_text}]")
            else:
                # Update position based on sorting
                tile = self.tiles[window.hwnd]
                label_text = display_label(window.title, window.pid)
                if tile.label_text != label_text:
                    tile.label_text = label_text
                    tile.label.setText(label_text)
                    logger.info(f"Updated tile label for window {window.hwnd} [{label_text}]")
                
                row = index // 2
                col = index % 2
                self.grid_layout.addWidget(tile, row, col)

        if not self.tiles:
            self.empty_label.show()
        else:
            self.empty_label.hide()
