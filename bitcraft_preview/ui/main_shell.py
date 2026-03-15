from __future__ import annotations

import logging
import os

import psutil
from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from bitcraft_preview import config
from bitcraft_preview.native.state_manager import NativeModeStateManager

logger = logging.getLogger("bitcraft_preview")


def build_dark_stylesheet() -> str:
    return """
QWidget {
    background-color: #161c24;
    color: #ebf2fa;
    font-family: "Segoe UI", "Candara", "Trebuchet MS";
    font-size: 10pt;
}
QFrame#MainSurface {
    background-color: #111820;
    border-radius: 12px;
}
QFrame#ContentSurface {
    background-color: #1c2633;
    border: 1px solid #374b62;
    border-radius: 12px;
}
QFrame#SidebarSurface {
    background-color: #152131;
    border: 1px solid #3b5168;
    border-radius: 12px;
}
QFrame#GroupCard {
    background-color: #202d3d;
    border: 1px solid #415870;
    border-radius: 10px;
}
QLabel#SectionTitle {
    font-size: 12.5pt;
    font-weight: 600;
    color: #ffffff;
}
QLabel#MutedText {
    color: #b5c6da;
}
QPushButton {
    background-color: #253548;
    border: 1px solid #40566d;
    border-radius: 6px;
    padding: 6px 10px;
}
QPushButton:hover {
    background-color: #2d4258;
}
QPushButton:pressed {
    background-color: #213043;
}
QPushButton#SidebarToggle {
    background-color: transparent;
    border: 1px solid #3b5168;
    border-radius: 6px;
    padding: 0px;
    min-width: 20px;
    max-width: 20px;
    min-height: 20px;
    max-height: 20px;
}
QPushButton#SidebarToggle:hover {
    background-color: #203247;
}
QPushButton#QuickActionButton {
    background-color: #203247;
    border: 1px solid #3f5570;
    border-radius: 6px;
    padding: 0px;
}
QPushButton#QuickActionButton:hover {
    background-color: #2b435d;
}
QPushButton#QuickActionButton:pressed {
    background-color: #1a2c3f;
}
QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
}
QListWidget::item {
    margin: 2px 0;
    padding: 7px 8px;
    border-radius: 6px;
}
QListWidget::item:selected {
    background-color: #365375;
    color: #ffffff;
}
QListWidget::item:hover {
    background-color: #2c435f;
}
QSlider::groove:horizontal {
    border: 1px solid #4a6179;
    background: #172538;
    height: 8px;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #6ec8ff;
    border: 1px solid #2d90c8;
    width: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
QTableWidget {
    background-color: #182433;
    border: 1px solid #425972;
    gridline-color: #3c5268;
}
QHeaderView::section {
    background-color: #2c435b;
    color: #eff6ff;
    border: 1px solid #415972;
    padding: 6px;
}
QToolButton#SectionToggle {
    background-color: transparent;
    border: none;
    color: #d9e7f5;
    font-weight: 600;
    text-align: left;
    padding: 4px 2px;
}
QToolButton#SectionToggle:hover {
    color: #ffffff;
}
QFrame#SectionDivider {
    background-color: #34485f;
    min-height: 1px;
}
QWidget#QuickActionsStrip {
    background-color: transparent;
}
"""


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

        # Keep preview scale stable and map tile size against a miniature of the primary monitor.
        stable_preview_zone_w = 210
        stable_preview_zone_h = 100
        zone_left = bg_rect.left() + (bg_rect.width() - stable_preview_zone_w) // 2
        zone_top = bg_rect.top() + 8
        preview_zone = QRect(zone_left, zone_top, stable_preview_zone_w, stable_preview_zone_h)

        # Build a monitor miniature that preserves primary display aspect ratio.
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

        # Grid is relative to monitor space, so tile rectangle visually correlates with main display size.
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
        painter.drawRoundedRect(tile_rect, 8, 8)

        painter.setPen(QColor("#e5edf7"))
        painter.drawText(
            bg_rect.adjusted(0, preview_h + 14, 0, 0),
            Qt.AlignmentFlag.AlignHCenter,
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

    def _toggle_content(self) -> None:
        expanded = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.content.setVisible(expanded)
        self.divider.setVisible(not expanded)

class SettingsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._building = False
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Settings")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Changes are saved instantly to config.json")
        subtitle.setObjectName("MutedText")

        root.addWidget(title)
        root.addWidget(subtitle)

        overlay_content = QWidget(self)
        overlay_layout = QGridLayout(overlay_content)
        overlay_layout.setHorizontalSpacing(12)
        overlay_layout.setVerticalSpacing(8)

        self.preview_opacity_label = QLabel("Overlay opacity: 80%")
        self.preview_opacity = QSlider(Qt.Orientation.Horizontal)
        self.preview_opacity.setRange(0, 100)
        self.preview_opacity.valueChanged.connect(self._on_preview_opacity_changed)
        self.preview_opacity_input = QDoubleSpinBox(self)
        self.preview_opacity_input.setRange(0, 100)
        self.preview_opacity_input.setDecimals(0)
        self.preview_opacity_input.setSuffix(" %")
        self.preview_opacity_input.valueChanged.connect(self._on_preview_opacity_input_changed)
        overlay_layout.addWidget(self.preview_opacity_label, 0, 0, 1, 2)
        overlay_layout.addWidget(self.preview_opacity, 1, 0, 1, 1)
        overlay_layout.addWidget(self.preview_opacity_input, 1, 1, 1, 1)

        self.hide_active_overlay = QCheckBox("Hide active window overlay")
        self.hide_active_overlay.stateChanged.connect(
            lambda: self._set_user_bool("hide_active_window_overlay", self.hide_active_overlay.isChecked())
        )
        overlay_layout.addWidget(self.hide_active_overlay, 2, 0, 1, 2)

        self.hover_zoom_enabled = QCheckBox("Enable hover zoom")
        self.hover_zoom_enabled.stateChanged.connect(
            lambda: self._set_user_bool("hover_zoom_enabled", self.hover_zoom_enabled.isChecked())
        )
        overlay_layout.addWidget(self.hover_zoom_enabled, 3, 0, 1, 2)

        self.hover_zoom_label = QLabel("Hover zoom percent: 200%")
        self.hover_zoom_percent = QSlider(Qt.Orientation.Horizontal)
        self.hover_zoom_percent.setRange(100, 500)
        self.hover_zoom_percent.valueChanged.connect(self._on_zoom_changed)
        self.hover_zoom_input = QSpinBox(self)
        self.hover_zoom_input.setRange(100, 500)
        self.hover_zoom_input.setSuffix(" %")
        self.hover_zoom_input.valueChanged.connect(self._on_zoom_input_changed)
        overlay_layout.addWidget(self.hover_zoom_label, 4, 0, 1, 2)
        overlay_layout.addWidget(self.hover_zoom_percent, 5, 0, 1, 1)
        overlay_layout.addWidget(self.hover_zoom_input, 5, 1, 1, 1)

        self.preview_tile_width_label = QLabel("Tile width: 300")
        self.preview_tile_width = QSlider(Qt.Orientation.Horizontal)
        self.preview_tile_width.setRange(100, 500)
        self.preview_tile_width.valueChanged.connect(self._on_tile_size_changed)
        self.preview_tile_width_input = QSpinBox(self)
        self.preview_tile_width_input.setRange(100, 500)
        self.preview_tile_width_input.valueChanged.connect(self._on_tile_width_input_changed)
        overlay_layout.addWidget(self.preview_tile_width_label, 6, 0, 1, 2)
        overlay_layout.addWidget(self.preview_tile_width, 7, 0, 1, 1)
        overlay_layout.addWidget(self.preview_tile_width_input, 7, 1, 1, 1)

        self.preview_tile_height_label = QLabel("Tile height: 200")
        self.preview_tile_height = QSlider(Qt.Orientation.Horizontal)
        self.preview_tile_height.setRange(60, 500)
        self.preview_tile_height.valueChanged.connect(self._on_tile_size_changed)
        self.preview_tile_height_input = QSpinBox(self)
        self.preview_tile_height_input.setRange(60, 500)
        self.preview_tile_height_input.valueChanged.connect(self._on_tile_height_input_changed)
        overlay_layout.addWidget(self.preview_tile_height_label, 8, 0, 1, 2)
        overlay_layout.addWidget(self.preview_tile_height, 9, 0, 1, 1)
        overlay_layout.addWidget(self.preview_tile_height_input, 9, 1, 1, 1)

        self.tile_preview = TilePreviewWidget(self)
        overlay_layout.addWidget(self.tile_preview, 10, 0, 1, 2)

        hotkey_content = QWidget(self)
        hotkey_layout = QGridLayout(hotkey_content)

        self.switch_window_enabled = QCheckBox("Enable switch-window hotkey")
        self.switch_window_enabled.stateChanged.connect(
            lambda: self._set_user_bool("switch_window_enabled", self.switch_window_enabled.isChecked())
        )
        hotkey_layout.addWidget(self.switch_window_enabled, 0, 0, 1, 2)

        hotkey_layout.addWidget(QLabel("Switch hotkey"), 1, 0)
        self.switch_window_hotkey = HotkeyCaptureButton(self)
        self.switch_window_hotkey.hotkey_captured.connect(self._on_hotkey_changed)
        hotkey_layout.addWidget(self.switch_window_hotkey, 1, 1)

        hint = QLabel("Click capture, then press key or mouse back/forward button.")
        hint.setObjectName("MutedText")
        hint.setWordWrap(True)
        hotkey_layout.addWidget(hint, 2, 0, 1, 2)

        app_content = QWidget(self)
        app_layout = QVBoxLayout(app_content)
        self.open_on_startup = QCheckBox("Open GUI on application startup")
        self.open_on_startup.stateChanged.connect(self._on_gui_flag_changed)
        app_layout.addWidget(self.open_on_startup)

        self.overlay_section = CollapsibleSection("Overlay", overlay_content, collapsed=False, parent=self)
        self.hotkey_section = CollapsibleSection("Hotkeys", hotkey_content, collapsed=False, parent=self)
        self.app_section = CollapsibleSection("Application", app_content, collapsed=True, parent=self)

        root.addWidget(self.overlay_section)
        root.addWidget(self.hotkey_section)
        root.addWidget(self.app_section)

        root.addStretch(1)

    def _load_values(self) -> None:
        self._building = True
        cfg = config.load_config()
        user = cfg.get("UserSettings", {})
        gui = config.get_gui_settings()

        self.open_on_startup.setChecked(gui.get("open_on_startup", False))

        opacity = max(0.0, min(1.0, float(user.get("preview_opacity", 0.8))))
        self.preview_opacity.setValue(int(opacity * 100))
        self.preview_opacity_input.setValue(int(opacity * 100))
        self.preview_opacity_label.setText(f"Overlay opacity: {int(opacity * 100)}%")

        self.hover_zoom_enabled.setChecked(bool(user.get("hover_zoom_enabled", True)))
        hover_zoom = max(100, min(500, int(user.get("hover_zoom_percent", 200))))
        self.hover_zoom_percent.setValue(hover_zoom)
        self.hover_zoom_input.setValue(hover_zoom)
        self.hover_zoom_label.setText(f"Hover zoom percent: {hover_zoom}%")

        self.hide_active_overlay.setChecked(bool(user.get("hide_active_window_overlay", False)))
        self.switch_window_enabled.setChecked(bool(user.get("switch_window_enabled", True)))

        hotkey = str(user.get("switch_window_hotkey", "MOUSE5") or "MOUSE5")
        self.switch_window_hotkey.set_hotkey(hotkey)

        tile_width = max(100, min(500, int(user.get("preview_tile_width", 300))))
        tile_height = max(60, min(500, int(user.get("preview_tile_height", 200))))
        self.preview_tile_width.setValue(tile_width)
        self.preview_tile_width_input.setValue(tile_width)
        self.preview_tile_height.setValue(tile_height)
        self.preview_tile_height_input.setValue(tile_height)
        self.preview_tile_width_label.setText(f"Tile width: {tile_width}")
        self.preview_tile_height_label.setText(f"Tile height: {tile_height}")
        self.tile_preview.set_tile_size(tile_width, tile_height)
        self._building = False

    def _on_gui_flag_changed(self) -> None:
        if self._building:
            return
        config.update_gui_settings(open_on_startup=self.open_on_startup.isChecked())

    def _on_preview_opacity_changed(self, value: int) -> None:
        if self._building:
            return
        normalized = max(0.0, min(1.0, value / 100.0))
        self.preview_opacity_label.setText(f"Overlay opacity: {value}%")
        self.preview_opacity_input.blockSignals(True)
        self.preview_opacity_input.setValue(value)
        self.preview_opacity_input.blockSignals(False)
        config.update_user_setting("preview_opacity", normalized)

    def _on_preview_opacity_input_changed(self, value: float) -> None:
        if self._building:
            return
        slider_value = int(value)
        self.preview_opacity.blockSignals(True)
        self.preview_opacity.setValue(slider_value)
        self.preview_opacity.blockSignals(False)
        self._on_preview_opacity_changed(slider_value)

    def _set_user_bool(self, key: str, checked: bool) -> None:
        if self._building:
            return
        config.update_user_setting(key, bool(checked))

    def _on_zoom_changed(self, value: int) -> None:
        if self._building:
            return
        zoom = max(100, min(500, int(value)))
        self.hover_zoom_label.setText(f"Hover zoom percent: {zoom}%")
        self.hover_zoom_input.blockSignals(True)
        self.hover_zoom_input.setValue(zoom)
        self.hover_zoom_input.blockSignals(False)
        config.update_user_setting("hover_zoom_percent", zoom)

    def _on_zoom_input_changed(self, value: int) -> None:
        if self._building:
            return
        self.hover_zoom_percent.blockSignals(True)
        self.hover_zoom_percent.setValue(int(value))
        self.hover_zoom_percent.blockSignals(False)
        self._on_zoom_changed(int(value))

    def _on_tile_size_changed(self) -> None:
        if self._building:
            return
        width = max(100, min(500, int(self.preview_tile_width.value())))
        height = max(60, min(500, int(self.preview_tile_height.value())))
        self.preview_tile_width_input.blockSignals(True)
        self.preview_tile_height_input.blockSignals(True)
        self.preview_tile_width_input.setValue(width)
        self.preview_tile_height_input.setValue(height)
        self.preview_tile_width_input.blockSignals(False)
        self.preview_tile_height_input.blockSignals(False)
        self.preview_tile_width_label.setText(f"Tile width: {width}")
        self.preview_tile_height_label.setText(f"Tile height: {height}")
        self.tile_preview.set_tile_size(width, height)
        config.update_user_setting("preview_tile_width", width)
        config.update_user_setting("preview_tile_height", height)

    def _on_tile_width_input_changed(self, value: int) -> None:
        if self._building:
            return
        self.preview_tile_width.blockSignals(True)
        self.preview_tile_width.setValue(int(value))
        self.preview_tile_width.blockSignals(False)
        self._on_tile_size_changed()

    def _on_tile_height_input_changed(self, value: int) -> None:
        if self._building:
            return
        self.preview_tile_height.blockSignals(True)
        self.preview_tile_height.setValue(int(value))
        self.preview_tile_height.blockSignals(False)
        self._on_tile_size_changed()

    def _on_hotkey_changed(self, value: str) -> None:
        if self._building:
            return
        config.update_user_setting("switch_window_hotkey", (value or "MOUSE5").strip() or "MOUSE5")


class AccountsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._running_icon = self._build_status_icon(QColor("#37c77a"))
        self._stopped_icon = self._build_status_icon(QColor("#6b7f94"))
        self._build_ui()
        self.refresh_data()

    def _build_status_icon(self, color: QColor) -> QIcon:
        pixmap = QPixmap(12, 12)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(1, 1, 10, 10)
        painter.end()
        return QIcon(pixmap)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Accounts")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Read-only overview for now. Launch and edit actions come next.")
        subtitle.setObjectName("MutedText")

        root.addWidget(title)
        root.addWidget(subtitle)

        toolbar = QHBoxLayout()
        status_legend = QLabel("Green = running, gray = stopped")
        status_legend.setObjectName("MutedText")
        toolbar.addWidget(status_legend)
        toolbar.addStretch(1)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)
        root.addLayout(toolbar)

        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(["", "Nickname", "Instance", "Username", "Entity ID"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 36)
        root.addWidget(self.table)

    def _collect_running_users(self) -> set[str]:
        users: set[str] = set()
        names = {"steam.exe", "bitcraft.exe"}
        for proc in psutil.process_iter(["name", "username"]):
            try:
                name = (proc.info.get("name") or "").strip().lower()
                if name not in names:
                    continue
                username = (proc.info.get("username") or "").strip().lower()
                if "\\" in username:
                    username = username.split("\\", 1)[1]
                if username:
                    users.add(username)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return users

    def refresh_data(self) -> None:
        state = NativeModeStateManager()
        instances = state.list_instances()
        running_users = self._collect_running_users()

        self.table.setRowCount(len(instances))
        for row, inst in enumerate(instances):
            is_running = inst.local_username.strip().lower() in running_users

            icon_item = QTableWidgetItem("")
            icon_item.setIcon(self._running_icon if is_running else self._stopped_icon)
            self.table.setItem(row, 0, icon_item)

            values = [
                inst.overlay_nickname or inst.instance_id,
                inst.instance_id,
                inst.local_username,
                inst.entity_id,
            ]
            for offset, value in enumerate(values, start=1):
                item = QTableWidgetItem(str(value or ""))
                self.table.setItem(row, offset, item)


class PlaceholderPanel(QWidget):
    def __init__(self, title: str, description: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(8)
        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        desc_label = QLabel(description)
        desc_label.setObjectName("MutedText")
        desc_label.setWordWrap(True)
        root.addWidget(title_label)
        root.addWidget(desc_label)
        root.addStretch(1)


class MainShellWindow(QMainWindow):
    SIDEBAR_EXPANDED_WIDTH = 188
    SIDEBAR_COLLAPSED_WIDTH = 46

    def __init__(self) -> None:
        super().__init__()
        self._panels: list[dict[str, str | QWidget]] = []
        self._panel_index_by_id: dict[str, int] = {}
        self._sidebar_collapsed = False
        self._build_ui()
        self._register_panels()
        self._restore_gui_state()

    def _build_ui(self) -> None:
        self.setWindowTitle("BitCraft Preview")
        self.resize(1180, 760)

        container = QWidget(self)
        self.setCentralWidget(container)

        root = QHBoxLayout(container)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        self.main_surface = QFrame(self)
        self.main_surface.setObjectName("MainSurface")
        main_layout = QHBoxLayout(self.main_surface)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(14)

        self.content_surface = QFrame(self.main_surface)
        self.content_surface.setObjectName("ContentSurface")
        content_layout = QVBoxLayout(self.content_surface)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(10)
        self.content_stack = QStackedWidget(self.content_surface)
        content_layout.addWidget(self.content_stack)

        self.sidebar_surface = QFrame(self.main_surface)
        self.sidebar_surface.setObjectName("SidebarSurface")
        self.sidebar_surface.setMinimumWidth(self.SIDEBAR_COLLAPSED_WIDTH)
        self.sidebar_surface.setMaximumWidth(self.SIDEBAR_EXPANDED_WIDTH)

        sidebar_layout = QVBoxLayout(self.sidebar_surface)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(8)

        top_row = QHBoxLayout()
        self.sidebar_toggle = QPushButton("<")
        self.sidebar_toggle.setObjectName("SidebarToggle")
        self.sidebar_toggle.clicked.connect(self.toggle_sidebar)
        top_row.addStretch(1)
        top_row.addWidget(self.sidebar_toggle)
        top_row.addStretch(1)

        self.sidebar_title = QLabel("Panels")
        self.sidebar_title.setObjectName("SectionTitle")

        self.nav = QListWidget(self.sidebar_surface)
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.nav.setUniformItemSizes(True)
        self.nav.currentRowChanged.connect(self._on_nav_changed)

        self.quick_actions_widget = QWidget(self.sidebar_surface)
        self.quick_actions_widget.setObjectName("QuickActionsStrip")
        quick_actions = QHBoxLayout(self.quick_actions_widget)
        quick_actions.setContentsMargins(0, 0, 0, 0)
        quick_actions.setSpacing(8)

        self.quick_settings_btn = QPushButton()
        self.quick_settings_btn.setObjectName("QuickActionButton")
        self.quick_settings_btn.setToolTip("Open Settings panel")
        self.quick_settings_btn.setStatusTip("Open Settings panel")
        self.quick_settings_btn.setWhatsThis("Quick action 1: opens the Settings panel.")
        self.quick_settings_btn.clicked.connect(lambda: self.show_panel("settings"))

        self.quick_setup_btn = QPushButton()
        self.quick_setup_btn.setObjectName("QuickActionButton")
        self.quick_setup_btn.setToolTip("Open Setup placeholder (future guided multi-step setup flow)")
        self.quick_setup_btn.setStatusTip("Setup is not implemented yet; this opens a placeholder panel")
        self.quick_setup_btn.setWhatsThis(
            "Quick action 2: opens the Setup placeholder panel. "
            "This is reserved for a future guided setup workflow."
        )
        self.quick_setup_btn.clicked.connect(lambda: self.show_panel("setup"))

        self.quick_exit_btn = QPushButton()
        self.quick_exit_btn.setObjectName("QuickActionButton")
        self.quick_exit_btn.setToolTip("Exit BitCraft Preview completely")
        self.quick_exit_btn.setStatusTip("Quit the app fully (tray and overlays will close)")
        self.quick_exit_btn.setWhatsThis("Quick action 3: exits BitCraft Preview completely.")
        self.quick_exit_btn.clicked.connect(QApplication.instance().quit)

        for btn in (self.quick_settings_btn, self.quick_setup_btn, self.quick_exit_btn):
            btn.setFixedHeight(32)
            btn.setFixedWidth(32)
            btn.setIconSize(QSize(20, 20))
            btn.setText("")
            quick_actions.addWidget(btn)

        quick_actions.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._try_apply_quick_action_icons()

        sidebar_layout.addLayout(top_row)
        sidebar_layout.addWidget(self.sidebar_title)
        sidebar_layout.addWidget(self.nav, 1)
        sidebar_layout.addWidget(self.quick_actions_widget, 0)

        main_layout.addWidget(self.content_surface, 1)
        main_layout.addWidget(self.sidebar_surface, 0)

        root.addWidget(self.main_surface, 1)

    def _register_panels(self) -> None:
        self._add_panel("settings", "Settings", SettingsPanel(self))
        self._add_panel(
            "setup",
            "Setup",
            PlaceholderPanel("Setup", "Setup workflow placeholder. This panel will host multi-step account setup in a later iteration.", self),
        )
        self._add_panel("accounts", "Accounts", AccountsPanel(self))
        self._add_panel(
            "monitor",
            "Monitor",
            PlaceholderPanel("Monitor", "Reserved for account activity and API data in a later iteration.", self),
        )
        self._add_panel(
            "updates",
            "Updates",
            PlaceholderPanel("Updates", "Reserved for in-app update notifications.", self),
        )
        self._add_panel(
            "map",
            "Map",
            PlaceholderPanel("Map", "Reserved for location/map visualization of active accounts.", self),
        )

    def _add_panel(self, panel_id: str, title: str, widget: QWidget) -> None:
        index = self.content_stack.addWidget(widget)
        self._panel_index_by_id[panel_id] = index
        self._panels.append({"id": panel_id, "title": title, "widget": widget})

        item = QListWidgetItem(title)
        item.setData(Qt.ItemDataRole.UserRole, panel_id)
        self.nav.addItem(item)

    def _try_apply_quick_action_icons(self) -> None:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = {
            self.quick_settings_btn: os.path.join(base_path, "assets", "icon_settings.png"),
            self.quick_setup_btn: os.path.join(base_path, "assets", "icon_setup.png"),
            self.quick_exit_btn: os.path.join(base_path, "assets", "icon_exit.png"),
        }
        for button, icon_path in candidates.items():
            if os.path.exists(icon_path):
                button.setIcon(QIcon(icon_path))

    def _restore_gui_state(self) -> None:
        settings = config.get_gui_settings()
        self._sidebar_collapsed = bool(settings.get("sidebar_collapsed", False))
        self._apply_sidebar_state(persist=False)

        panel_id = settings.get("last_panel", "settings")
        self.show_panel(str(panel_id))

    def show_panel(self, panel_id: str) -> None:
        target = str(panel_id or "settings").strip().lower()
        if target not in self._panel_index_by_id:
            target = "settings"
        index = self._panel_index_by_id[target]
        self.content_stack.setCurrentIndex(index)
        self.nav.setCurrentRow(index)

    def _on_nav_changed(self, index: int) -> None:
        if index < 0:
            return
        self.content_stack.setCurrentIndex(index)
        item = self.nav.item(index)
        if item is None:
            return
        panel_id = str(item.data(Qt.ItemDataRole.UserRole) or "settings")
        config.update_gui_settings(last_panel=panel_id)

        widget = self.content_stack.currentWidget()
        if isinstance(widget, AccountsPanel):
            widget.refresh_data()

    def toggle_sidebar(self) -> None:
        self._sidebar_collapsed = not self._sidebar_collapsed
        self._apply_sidebar_state(persist=True)

    def _apply_sidebar_state(self, persist: bool) -> None:
        if self._sidebar_collapsed:
            self.sidebar_surface.setMinimumWidth(self.SIDEBAR_COLLAPSED_WIDTH)
            self.sidebar_surface.setMaximumWidth(self.SIDEBAR_COLLAPSED_WIDTH)
            self.sidebar_title.hide()
            self.nav.hide()
            self.quick_actions_widget.hide()
            self.sidebar_toggle.setText(">")
        else:
            self.sidebar_surface.setMinimumWidth(self.SIDEBAR_EXPANDED_WIDTH)
            self.sidebar_surface.setMaximumWidth(self.SIDEBAR_EXPANDED_WIDTH)
            self.sidebar_title.show()
            self.nav.show()
            self.quick_actions_widget.show()
            self.sidebar_toggle.setText("<")

        if persist:
            config.update_gui_settings(sidebar_collapsed=self._sidebar_collapsed)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        # Keep app/tray running when shell window is closed.
        event.ignore()
        self.hide()

    def show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
