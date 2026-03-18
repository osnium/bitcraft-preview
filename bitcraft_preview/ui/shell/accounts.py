from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QContextMenuEvent, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bitcraft_preview.native.state_manager import NativeInstance


@dataclass(frozen=True)
class AccountRowState:
    instance_id: str
    local_username: str
    display_name: str
    entity_id: str
    is_running: bool


class AccountsSelectionController:
    def __init__(self) -> None:
        self._selected_ids: set[str] = set()

    @property
    def selected_ids(self) -> set[str]:
        return set(self._selected_ids)

    def click(self, instance_id: str, ctrl_pressed: bool) -> set[str]:
        if ctrl_pressed:
            if instance_id in self._selected_ids:
                self._selected_ids.remove(instance_id)
            else:
                self._selected_ids.add(instance_id)
        else:
            self._selected_ids = {instance_id}
        return self.selected_ids

    def clear(self) -> set[str]:
        self._selected_ids.clear()
        return self.selected_ids

    def retain(self, valid_ids: set[str]) -> set[str]:
        self._selected_ids.intersection_update(valid_ids)
        return self.selected_ids


def resolve_account_display_name(instance: NativeInstance) -> str:
    nickname = (instance.overlay_nickname or "").strip()
    return nickname or instance.instance_id


def resolve_account_subtitle(instance: NativeInstance) -> str:
    parts = [instance.instance_id]
    entity_id = (instance.entity_id or "").strip()
    if entity_id:
        parts.append(f"Entity: {entity_id}")
    return " | ".join(parts)


def resolve_bulk_launch_targets(all_instance_ids: list[str], selected_ids: set[str]) -> list[str]:
    if len(selected_ids) < 2:
        return list(all_instance_ids)
    return [instance_id for instance_id in all_instance_ids if instance_id in selected_ids]


def build_instance_update_payload(instance: NativeInstance, nickname: str, entity_id: str) -> dict[str, str | int | None]:
    return {
        "instance_id": instance.instance_id,
        "local_username": instance.local_username,
        "plain_password": None,
        "steam_account_name": instance.steam_account_name,
        "entity_id": entity_id.strip(),
        "overlay_nickname": nickname.strip(),
        "local_user_sid": instance.local_user_sid,
        "instance_root": instance.instance_root,
        "steam_exe_path": instance.steam_exe_path,
        "steamapps_link_path": instance.steamapps_link_path,
        "steamapps_link_target": instance.steamapps_link_target,
        "tile_position_x": instance.tile_position_x,
        "tile_position_y": instance.tile_position_y,
        "status": instance.status,
    }


class AccountRowWidget(QFrame):
    row_clicked = Signal(str, bool)
    primary_requested = Signal(str)
    kill_requested = Signal(str)
    metadata_submitted = Signal(str, str, str)

    def __init__(
        self,
        row_state: AccountRowState,
        *,
        status_icon: QIcon,
        launch_icon: QIcon,
        restart_icon: QIcon,
        kill_icon: QIcon,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._row_state = row_state
        self._status_icon = status_icon
        self._launch_icon = launch_icon
        self._restart_icon = restart_icon
        self._kill_icon = kill_icon
        self._status_hide_timer = QTimer(self)
        self._status_hide_timer.setSingleShot(True)
        self._status_hide_timer.timeout.connect(self._start_status_fade)
        self._editor_focus_field = "nickname"
        self._build_ui()
        self.update_state(row_state)
        self.set_selected(False)
        self.set_actions_enabled(True)

    @property
    def instance_id(self) -> str:
        return self._row_state.instance_id

    def _build_ui(self) -> None:
        self.setObjectName("AccountRow")
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 7, 8, 7)
        root.setSpacing(5)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(10)

        self.status_label = QLabel(self)
        self.status_label.setObjectName("AccountStatusDot")
        self.status_label.setFixedWidth(16)
        top.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignVCenter)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.display_label = QLabel(self)
        self.display_label.setObjectName("AccountDisplayName")
        text_layout.addWidget(self.display_label)

        self.subtitle_label = QLabel(self)
        self.subtitle_label.setObjectName("MutedText")
        text_layout.addWidget(self.subtitle_label)

        top.addLayout(text_layout, 1)

        self.primary_button = QPushButton(self)
        self.primary_button.setObjectName("AccountActionButton")
        self.primary_button.setFixedSize(30, 30)
        self.primary_button.clicked.connect(lambda: self.primary_requested.emit(self.instance_id))
        top.addWidget(self.primary_button, 0, Qt.AlignmentFlag.AlignCenter)

        self.kill_button = QPushButton(self)
        self.kill_button.setObjectName("AccountActionButton")
        self.kill_button.setFixedSize(30, 30)
        self.kill_button.clicked.connect(lambda: self.kill_requested.emit(self.instance_id))
        top.addWidget(self.kill_button, 0, Qt.AlignmentFlag.AlignCenter)

        root.addLayout(top)

        self.action_status_label = QLabel(self)
        self.action_status_label.setObjectName("AccountRowStatus")
        self.action_status_label.hide()
        self._status_opacity = QGraphicsOpacityEffect(self.action_status_label)
        self.action_status_label.setGraphicsEffect(self._status_opacity)
        self._status_fade_animation = QPropertyAnimation(self._status_opacity, b"opacity", self)
        self._status_fade_animation.setDuration(450)
        self._status_fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._status_fade_animation.finished.connect(self._on_status_fade_finished)
        root.addWidget(self.action_status_label)

        self.editor_frame = QFrame(self)
        self.editor_frame.setObjectName("AccountInlineEditor")
        self.editor_frame.setMaximumHeight(0)
        self._editor_full_height = 0
        self._editor_opacity = QGraphicsOpacityEffect(self.editor_frame)
        self.editor_frame.setGraphicsEffect(self._editor_opacity)
        self._editor_opacity.setOpacity(0.0)

        editor_layout = QVBoxLayout(self.editor_frame)
        editor_layout.setContentsMargins(8, 8, 8, 8)
        editor_layout.setSpacing(6)

        self.nickname_edit = QLineEdit(self.editor_frame)
        self.nickname_edit.setPlaceholderText("Nickname")
        editor_layout.addWidget(self.nickname_edit)

        self.entity_id_edit = QLineEdit(self.editor_frame)
        self.entity_id_edit.setPlaceholderText("Entity ID")
        editor_layout.addWidget(self.entity_id_edit)

        editor_actions = QHBoxLayout()
        editor_actions.setContentsMargins(0, 0, 0, 0)
        editor_actions.setSpacing(6)

        self.save_button = QPushButton("Save", self.editor_frame)
        self.save_button.setObjectName("AccountInlineButton")
        self.save_button.clicked.connect(self._submit_metadata)
        editor_actions.addWidget(self.save_button)

        self.cancel_button = QPushButton("Cancel", self.editor_frame)
        self.cancel_button.setObjectName("AccountInlineButton")
        self.cancel_button.clicked.connect(self.hide_editor)
        editor_actions.addWidget(self.cancel_button)
        editor_actions.addStretch(1)
        editor_layout.addLayout(editor_actions)

        root.addWidget(self.editor_frame)

        self._editor_height_anim = QPropertyAnimation(self.editor_frame, b"maximumHeight", self)
        self._editor_height_anim.setDuration(140)
        self._editor_height_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._editor_height_anim.finished.connect(self._on_editor_height_animation_finished)

        self._editor_opacity_anim = QPropertyAnimation(self._editor_opacity, b"opacity", self)
        self._editor_opacity_anim.setDuration(120)
        self._editor_opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def update_state(self, row_state: AccountRowState) -> None:
        self._row_state = row_state
        self.status_label.setPixmap(self._status_icon.pixmap(12, 12))
        self.display_label.setText(row_state.display_name)
        subtitle = row_state.instance_id
        entity_id = row_state.entity_id.strip()
        if entity_id:
            subtitle = f"{subtitle} | Entity: {entity_id}"
        self.subtitle_label.setText(subtitle)

        if row_state.is_running:
            self.primary_button.setIcon(self._restart_icon)
            self.primary_button.setToolTip("Restart account")
        else:
            self.primary_button.setIcon(self._launch_icon)
            self.primary_button.setToolTip("Start account")
        self.primary_button.setIconSize(QSize(18, 18))
        self.kill_button.setIcon(self._kill_icon)
        self.kill_button.setToolTip("Kill account")
        self.kill_button.setIconSize(QSize(18, 18))
        self.nickname_edit.setText(row_state.display_name if row_state.display_name != row_state.instance_id else "")
        self.entity_id_edit.setText(row_state.entity_id)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def set_actions_enabled(self, enabled: bool) -> None:
        self.primary_button.setEnabled(enabled)
        self.kill_button.setEnabled(enabled)
        self.save_button.setEnabled(enabled)
        self.cancel_button.setEnabled(enabled)

    def show_action_in_progress(self, message: str) -> None:
        self._status_hide_timer.stop()
        self._status_fade_animation.stop()
        self.action_status_label.setProperty("error", False)
        self.action_status_label.setText(message)
        self.action_status_label.style().unpolish(self.action_status_label)
        self.action_status_label.style().polish(self.action_status_label)
        self._status_opacity.setOpacity(1.0)
        self.action_status_label.show()

    def show_action_result(self, message: str, *, error: bool = False) -> None:
        self._status_hide_timer.stop()
        self._status_fade_animation.stop()
        self.action_status_label.setProperty("error", error)
        self.action_status_label.setText(message)
        self.action_status_label.style().unpolish(self.action_status_label)
        self.action_status_label.style().polish(self.action_status_label)
        self._status_opacity.setOpacity(1.0)
        self.action_status_label.show()
        self._status_hide_timer.start(3500 if error else 2200)

    def _start_status_fade(self) -> None:
        self._status_fade_animation.stop()
        self._status_fade_animation.setStartValue(1.0)
        self._status_fade_animation.setEndValue(0.0)
        self._status_fade_animation.start()

    def _on_status_fade_finished(self) -> None:
        if self._status_opacity.opacity() > 0.0:
            return
        self.action_status_label.hide()
        self.action_status_label.setText("")
        self.action_status_label.setProperty("error", False)
        self.action_status_label.style().unpolish(self.action_status_label)
        self.action_status_label.style().polish(self.action_status_label)

    def show_editor(self, focus_field: str) -> None:
        self._editor_focus_field = focus_field
        self.editor_frame.show()
        self._editor_full_height = max(self.editor_frame.sizeHint().height(), 78)
        self._editor_height_anim.stop()
        self._editor_opacity_anim.stop()

        self._editor_height_anim.setStartValue(self.editor_frame.maximumHeight())
        self._editor_height_anim.setEndValue(self._editor_full_height)
        self._editor_opacity_anim.setStartValue(self._editor_opacity.opacity())
        self._editor_opacity_anim.setEndValue(1.0)

        self._editor_height_anim.start()
        self._editor_opacity_anim.start()

        if focus_field == "entity_id":
            self.entity_id_edit.setFocus()
            self.entity_id_edit.selectAll()
        else:
            self.nickname_edit.setFocus()
            self.nickname_edit.selectAll()

    def hide_editor(self) -> None:
        self._editor_height_anim.stop()
        self._editor_opacity_anim.stop()
        self._editor_height_anim.setStartValue(self.editor_frame.maximumHeight())
        self._editor_height_anim.setEndValue(0)
        self._editor_opacity_anim.setStartValue(self._editor_opacity.opacity())
        self._editor_opacity_anim.setEndValue(0.0)
        self._editor_height_anim.start()
        self._editor_opacity_anim.start()

    def _on_editor_height_animation_finished(self) -> None:
        if self.editor_frame.maximumHeight() == 0:
            self.editor_frame.hide()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            ctrl_pressed = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            self.row_clicked.emit(self.instance_id, ctrl_pressed)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            ctrl_pressed = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            self.row_clicked.emit(self.instance_id, ctrl_pressed)
            self.primary_requested.emit(self.instance_id)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # type: ignore[override]
        menu = QMenu(self)
        edit_action = menu.addAction("Edit")
        chosen = menu.exec(event.globalPos())
        if chosen == edit_action:
            self.show_editor("nickname")

    def _submit_metadata(self) -> None:
        self.metadata_submitted.emit(self.instance_id, self.nickname_edit.text(), self.entity_id_edit.text())
        self.hide_editor()
