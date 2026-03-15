from __future__ import annotations

import os

from PySide6.QtCore import QEasingCurve, QParallelAnimationGroup, QPropertyAnimation, QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from bitcraft_preview import config
from bitcraft_preview.ui.shell.panels import AccountsPanel, PlaceholderPanel, SettingsPanel


class MainShellWindow(QMainWindow):
    SIDEBAR_EXPANDED_WIDTH = 188
    SIDEBAR_COLLAPSED_WIDTH = 46

    def __init__(self) -> None:
        super().__init__()
        self._panels: list[dict[str, str | QWidget]] = []
        self._panel_index_by_id: dict[str, int] = {}
        self._nav_row_by_panel_id: dict[str, int] = {}
        self._sidebar_collapsed = False
        self._sidebar_width_animation = QParallelAnimationGroup(self)
        self._build_ui()
        self._register_panels()
        self._setup_sidebar_animation()
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

        self.sidebar_toggle_row = QWidget(self.sidebar_surface)
        self.sidebar_toggle_row.setObjectName("SidebarToggleRow")
        self.sidebar_toggle_row.setFixedHeight(30)
        top_row = QHBoxLayout(self.sidebar_toggle_row)
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        self.sidebar_title = QLabel("Panels")
        self.sidebar_title.setObjectName("SectionTitle")

        self.sidebar_toggle = QPushButton("<")
        self.sidebar_toggle.setObjectName("SidebarToggle")
        self.sidebar_toggle.clicked.connect(self.toggle_sidebar)
        top_row.addWidget(self.sidebar_title)
        top_row.addStretch(1)
        top_row.addWidget(self.sidebar_toggle)
        self.sidebar_toggle.setText("")
        self.sidebar_toggle.setIconSize(QSize(18, 18))
        self._sidebar_expand_icon = QIcon()
        self._sidebar_collapse_icon = QIcon()
        self._try_apply_sidebar_toggle_icons()

        self.nav = QListWidget(self.sidebar_surface)
        self.nav.setIconSize(QSize(27, 27))
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.nav.setMinimumHeight(0)
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
        self.quick_settings_btn.clicked.connect(lambda: self.show_panel("settings", sync_nav=False))

        self.quick_setup_btn = QPushButton()
        self.quick_setup_btn.setObjectName("QuickActionButton")
        self.quick_setup_btn.setToolTip("Open Setup placeholder (future guided multi-step setup flow)")
        self.quick_setup_btn.clicked.connect(lambda: self.show_panel("setup", sync_nav=False))

        self.quick_exit_btn = QPushButton()
        self.quick_exit_btn.setObjectName("QuickActionButton")
        self.quick_exit_btn.setToolTip("Exit BitCraft Preview completely")
        self.quick_exit_btn.clicked.connect(QApplication.instance().quit)

        for btn in (self.quick_settings_btn, self.quick_setup_btn, self.quick_exit_btn):
            btn.setFixedSize(32, 32)
            btn.setIconSize(QSize(20, 20))
            btn.setText("")
            quick_actions.addWidget(btn)

        quick_actions.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._try_apply_quick_action_icons()

        sidebar_layout.addWidget(self.sidebar_toggle_row)
        sidebar_layout.addWidget(self.nav, 1)
        sidebar_layout.addWidget(self.quick_actions_widget, 0)
        sidebar_layout.addStretch(0)

        main_layout.addWidget(self.sidebar_surface, 0)
        main_layout.addWidget(self.content_surface, 1)

        root.addWidget(self.main_surface, 1)

    def _setup_sidebar_animation(self) -> None:
        self._sidebar_min_anim = QPropertyAnimation(self.sidebar_surface, b"minimumWidth", self)
        self._sidebar_min_anim.setDuration(120)
        self._sidebar_min_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._sidebar_max_anim = QPropertyAnimation(self.sidebar_surface, b"maximumWidth", self)
        self._sidebar_max_anim.setDuration(120)
        self._sidebar_max_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._sidebar_width_animation.addAnimation(self._sidebar_min_anim)
        self._sidebar_width_animation.addAnimation(self._sidebar_max_anim)
        self._sidebar_width_animation.finished.connect(self._on_sidebar_animation_finished)

    def _register_panels(self) -> None:
        self._add_panel("settings", "Settings", SettingsPanel(self), add_to_nav=False)
        self._add_panel(
            "setup",
            "Setup",
            PlaceholderPanel("Setup", "Setup workflow placeholder. This panel will host multi-step account setup in a later iteration.", self),
            add_to_nav=False,
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

    def _add_panel(self, panel_id: str, title: str, widget: QWidget, add_to_nav: bool = True, scrollable: bool = True) -> None:
        if scrollable:
            page = QScrollArea(self.content_stack)
            page.setWidgetResizable(True)
            page.setFrameShape(QFrame.Shape.NoFrame)
            page.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            page.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            page.setWidget(widget)
            index = self.content_stack.addWidget(page)
        else:
            index = self.content_stack.addWidget(widget)

        self._panel_index_by_id[panel_id] = index
        self._panels.append({"id": panel_id, "title": title, "widget": widget})

        if add_to_nav:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, panel_id)
            icon = self._nav_icon_for_panel(panel_id)
            if not icon.isNull():
                item.setIcon(icon)
            self.nav.addItem(item)
            self._nav_row_by_panel_id[panel_id] = self.nav.count() - 1

    def _asset_path(self, *parts: str) -> str:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_path, "assets", *parts)

    def _nav_icon_for_panel(self, panel_id: str) -> QIcon:
        icon_paths = {
            "accounts": self._asset_path("icons", "tabs", "accounts.png"),
            "monitor": self._asset_path("icons", "tabs", "monitor.png"),
            "updates": self._asset_path("icons", "tabs", "updates.png"),
            "map": self._asset_path("icons", "tabs", "map.png"),
        }
        path = icon_paths.get(panel_id)
        if path and os.path.exists(path):
            return QIcon(path)
        return QIcon()

    def _try_apply_sidebar_toggle_icons(self) -> None:
        expand_path = self._asset_path("icons", "ui", "sidebar_expand.png")
        collapse_path = self._asset_path("icons", "ui", "sidebar_collapse.png")

        if os.path.exists(expand_path):
            self._sidebar_expand_icon = QIcon(expand_path)
        if os.path.exists(collapse_path):
            self._sidebar_collapse_icon = QIcon(collapse_path)

    def _try_apply_quick_action_icons(self) -> None:
        candidates = {
            self.quick_settings_btn: self._asset_path("icons", "quick", "settings.png"),
            self.quick_setup_btn: self._asset_path("icons", "quick", "setup.png"),
            self.quick_exit_btn: self._asset_path("icons", "quick", "exit.png"),
        }
        for button, icon_path in candidates.items():
            if os.path.exists(icon_path):
                button.setIcon(QIcon(icon_path))

    def _restore_gui_state(self) -> None:
        settings = config.get_gui_settings()
        self._sidebar_collapsed = bool(settings.get("sidebar_collapsed", False))
        self._apply_sidebar_state(persist=False, animate=False)

        panel_id = settings.get("last_panel", "settings")
        self.show_panel(str(panel_id))

    def show_panel(self, panel_id: str, sync_nav: bool = True) -> None:
        target = str(panel_id or "settings").strip().lower()
        if target not in self._panel_index_by_id:
            target = "settings"
        index = self._panel_index_by_id[target]
        self.content_stack.setCurrentIndex(index)
        self._refresh_visible_panel()

        if sync_nav:
            row = self._nav_row_by_panel_id.get(target)
            if row is not None:
                self.nav.setCurrentRow(row)
            else:
                self.nav.blockSignals(True)
                self.nav.setCurrentRow(-1)
                self.nav.blockSignals(False)
        else:
            self.nav.blockSignals(True)
            self.nav.setCurrentRow(-1)
            self.nav.blockSignals(False)

    def _on_nav_changed(self, index: int) -> None:
        if index < 0:
            return
        item = self.nav.item(index)
        if item is None:
            return
        panel_id = str(item.data(Qt.ItemDataRole.UserRole) or "settings")

        panel_index = self._panel_index_by_id.get(panel_id)
        if panel_index is None:
            return

        self.content_stack.setCurrentIndex(panel_index)
        config.update_gui_settings(last_panel=panel_id)
        self._refresh_visible_panel()

    def _refresh_visible_panel(self) -> None:
        widget = self.content_stack.currentWidget()
        if isinstance(widget, QScrollArea):
            widget = widget.widget()
        if isinstance(widget, AccountsPanel):
            widget.refresh_data()

    def toggle_sidebar(self) -> None:
        self._sidebar_collapsed = not self._sidebar_collapsed
        self._apply_sidebar_state(persist=True, animate=True)

    def _apply_sidebar_state(self, persist: bool, animate: bool = True) -> None:
        target_width = self.SIDEBAR_COLLAPSED_WIDTH if self._sidebar_collapsed else self.SIDEBAR_EXPANDED_WIDTH

        self._sidebar_width_animation.stop()

        if not self._sidebar_collapsed:
            self.sidebar_title.show()
            self.nav.show()
            self.quick_actions_widget.show()

        if self._sidebar_collapsed:
            if not self._sidebar_expand_icon.isNull():
                self.sidebar_toggle.setIcon(self._sidebar_expand_icon)
            else:
                self.sidebar_toggle.setText(">")
        else:
            if not self._sidebar_collapse_icon.isNull():
                self.sidebar_toggle.setIcon(self._sidebar_collapse_icon)
            else:
                self.sidebar_toggle.setText("<")

        if not animate:
            self.sidebar_surface.setMinimumWidth(target_width)
            self.sidebar_surface.setMaximumWidth(target_width)
            self._on_sidebar_animation_finished()
        else:
            current_width = max(self.sidebar_surface.width(), self.sidebar_surface.minimumWidth())
            self._sidebar_min_anim.setStartValue(current_width)
            self._sidebar_min_anim.setEndValue(target_width)
            self._sidebar_max_anim.setStartValue(current_width)
            self._sidebar_max_anim.setEndValue(target_width)
            self._sidebar_width_animation.start()

        if persist:
            config.update_gui_settings(sidebar_collapsed=self._sidebar_collapsed)

    def _on_sidebar_animation_finished(self) -> None:
        if self._sidebar_collapsed:
            self.sidebar_title.hide()
            self.nav.hide()
            self.quick_actions_widget.hide()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()
        self.hide()

    def show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
