from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QPoint
import ctypes

from bitcraft_preview.win32.dwm_thumbnail import register_thumbnail, update_thumbnail, unregister_thumbnail
from bitcraft_preview.win32.activation import activate_window

class WinEventFilter(QWidget):
    def eventFilter(self, obj, event):
        # Pass mouse press and release to activate the window
        if event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                activate_window(self.source_hwnd)
        return super().eventFilter(obj, event)

class LivePreviewTile(QWidget):
    def __init__(self, target_hwnd: int, label_text: str, parent=None):
        super().__init__(parent)
        self.target_hwnd = target_hwnd
        self.label_text = label_text
        self.thumbnail_handle = None

        self.setup_ui()
        # Install an event filter to capture clicks on this widget
        self.installEventFilter(self)

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel(self.label_text)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: white; background-color: rgba(0,0,0,150); padding: 5px;")
        
        # Spacer so label goes to bottom, adjust as needed
        self.layout.addStretch()
        self.layout.addWidget(self.label)
        
    def showEvent(self, event):
        super().showEvent(event)
        if not self.thumbnail_handle:
            # register self with DWM using the top-level window's HWND
            win_id = int(self.window().winId())
            self.thumbnail_handle = register_thumbnail(win_id, self.target_hwnd)
            self.update_thumbnail_rect()
            
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_thumbnail_rect()
        
    def update_thumbnail_rect(self):
        if self.thumbnail_handle:
            # map coordinates to the top-level window
            top_level = self.window()
            pos = self.mapTo(top_level, QPoint(0, 0))
            
            # left, top, right, bottom
            left = pos.x()
            top = pos.y()
            right = left + self.width()
            bottom = top + self.height()
            
            rect = (left, top, right, bottom)
            update_thumbnail(self.thumbnail_handle, rect)

    def closeEvent(self, event):
        if self.thumbnail_handle:
            unregister_thumbnail(self.thumbnail_handle)
            self.thumbnail_handle = None
        super().closeEvent(event)

    def eventFilter(self, obj, event):
        if obj == self and event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                activate_window(self.target_hwnd)
                return True
        return super().eventFilter(obj, event)
