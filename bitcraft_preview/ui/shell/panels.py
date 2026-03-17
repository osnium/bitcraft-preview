from __future__ import annotations

import os
import time
import psutil
from PySide6.QtCore import QEvent, QSize, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from bitcraft_preview import config
from bitcraft_preview.assets import get_asset_path
from bitcraft_preview.native.process_control import NativeProcessController
from bitcraft_preview.native.state_manager import NativeModeStateManager
from bitcraft_preview.ui.shell.accounts import (
    AccountRowState,
    AccountRowWidget,
    AccountsSelectionController,
    build_instance_update_payload,
    resolve_account_display_name,
    resolve_bulk_launch_targets,
)
from bitcraft_preview.ui.shell.widgets import CollapsibleSection, DirectInputSlider, HotkeyCaptureButton, TilePreviewWidget


class SettingsPanel(QWidget):
    live_setting_changed = Signal(str)

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
        self.live_setting_changed.emit("preview_opacity")

    def _set_user_bool(self, key: str, checked: bool) -> None:
        if self._building:
            return
        config.update_user_setting(key, bool(checked))
        self.live_setting_changed.emit(key)

    def _on_zoom_changed(self, value: int) -> None:
        if self._building:
            return
        zoom = max(100, min(500, int(value)))
        self.hover_zoom_value.setText(f"{zoom}%")
        config.update_user_setting("hover_zoom_percent", zoom)
        self.live_setting_changed.emit("hover_zoom_percent")

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
        self.live_setting_changed.emit("preview_tile_size")

    def _on_hotkey_changed(self, value: str) -> None:
        if self._building:
            return
        config.update_user_setting("switch_window_hotkey", (value or "MOUSE5").strip() or "MOUSE5")
        self.live_setting_changed.emit("switch_window_hotkey")


class AccountsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = NativeModeStateManager()
        self._controller = NativeProcessController(state=self._state)
        self._selection = AccountsSelectionController()
        self._row_widgets: dict[str, AccountRowWidget] = {}
        self._ordered_instance_ids: list[str] = []
        self._instances_by_id: dict[str, object] = {}
        self._busy_rows: set[str] = set()
        self._row_action_timers: dict[str, QTimer] = {}
        self._pending_target_running: dict[str, bool] = {}
        self._pending_action_kind: dict[str, str] = {}
        self._min_complete_after: dict[str, float] = {}
        self._row_progress_message: dict[str, str] = {}
        self._row_action_timeout_ms = 30000
        self._watch_timer = QTimer(self)
        self._watch_timer.setInterval(900)
        self._watch_timer.timeout.connect(self._poll_row_actions)
        self._running_icon = self._build_status_icon(QColor("#37c77a"))
        self._stopped_icon = self._build_status_icon(QColor("#6b7f94"))
        self._launch_icon = self._load_account_action_icon("account_launch.png", self._build_launch_icon)
        self._restart_icon = self._load_account_action_icon("account_restart.png", self._build_restart_icon)
        self._kill_icon = self._load_account_action_icon("account_kill.png", self._build_kill_icon)
        self._build_ui()
        self.refresh_data()

    def _asset_path(self, *parts: str) -> str:
        return get_asset_path(*parts)

    def _load_account_action_icon(self, filename: str, fallback_builder) -> QIcon:
        path = self._asset_path("icons", "ui", filename)
        if os.path.exists(path):
            icon = QIcon(path)
            if not icon.isNull():
                return icon
        return fallback_builder()

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

    def _build_launch_icon(self) -> QIcon:
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#9cd6ff"))
        path = QPainterPath()
        path.moveTo(6.5, 4.0)
        path.lineTo(15.2, 10.0)
        path.lineTo(6.5, 16.0)
        path.closeSubpath()
        painter.drawPath(path)
        painter.end()
        return QIcon(pixmap)

    def _build_restart_icon(self) -> QIcon:
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#9cd6ff"), 1.9)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Draw a near-full circular arc and a larger arrowhead so it reads clearly as restart.
        painter.drawArc(3, 3, 14, 14, 34 * 16, 310 * 16)

        head = QPainterPath()
        head.moveTo(14.6, 2.9)
        head.lineTo(18.2, 4.0)
        head.lineTo(16.0, 7.2)
        head.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#9cd6ff"))
        painter.drawPath(head)
        painter.end()
        return QIcon(pixmap)

    def _build_kill_icon(self) -> QIcon:
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#ff9c9c"), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(6.0, 6.0, 14.0, 14.0)
        painter.drawLine(14.0, 6.0, 6.0, 14.0)
        painter.end()
        return QIcon(pixmap)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Accounts")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Manage native accounts, launch state, and instance metadata.")
        subtitle.setObjectName("MutedText")
        subtitle.setToolTip("Ctrl+Click to select multiple accounts.")

        root.addWidget(title)
        root.addWidget(subtitle)

        toolbar = QHBoxLayout()
        edit_hint = QLabel("Tip: Right-click an account -> Edit")
        edit_hint.setObjectName("MutedText")
        edit_hint.setToolTip("Right-click any account row and choose Edit to update nickname and entity ID.")
        toolbar.addWidget(edit_hint)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        self.accounts_scroll = QScrollArea(self)
        self.accounts_scroll.setWidgetResizable(True)
        self.accounts_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.accounts_scroll.viewport().installEventFilter(self)

        self.accounts_container = QWidget(self.accounts_scroll)
        self.accounts_container.installEventFilter(self)
        self.accounts_layout = QVBoxLayout(self.accounts_container)
        self.accounts_layout.setContentsMargins(0, 0, 0, 0)
        self.accounts_layout.setSpacing(8)
        self.accounts_scroll.setWidget(self.accounts_container)
        root.addWidget(self.accounts_scroll, 1)

        self.empty_state = QPushButton("No accounts set up. Click here for Setup.", self)
        self.empty_state.setObjectName("AccountsEmptyState")
        self.empty_state.clicked.connect(self._show_setup_panel)
        self.accounts_layout.addWidget(self.empty_state)
        self.accounts_layout.addStretch(1)

        self.feedback_label = QLabel("", self)
        self.feedback_label.setObjectName("AccountFeedback")
        self.feedback_label.hide()
        root.addWidget(self.feedback_label)

        divider = QFrame(self)
        divider.setObjectName("SectionDivider")
        root.addWidget(divider)

        footer = QWidget(self)
        footer.setObjectName("AccountsFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(24)

        launch_column = QVBoxLayout()
        launch_column.setContentsMargins(0, 0, 0, 0)
        launch_column.setSpacing(6)
        self.bulk_launch_label = QLabel("Launch All", footer)
        self.bulk_launch_label.setObjectName("MutedText")
        self.bulk_launch_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.bulk_launch_label.setMinimumWidth(118)
        launch_column.addWidget(self.bulk_launch_label, 0, Qt.AlignmentFlag.AlignHCenter)
        self.bulk_launch_button = QPushButton(footer)
        self.bulk_launch_button.setObjectName("AccountFooterButton")
        self.bulk_launch_button.setFixedSize(40, 40)
        self.bulk_launch_button.setIcon(self._launch_icon)
        self.bulk_launch_button.setIconSize(QSize(20, 20))
        self.bulk_launch_button.setToolTip("Launch all accounts, or only the selected accounts when a selection exists.")
        self.bulk_launch_button.clicked.connect(self._handle_bulk_launch)
        launch_column.addWidget(self.bulk_launch_button, 0, Qt.AlignmentFlag.AlignHCenter)

        kill_column = QVBoxLayout()
        kill_column.setContentsMargins(0, 0, 0, 0)
        kill_column.setSpacing(6)
        self.bulk_kill_label = QLabel("Kill All", footer)
        self.bulk_kill_label.setObjectName("MutedText")
        self.bulk_kill_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.bulk_kill_label.setMinimumWidth(118)
        kill_column.addWidget(self.bulk_kill_label, 0, Qt.AlignmentFlag.AlignHCenter)
        self.bulk_kill_button = QPushButton(footer)
        self.bulk_kill_button.setObjectName("AccountFooterButton")
        self.bulk_kill_button.setFixedSize(40, 40)
        self.bulk_kill_button.setIcon(self._kill_icon)
        self.bulk_kill_button.setIconSize(QSize(20, 20))
        self.bulk_kill_button.setToolTip("Kill all configured accounts.")
        self.bulk_kill_button.clicked.connect(self._handle_kill_all)
        kill_column.addWidget(self.bulk_kill_button, 0, Qt.AlignmentFlag.AlignHCenter)

        footer_layout.addLayout(launch_column)
        footer_layout.addStretch(1)
        footer_layout.addLayout(kill_column)
        root.addWidget(footer)

    def _collect_running_processes_by_user(self) -> dict[str, set[str]]:
        running: dict[str, set[str]] = {}
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
                    running.setdefault(username, set()).add(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return running

    def _is_instance_running(self, instance, running_processes_by_user: dict[str, set[str]]) -> bool:
        username = (getattr(instance, "local_username", "") or "").strip().lower()
        if not username:
            return False
        return bool(running_processes_by_user.get(username))

    def _update_row_visual_state(self, instance_id: str, running_processes_by_user: dict[str, set[str]]) -> None:
        row = self._row_widgets.get(instance_id)
        instance = self._instances_by_id.get(instance_id)
        if row is None or instance is None:
            return
        row_state = AccountRowState(
            instance_id=instance.instance_id,
            local_username=instance.local_username,
            display_name=resolve_account_display_name(instance),
            entity_id=instance.entity_id,
            is_running=self._is_instance_running(instance, running_processes_by_user),
        )
        row._status_icon = self._running_icon if row_state.is_running else self._stopped_icon
        row.update_state(row_state)

    def eventFilter(self, watched, event) -> bool:  # type: ignore[override]
        if watched in {self.accounts_scroll.viewport(), self.accounts_container} and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                child = watched.childAt(event.position().toPoint())
                if self._find_row_widget(child) is None:
                    self._selection.clear()
                    self._sync_selection_state()
        return super().eventFilter(watched, event)

    def _find_row_widget(self, child: QWidget | None) -> AccountRowWidget | None:
        current = child
        while current is not None and current is not self.accounts_container:
            if isinstance(current, AccountRowWidget):
                return current
            current = current.parentWidget()
        return None

    def _clear_account_rows(self) -> None:
        for index in reversed(range(self.accounts_layout.count())):
            item = self.accounts_layout.takeAt(index)
            widget = item.widget()
            if widget is None:
                continue
            if widget is self.empty_state:
                # Keep the empty-state button alive across refreshes.
                widget.setParent(self)
                continue
            widget.deleteLater()

    def _set_feedback(self, message: str, *, error: bool = False) -> None:
        self.feedback_label.setProperty("error", error)
        self.feedback_label.setText(message)
        self.feedback_label.style().unpolish(self.feedback_label)
        self.feedback_label.style().polish(self.feedback_label)
        self.feedback_label.setVisible(bool(message))

    def _sync_selection_state(self) -> None:
        selected_ids = self._selection.selected_ids
        for instance_id, row_widget in self._row_widgets.items():
            row_widget.set_selected(instance_id in selected_ids)
        self.bulk_launch_label.setText("Launch Selected" if len(selected_ids) >= 2 else "Launch All")

    def _sync_action_enabled_state(self) -> None:
        has_accounts = bool(self._ordered_instance_ids)
        self.bulk_launch_button.setEnabled(has_accounts)
        self.bulk_kill_button.setEnabled(has_accounts)
        for instance_id, row_widget in self._row_widgets.items():
            row_widget.set_actions_enabled(instance_id not in self._busy_rows)

    def _show_setup_panel(self) -> None:
        shell = self.window()
        if hasattr(shell, "show_panel"):
            shell.show_panel("setup", sync_nav=False)

    def _get_row_action_timer(self, instance_id: str) -> QTimer:
        timer = self._row_action_timers.get(instance_id)
        if timer is not None:
            return timer
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda iid=instance_id: self._on_row_action_timeout(iid))
        self._row_action_timers[instance_id] = timer
        return timer

    def _start_row_action(
        self,
        instance_id: str,
        in_progress: str,
        *,
        action_kind: str,
        expected_running: bool,
        min_complete_delay_s: float = 0.0,
    ) -> None:
        self._busy_rows.add(instance_id)
        self._pending_action_kind[instance_id] = action_kind
        self._pending_target_running[instance_id] = expected_running
        self._min_complete_after[instance_id] = time.monotonic() + max(0.0, min_complete_delay_s)
        self._row_progress_message[instance_id] = in_progress
        timer = self._get_row_action_timer(instance_id)
        timer.start(self._row_action_timeout_ms)

        row = self._row_widgets.get(instance_id)
        if row is not None:
            row.show_action_in_progress(in_progress)

        self._sync_action_enabled_state()
        if not self._watch_timer.isActive():
            self._watch_timer.start()

    def _finish_row_action(
        self,
        instance_id: str,
        message: str,
        *,
        error: bool = False,
        running_processes_by_user: dict[str, set[str]] | None = None,
    ) -> None:
        timer = self._row_action_timers.get(instance_id)
        if timer is not None:
            timer.stop()

        self._busy_rows.discard(instance_id)
        self._pending_action_kind.pop(instance_id, None)
        self._pending_target_running.pop(instance_id, None)
        self._min_complete_after.pop(instance_id, None)
        self._row_progress_message.pop(instance_id, None)

        if running_processes_by_user is None:
            running_processes_by_user = self._collect_running_processes_by_user()
        self._update_row_visual_state(instance_id, running_processes_by_user)
        row = self._row_widgets.get(instance_id)
        if row is not None:
            row.show_action_result(message, error=error)

        if error:
            self._set_feedback(f"{instance_id}: {message}", error=True)

        self._sync_action_enabled_state()
        if not self._pending_target_running and self._watch_timer.isActive():
            self._watch_timer.stop()

    def _on_row_action_timeout(self, instance_id: str) -> None:
        if instance_id not in self._busy_rows:
            return
        action_kind = self._pending_action_kind.get(instance_id, "")
        if action_kind in {"start", "restart"}:
            timeout_message = "Timed out waiting for BitCraft process."
        else:
            timeout_message = "Timed out waiting for account to close."
        self._finish_row_action(instance_id, timeout_message, error=True)

    def _poll_row_actions(self) -> None:
        if not self._pending_target_running:
            self._watch_timer.stop()
            return

        running_processes_by_user = self._collect_running_processes_by_user()
        now = time.monotonic()
        completed: list[tuple[str, str]] = []

        for instance_id, desired_running in list(self._pending_target_running.items()):
            if instance_id not in self._busy_rows:
                continue
            instance = self._instances_by_id.get(instance_id)
            if instance is None:
                continue
            username = (getattr(instance, "local_username", "") or "").strip().lower()
            if not username:
                continue
            processes = running_processes_by_user.get(username, set())
            has_steam = "steam.exe" in processes
            has_bitcraft = "bitcraft.exe" in processes
            is_running = bool(processes)
            if now < self._min_complete_after.get(instance_id, 0.0):
                continue

            action_kind = self._pending_action_kind.get(instance_id, "")
            if desired_running:
                if has_bitcraft:
                    completed.append((instance_id, "Game started."))
                    continue
                if has_steam:
                    progress_message = "Steam started, waiting for game..."
                    if self._row_progress_message.get(instance_id) != progress_message:
                        self._row_progress_message[instance_id] = progress_message
                        row = self._row_widgets.get(instance_id)
                        if row is not None:
                            row.show_action_in_progress(progress_message)
                continue

            if not is_running:
                completed.append((instance_id, "Account closed."))

        for instance_id, message in completed:
            self._finish_row_action(instance_id, message, running_processes_by_user=running_processes_by_user)

    def _handle_row_clicked(self, instance_id: str, ctrl_pressed: bool) -> None:
        self._selection.click(instance_id, ctrl_pressed)
        self._sync_selection_state()

    def _handle_primary_action(self, instance_id: str) -> None:
        if instance_id in self._busy_rows:
            return
        row = self._row_widgets.get(instance_id)
        if row is None:
            return
        is_restart = row._row_state.is_running
        message = "Restarting account..." if is_restart else "Starting account..."
        try:
            if is_restart:
                self._controller.restart_instance(instance_id)
            else:
                self._controller.launch_instance(instance_id)
        except Exception as exc:
            row.show_action_result(str(exc), error=True)
            self._set_feedback(str(exc), error=True)
            return
        self._start_row_action(
            instance_id,
            message,
            action_kind="restart" if is_restart else "start",
            expected_running=True,
            # Restarts can report running throughout process recycle; wait briefly before completion checks.
            min_complete_delay_s=3.0 if is_restart else 0.4,
        )

    def _handle_kill_action(self, instance_id: str) -> None:
        if instance_id in self._busy_rows:
            return
        self._start_row_action(
            instance_id,
            "Closing account...",
            action_kind="kill",
            expected_running=False,
            min_complete_delay_s=0.2,
        )
        try:
            self._controller.force_kill_instance_processes(instance_id, timeout=10.0)
        except Exception as exc:
            self._finish_row_action(instance_id, str(exc), error=True)
            return

    def _handle_bulk_launch(self) -> None:
        targets = resolve_bulk_launch_targets(self._ordered_instance_ids, self._selection.selected_ids)
        if not targets:
            return

        available_targets = [instance_id for instance_id in targets if instance_id not in self._busy_rows]
        if not available_targets:
            self._set_feedback("Selected accounts are already running an action.", error=True)
            return

        errors: list[str] = []
        successes = 0
        for instance_id in available_targets:
            try:
                self._controller.launch_or_restart(instance_id)
                successes += 1
                row = self._row_widgets.get(instance_id)
                is_restart = bool(row and row._row_state.is_running)
                self._start_row_action(
                    instance_id,
                    "Restarting account..." if is_restart else "Starting account...",
                    action_kind="restart" if is_restart else "start",
                    expected_running=True,
                    min_complete_delay_s=3.0 if is_restart else 0.4,
                )
            except Exception as exc:
                errors.append(f"{instance_id}: {exc}")

        if successes:
            if errors:
                self._set_feedback("Some actions failed: " + " | ".join(errors), error=True)
            else:
                self._set_feedback("")
            return
        self._set_feedback(" | ".join(errors) or "No accounts available to launch.", error=True)

    def _handle_kill_all(self) -> None:
        if not self._ordered_instance_ids:
            return
        running_processes_by_user = self._collect_running_processes_by_user()
        running_targets = [
            instance_id
            for instance_id in self._ordered_instance_ids
            if instance_id not in self._busy_rows
            and (instance := self._instances_by_id.get(instance_id)) is not None
            and self._is_instance_running(instance, running_processes_by_user)
        ]
        if not running_targets:
            self._set_feedback("No running accounts to close.")
            return

        errors: list[str] = []
        processed = 0
        for instance_id in running_targets:
            self._start_row_action(
                instance_id,
                "Closing account...",
                action_kind="kill",
                expected_running=False,
                min_complete_delay_s=0.2,
            )
            try:
                self._controller.force_kill_instance_processes(instance_id, timeout=10.0)
                processed += 1
            except Exception as exc:
                self._finish_row_action(instance_id, str(exc), error=True)
                errors.append(f"{instance_id}: {exc}")

        if errors:
            self._set_feedback("Some actions failed: " + " | ".join(errors), error=True)
        elif processed:
            self._set_feedback("")

    def _handle_metadata_submitted(self, instance_id: str, nickname: str, entity_id: str) -> None:
        instance = self._state.get_instance(instance_id)
        if instance is None:
            self._set_feedback(f"Unknown account: {instance_id}", error=True)
            return
        payload = build_instance_update_payload(instance, nickname, entity_id)
        self._state.upsert_instance(**payload)
        self.refresh_data()
        self._set_feedback("Account metadata updated.")

    def refresh_data(self) -> None:
        instances = self._state.list_instances()
        running_processes_by_user = self._collect_running_processes_by_user()
        self._ordered_instance_ids = [inst.instance_id for inst in instances]
        self._instances_by_id = {inst.instance_id: inst for inst in instances}
        valid_ids = set(self._ordered_instance_ids)
        self._selection.retain(set(self._ordered_instance_ids))

        stale_busy = self._busy_rows - valid_ids
        for instance_id in stale_busy:
            self._busy_rows.discard(instance_id)
            self._pending_action_kind.pop(instance_id, None)
            self._pending_target_running.pop(instance_id, None)
            self._min_complete_after.pop(instance_id, None)
            self._row_progress_message.pop(instance_id, None)
            timer = self._row_action_timers.get(instance_id)
            if timer is not None:
                timer.stop()

        self._clear_account_rows()
        self._row_widgets = {}

        if not instances:
            self.empty_state.show()
            self.accounts_layout.addWidget(self.empty_state)
        else:
            self.empty_state.hide()
            for inst in instances:
                row_state = AccountRowState(
                    instance_id=inst.instance_id,
                    local_username=inst.local_username,
                    display_name=resolve_account_display_name(inst),
                    entity_id=inst.entity_id,
                    is_running=self._is_instance_running(inst, running_processes_by_user),
                )
                row_widget = AccountRowWidget(
                    row_state,
                    status_icon=self._running_icon if row_state.is_running else self._stopped_icon,
                    launch_icon=self._launch_icon,
                    restart_icon=self._restart_icon,
                    kill_icon=self._kill_icon,
                    parent=self.accounts_container,
                )
                row_widget.row_clicked.connect(self._handle_row_clicked)
                row_widget.primary_requested.connect(self._handle_primary_action)
                row_widget.kill_requested.connect(self._handle_kill_action)
                row_widget.metadata_submitted.connect(self._handle_metadata_submitted)
                if inst.instance_id in self._busy_rows:
                    progress_message = self._row_progress_message.get(inst.instance_id)
                    if progress_message:
                        row_widget.show_action_in_progress(progress_message)
                self._row_widgets[inst.instance_id] = row_widget
                self.accounts_layout.addWidget(row_widget)

        self.accounts_layout.addStretch(1)
        self._sync_selection_state()
        self._sync_action_enabled_state()


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
