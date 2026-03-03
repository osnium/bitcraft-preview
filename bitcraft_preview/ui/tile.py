from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainterPath, QRegion, QPainter, QColor
import ctypes
from bitcraft_preview.win32.dwm_thumbnail import register_thumbnail, update_thumbnail, unregister_thumbnail
from bitcraft_preview.win32.activation import activate_window

class LivePreviewTile(QWidget):
    def __init__(self, target_hwnd: int, label_text: str, parent=None):
        super().__init__(parent)
        self.target_hwnd = target_hwnd
        self.label_text = label_text
        self.thumbnail_handle = None
        self.dragging = False
        self.drag_start_position = None
        self.window_start_position = None

        # Set window flags for borderless, always-on-top, tool window (no taskbar icon)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        
        # Set translucency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.resize(300, 200) # Default size
        self.setup_ui()
        
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # Sandbox label at bottom-left
        self.label = QLabel(self.label_text)
        self.label.setStyleSheet(
            "color: white; background-color: rgba(0,0,0,150); padding: 5px; font-weight: bold; border-radius: 5px;"
        )
        
        # Spacer so label stays at the bottom
        self.layout.addStretch()
        self.layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)

    def paintEvent(self, event):
        # We must paint the background for the transparent window to register mouse clicks properly.
        # Otherwise, clicks pass entirely right through the invisible areas.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(0, 0, 0, 128)) # 50% opacity
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_start_position = event.globalPosition().toPoint()
            self.window_start_position = self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging:
            delta = event.globalPosition().toPoint() - self.drag_start_position
            self.move(self.window_start_position + delta)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            # Check if it was a fast click vs a drag
            delta = event.globalPosition().toPoint() - self.drag_start_position
            if delta.manhattanLength() < 5:
                activate_window(self.target_hwnd)
            event.accept()

    def showEvent(self, event):
        super().showEvent(event)
        if not self.thumbnail_handle:
            win_id = int(self.winId())
            self.thumbnail_handle = register_thumbnail(win_id, self.target_hwnd)
            self.update_thumbnail_rect()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_thumbnail_rect()
        
        # Add rounded corners to the OS window mask so the DWM thumbnail is also clipped
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 15, 15)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    def update_thumbnail_rect(self):
        if self.thumbnail_handle:
            # DWM renders over the Qt window. We restrict its height 
            # so the QLabel sandbox name below is visible and not covered.
            label_zone = self.label.height() + 20 # Label + margins
            rect = (0, 0, self.width(), self.height() - label_zone)
            update_thumbnail(self.thumbnail_handle, rect)

    def closeEvent(self, event):
        if self.thumbnail_handle:
            unregister_thumbnail(self.thumbnail_handle)
            self.thumbnail_handle = None
        super().closeEvent(event)
