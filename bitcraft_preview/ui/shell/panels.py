from __future__ import annotations

import psutil
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bitcraft_preview import config
from bitcraft_preview.native.state_manager import NativeModeStateManager
from bitcraft_preview.ui.shell.widgets import CollapsibleSection, DirectInputSlider, HotkeyCaptureButton, TilePreviewWidget


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
        overlay_layout.setColumnStretch(1, 1)

        self.preview_opacity_name = QLabel("Overlay opacity")
        self.preview_opacity_value = QLabel("80%")
        self.preview_opacity = DirectInputSlider("Overlay opacity", " %", self)
        self.preview_opacity.setRange(0, 100)
        self.preview_opacity.valueChanged.connect(self._on_preview_opacity_changed)
        self._add_inline_slider_row(overlay_layout, 0, self.preview_opacity_name, self.preview_opacity, self.preview_opacity_value)

        self.hide_active_overlay = QCheckBox("Hide active window overlay")
        self.hide_active_overlay.stateChanged.connect(
            lambda: self._set_user_bool("hide_active_window_overlay", self.hide_active_overlay.isChecked())
        )
        overlay_layout.addWidget(self.hide_active_overlay, 1, 0, 1, 3)

        self.hover_zoom_enabled = QCheckBox("Enable hover zoom")
        self.hover_zoom_enabled.stateChanged.connect(
            lambda: self._set_user_bool("hover_zoom_enabled", self.hover_zoom_enabled.isChecked())
        )
        overlay_layout.addWidget(self.hover_zoom_enabled, 2, 0, 1, 3)

        self.hover_zoom_name = QLabel("Hover zoom percent")
        self.hover_zoom_value = QLabel("200%")
        self.hover_zoom_percent = DirectInputSlider("Hover zoom percent", " %", self)
        self.hover_zoom_percent.setRange(100, 500)
        self.hover_zoom_percent.valueChanged.connect(self._on_zoom_changed)
        self._add_inline_slider_row(overlay_layout, 3, self.hover_zoom_name, self.hover_zoom_percent, self.hover_zoom_value)

        self.preview_tile_width_name = QLabel("Tile width")
        self.preview_tile_width_value = QLabel("300")
        self.preview_tile_width = DirectInputSlider("Tile width", " px", self)
        self.preview_tile_width.setRange(100, 500)
        self.preview_tile_width.valueChanged.connect(self._on_tile_size_changed)
        self._add_inline_slider_row(overlay_layout, 4, self.preview_tile_width_name, self.preview_tile_width, self.preview_tile_width_value)

        self.preview_tile_height_name = QLabel("Tile height")
        self.preview_tile_height_value = QLabel("200")
        self.preview_tile_height = DirectInputSlider("Tile height", " px", self)
        self.preview_tile_height.setRange(60, 500)
        self.preview_tile_height.valueChanged.connect(self._on_tile_size_changed)
        self._add_inline_slider_row(overlay_layout, 5, self.preview_tile_height_name, self.preview_tile_height, self.preview_tile_height_value)

        self.tile_preview = TilePreviewWidget(self)
        overlay_layout.addWidget(self.tile_preview, 6, 0, 1, 3)

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

    def _add_inline_slider_row(self, layout: QGridLayout, row: int, name_label: QLabel, slider: QSlider, value_label: QLabel) -> None:
        name_label.setObjectName("MutedText")
        value_label.setObjectName("MutedText")
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value_label.setMinimumWidth(56)
        slider.setFixedHeight(18)
        layout.addWidget(name_label, row, 0)
        layout.addWidget(slider, row, 1)
        layout.addWidget(value_label, row, 2)

    def _load_values(self) -> None:
        self._building = True
        cfg = config.load_config()
        user = cfg.get("UserSettings", {})
        gui = config.get_gui_settings()

        self.open_on_startup.setChecked(gui.get("open_on_startup", False))

        opacity = max(0.0, min(1.0, float(user.get("preview_opacity", 0.8))))
        self.preview_opacity.setValue(int(opacity * 100))
        self.preview_opacity_value.setText(f"{int(opacity * 100)}%")

        self.hover_zoom_enabled.setChecked(bool(user.get("hover_zoom_enabled", True)))
        hover_zoom = max(100, min(500, int(user.get("hover_zoom_percent", 200))))
        self.hover_zoom_percent.setValue(hover_zoom)
        self.hover_zoom_value.setText(f"{hover_zoom}%")

        self.hide_active_overlay.setChecked(bool(user.get("hide_active_window_overlay", False)))
        self.switch_window_enabled.setChecked(bool(user.get("switch_window_enabled", True)))

        hotkey = str(user.get("switch_window_hotkey", "MOUSE5") or "MOUSE5")
        self.switch_window_hotkey.set_hotkey(hotkey)

        tile_width = max(100, min(500, int(user.get("preview_tile_width", 300))))
        tile_height = max(60, min(500, int(user.get("preview_tile_height", 200))))
        self.preview_tile_width.setValue(tile_width)
        self.preview_tile_height.setValue(tile_height)
        self.preview_tile_width_value.setText(str(tile_width))
        self.preview_tile_height_value.setText(str(tile_height))
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
        self.preview_opacity_value.setText(f"{value}%")
        config.update_user_setting("preview_opacity", normalized)

    def _set_user_bool(self, key: str, checked: bool) -> None:
        if self._building:
            return
        config.update_user_setting(key, bool(checked))

    def _on_zoom_changed(self, value: int) -> None:
        if self._building:
            return
        zoom = max(100, min(500, int(value)))
        self.hover_zoom_value.setText(f"{zoom}%")
        config.update_user_setting("hover_zoom_percent", zoom)

    def _on_tile_size_changed(self) -> None:
        if self._building:
            return
        width = max(100, min(500, int(self.preview_tile_width.value())))
        height = max(60, min(500, int(self.preview_tile_height.value())))
        self.preview_tile_width_value.setText(str(width))
        self.preview_tile_height_value.setText(str(height))
        self.tile_preview.set_tile_size(width, height)
        config.update_user_setting("preview_tile_width", width)
        config.update_user_setting("preview_tile_height", height)

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
