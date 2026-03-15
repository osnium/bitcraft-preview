from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QIntValidator, QPainter, QPen
from PySide6.QtWidgets import QFrame, QLineEdit, QPushButton, QSlider, QToolButton, QVBoxLayout, QWidget


def _key_to_string(key: int) -> str:
    if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F24:
        return f"F{key - int(Qt.Key.Key_F1) + 1}"

    mapping = {
        Qt.Key.Key_Space: "SPACE",
        Qt.Key.Key_Tab: "TAB",
        Qt.Key.Key_Escape: "ESC",
        Qt.Key.Key_Return: "ENTER",
        Qt.Key.Key_Enter: "ENTER",
        Qt.Key.Key_Backspace: "BACKSPACE",
    }
    if key in mapping:
        return mapping[key]

    if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
        return chr(key)
    if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
        return chr(key)

    return ""


class HotkeyCaptureButton(QPushButton):
    hotkey_captured = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._capturing = False
        self._hotkey_text = "MOUSE5"
        self.setText("Capture Hotkey")
        self.clicked.connect(self._begin_capture)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_hotkey(self, hotkey_text: str) -> None:
        normalized = (hotkey_text or "MOUSE5").strip().upper()
        self._hotkey_text = normalized or "MOUSE5"
        self.setText(self._hotkey_text)

    def _begin_capture(self) -> None:
        self._capturing = True
        self.setText("Press any key...")
        self.setFocus()

    def _finalize_capture(self, hotkey_text: str) -> None:
        self._capturing = False
        self.set_hotkey(hotkey_text)
        self.hotkey_captured.emit(self._hotkey_text)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if not self._capturing:
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key.Key_Escape:
            self._capturing = False
            self.setText(self._hotkey_text)
            return

        key_name = _key_to_string(event.key())
        if key_name:
            self._finalize_capture(key_name)
            return

        self.setText("Unsupported key")

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if self._capturing and event.button() == Qt.MouseButton.BackButton:
            self._finalize_capture("MOUSE4")
            return
        if self._capturing and event.button() == Qt.MouseButton.ForwardButton:
            self._finalize_capture("MOUSE5")
            return
        super().mousePressEvent(event)


class DirectInputSlider(QSlider):
    def __init__(self, dialog_title: str, suffix: str = "", parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._dialog_title = dialog_title
        self._suffix = suffix
        self._value_before_double_click: int | None = None
        self._inline_editor = QLineEdit(self)
        self._inline_editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._inline_editor.setValidator(QIntValidator(self.minimum(), self.maximum(), self._inline_editor))
        self._inline_editor.hide()
        self._inline_editor.returnPressed.connect(self._commit_inline_edit)
        self._inline_editor.editingFinished.connect(self._commit_inline_edit)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._value_before_double_click = self.value()
        super().mousePressEvent(event)

    def setRange(self, min: int, max: int) -> None:  # type: ignore[override]
        super().setRange(min, max)
        self._inline_editor.setValidator(QIntValidator(min, max, self._inline_editor))

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self._inline_editor.isVisible():
            self._position_inline_editor()

    def _position_inline_editor(self) -> None:
        editor_w = min(86, max(60, self.width() // 5))
        editor_h = 22
        x = (self.width() - editor_w) // 2
        y = (self.height() - editor_h) // 2
        self._inline_editor.setGeometry(x, y, editor_w, editor_h)

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        if self._value_before_double_click is not None and self.value() != self._value_before_double_click:
            self.setValue(self._value_before_double_click)
        self._position_inline_editor()
        self._inline_editor.setText(str(self.value()))
        self._inline_editor.show()
        self._inline_editor.setFocus()
        self._inline_editor.selectAll()
        event.accept()

    def _commit_inline_edit(self) -> None:
        if not self._inline_editor.isVisible():
            return
        text = self._inline_editor.text().strip()
        if text:
            value = int(text)
            value = max(self.minimum(), min(self.maximum(), value))
            self.setValue(value)
        self._inline_editor.hide()


class TilePreviewWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tile_width = 300
        self._tile_height = 200
        self.setMinimumHeight(150)
        self.setMaximumHeight(150)

    def set_tile_size(self, width: int, height: int) -> None:
        self._tile_width = max(100, min(500, int(width)))
        self._tile_height = max(60, min(500, int(height)))
        self.update()

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(240, 170)

    def _primary_resolution(self) -> tuple[int, int]:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return (1920, 1080)
        geo = screen.geometry()
        return (max(1, int(geo.width())), max(1, int(geo.height())))

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg_rect = self.rect().adjusted(8, 8, -8, -8)
        painter.setPen(QPen(QColor("#3d5369"), 1))
        painter.setBrush(QColor("#172334"))
        painter.drawRoundedRect(bg_rect, 10, 10)

        stable_preview_zone_w = 210
        stable_preview_zone_h = 100
        zone_left = bg_rect.left() + (bg_rect.width() - stable_preview_zone_w) // 2
        zone_top = bg_rect.top() + 8
        preview_zone = QRect(zone_left, zone_top, stable_preview_zone_w, stable_preview_zone_h)

        monitor_w, monitor_h = self._primary_resolution()
        monitor_aspect = monitor_w / max(1, monitor_h)
        monitor_rect_w = preview_zone.width()
        monitor_rect_h = int(monitor_rect_w / monitor_aspect)
        if monitor_rect_h > preview_zone.height():
            monitor_rect_h = preview_zone.height()
            monitor_rect_w = int(monitor_rect_h * monitor_aspect)
        monitor_left = preview_zone.left() + (preview_zone.width() - monitor_rect_w) // 2
        monitor_top = preview_zone.top() + (preview_zone.height() - monitor_rect_h) // 2
        monitor_rect = QRect(monitor_left, monitor_top, monitor_rect_w, monitor_rect_h)

        painter.setPen(QPen(QColor("#44607c"), 1))
        painter.setBrush(QColor("#1a2a3e"))
        painter.drawRoundedRect(monitor_rect, 6, 6)

        cols = 10
        rows = 6

        painter.setPen(QPen(QColor("#2f4359"), 1))
        for col in range(1, cols):
            x = monitor_rect.left() + int((col / cols) * monitor_rect.width())
            painter.drawLine(x, monitor_rect.top(), x, monitor_rect.bottom())
        for row in range(1, rows):
            y = monitor_rect.top() + int((row / rows) * monitor_rect.height())
            painter.drawLine(monitor_rect.left(), y, monitor_rect.right(), y)

        painter.setPen(QColor("#8fb2d1"))
        painter.drawText(
            bg_rect.adjusted(10, 0, -10, 0),
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
            f"Main monitor: {monitor_w}x{monitor_h}",
        )

        preview_w = max(2, int((self._tile_width / monitor_w) * monitor_rect.width()))
        preview_h = max(2, int((self._tile_height / monitor_h) * monitor_rect.height()))
        left = monitor_rect.left() + (monitor_rect.width() - preview_w) // 2
        top = monitor_rect.top() + (monitor_rect.height() - preview_h) // 2

        tile_rect = QRect(left, top, preview_w, preview_h)
        painter.setPen(QPen(QColor("#6ec8ff"), 2))
        painter.setBrush(QColor("#273d57"))
        radius = min(6, max(2, int(min(preview_w, preview_h) * 0.12)))
        painter.drawRoundedRect(tile_rect, radius, radius)

        painter.setPen(QColor("#e5edf7"))
        text_rect = QRect(bg_rect.left(), monitor_rect.bottom() + 4, bg_rect.width(), max(18, bg_rect.bottom() - monitor_rect.bottom() - 4))
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            f"{self._tile_width} x {self._tile_height}",
        )


class CollapsibleSection(QWidget):
    def __init__(self, title: str, content_widget: QWidget, collapsed: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        self.toggle_button = QToolButton(self)
        self.toggle_button.setObjectName("SectionToggle")
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(not collapsed)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if not collapsed else Qt.ArrowType.RightArrow)
        self.toggle_button.clicked.connect(self._toggle_content)
        root.addWidget(self.toggle_button)

        self.divider = QFrame(self)
        self.divider.setObjectName("SectionDivider")
        root.addWidget(self.divider)

        self.content_frame = QFrame(self)
        self.content_frame.setObjectName("GroupCard")
        content_frame_layout = QVBoxLayout(self.content_frame)
        content_frame_layout.setContentsMargins(10, 10, 10, 10)
        content_frame_layout.addWidget(content_widget)

        self.content = self.content_frame
        self.content.setVisible(not collapsed)
        root.addWidget(self.content)
        self.divider.setVisible(collapsed)

        self._content_animation = QPropertyAnimation(self.content_frame, b"maximumHeight", self)
        self._content_animation.setDuration(110)
        self._content_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._content_animation.finished.connect(self._on_animation_finished)

        if collapsed:
            self.content_frame.setMaximumHeight(0)
        else:
            self.content_frame.setMaximumHeight(16777215)

    def _toggle_content(self) -> None:
        expanded = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.divider.setVisible(not expanded)

        self._content_animation.stop()
        if expanded:
            self.content.setVisible(True)
            start_height = max(0, self.content_frame.height())
            end_height = max(1, self.content_frame.layout().sizeHint().height() + 20)
            self._content_animation.setStartValue(start_height)
            self._content_animation.setEndValue(end_height)
        else:
            self._content_animation.setStartValue(self.content_frame.height())
            self._content_animation.setEndValue(0)

        self._content_animation.start()

    def _on_animation_finished(self) -> None:
        expanded = self.toggle_button.isChecked()
        if expanded:
            self.content.setVisible(True)
            self.content_frame.setMaximumHeight(16777215)
        else:
            self.content.setVisible(False)
            self.content_frame.setMaximumHeight(0)
