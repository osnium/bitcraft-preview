# bitcraft_preview/ui/overlay_manager.py
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import QTimer
import ctypes
import psutil
from bitcraft_preview.win32.window_discovery import enumerate_windows
from bitcraft_preview.ui.tile import LivePreviewTile
from bitcraft_preview.config import (
    PROCESS_NAME,
    REFRESH_INTERVAL_MS,
    get_current_mode,
    get_hide_active_window_overlay,
    get_overlay_enabled,
    get_preview_tile_width,
    get_save_overlay_position_per_account,
    get_show_overlay_only_when_focused,
    get_switch_window_enabled,
    get_switch_window_hotkey,
)
from bitcraft_preview.native.state_manager import NativeModeStateManager
from bitcraft_preview.win32.title_parse import display_label
from bitcraft_preview.win32.activation import activate_window
from bitcraft_preview.win32.hotkey_monitor import GlobalHotkeyMonitor
import logging

logger = logging.getLogger("bitcraft_preview")
user32 = ctypes.windll.user32
HOTKEY_POLL_INTERVAL_MS = 25

class OverlayManager:
    def __init__(self):
        self.overlays = {}  # target_hwnd -> LivePreviewTile overlay
        self._overlay_windows = {}  # target_hwnd -> overlay widget hwnd
        self._live_refresh_queued = False
        self.hotkey_monitor = GlobalHotkeyMonitor()
        self._current_hotkey_spec = ""
        self._last_switched_hwnd = None
        # Always keep a valid binding to avoid a non-functional hotkey if config is malformed.
        self.hotkey_monitor.set_hotkey("MOUSE5")
        self._current_hotkey_spec = "MOUSE5"
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_windows)
        self.timer.start(REFRESH_INTERVAL_MS)

        # Poll hotkey separately from expensive overlay refresh so switching stays responsive.
        self.hotkey_timer = QTimer()
        self.hotkey_timer.timeout.connect(self.poll_hotkey)
        self.hotkey_timer.start(HOTKEY_POLL_INTERVAL_MS)

        self.refresh_windows()

    def get_active_window(self):
        return user32.GetForegroundWindow()

    def _refresh_hotkey_binding(self):
        configured_spec = get_switch_window_hotkey().strip()
        if not configured_spec:
            configured_spec = "MOUSE5"

        if configured_spec == self._current_hotkey_spec:
            return

        if self.hotkey_monitor.set_hotkey(configured_spec):
            self._current_hotkey_spec = configured_spec

    def _sorted_windows(self, windows):
        return sorted(windows, key=lambda w: ((w.sandbox_name or "").lower(), int(w.hwnd)))

    def _normalize_hwnd(self, hwnd):
        try:
            return int(hwnd)
        except (TypeError, ValueError):
            return None

    def _is_target_process_foreground(self):
        active_hwnd = self._normalize_hwnd(self.get_active_window())
        if not active_hwnd:
            return False

        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(active_hwnd, ctypes.byref(pid))
        if not pid.value:
            return False

        try:
            active_name = psutil.Process(pid.value).name().lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False

        return active_name == PROCESS_NAME.lower()

    def _close_all_overlays(self):
        for hwnd in list(self.overlays.keys()):
            overlay = self.overlays.pop(hwnd)
            self._overlay_windows.pop(hwnd, None)
            overlay.close()
            overlay.deleteLater()

    def _is_overlay_interaction_active(self, active_hwnd=None):
        normalized_active = self._normalize_hwnd(active_hwnd if active_hwnd is not None else self.get_active_window())
        for target_hwnd, overlay in list(self.overlays.items()):
            if getattr(overlay, "dragging", False):
                return True
            overlay_hwnd = self._overlay_windows.get(target_hwnd)
            if overlay_hwnd is None:
                try:
                    overlay_hwnd = int(overlay.winId())
                    self._overlay_windows[target_hwnd] = overlay_hwnd
                except (TypeError, ValueError, RuntimeError):
                    overlay_hwnd = None
            if overlay_hwnd is not None and normalized_active == overlay_hwnd:
                return True
        return False

    def _should_show_overlays(self, active_hwnd=None):
        if not get_show_overlay_only_when_focused():
            return True
        if self._is_target_process_foreground():
            return True
        return self._is_overlay_interaction_active(active_hwnd)

    def _build_native_instance_label_map(self):
        label_map = {}
        if get_current_mode() != "native":
            return label_map
        for instance in NativeModeStateManager().list_instances():
            instance_key = instance.instance_id.strip().lower()
            if instance_key:
                label_map[instance_key] = instance
            nickname_key = (instance.overlay_nickname or "").strip().lower()
            if nickname_key:
                label_map[nickname_key] = instance
        return label_map

    def _resolve_saved_tile_position(self, label_map, label_text):
        if not get_save_overlay_position_per_account():
            return None
        if get_current_mode() != "native":
            return None
        instance = label_map.get((label_text or "").strip().lower())
        if instance is None:
            return None
        x = int(getattr(instance, "tile_position_x", 0) or 0)
        y = int(getattr(instance, "tile_position_y", 0) or 0)
        if x == 0 and y == 0:
            return None
        return x, y

    def _persist_tile_position(self, label_text, x, y):
        if not get_save_overlay_position_per_account():
            return
        if get_current_mode() != "native":
            return

        normalized_label = (label_text or "").strip().lower()
        if not normalized_label:
            return

        state = NativeModeStateManager()
        instance = None
        for row in state.list_instances():
            if row.instance_id.strip().lower() == normalized_label:
                instance = row
                break
            nickname = (row.overlay_nickname or "").strip().lower()
            if nickname and nickname == normalized_label:
                instance = row
                break

        if instance is None:
            return

        state.upsert_instance(
            instance_id=instance.instance_id,
            local_username=instance.local_username,
            plain_password=None,
            steam_account_name=instance.steam_account_name,
            entity_id=instance.entity_id,
            overlay_nickname=instance.overlay_nickname,
            local_user_sid=instance.local_user_sid,
            instance_root=instance.instance_root,
            steam_exe_path=instance.steam_exe_path,
            steamapps_link_path=instance.steamapps_link_path,
            steamapps_link_target=instance.steamapps_link_target,
            tile_position_x=int(x),
            tile_position_y=int(y),
            status=instance.status,
        )

    def _on_overlay_tile_position_changed(self, target_hwnd, x, y):
        overlay = self.overlays.get(target_hwnd)
        if overlay is None:
            return
        self._persist_tile_position(overlay.label_text, x, y)

    def _switch_to_next_window(self, windows):
        if not windows:
            return

        ordered = self._sorted_windows(windows)
        active_hwnd = self._normalize_hwnd(self.get_active_window())
        hwnds = [self._normalize_hwnd(w.hwnd) for w in ordered]
        hwnds = [hwnd for hwnd in hwnds if hwnd is not None]
        if not hwnds:
            return

        last_switched = self._normalize_hwnd(self._last_switched_hwnd)

        # Prefer our own cursor (last switched hwnd) so presses always advance,
        # even if foreground-window reporting is stale or focus was denied.
        if last_switched in hwnds:
            current_index = hwnds.index(last_switched)
            next_hwnd = hwnds[(current_index + 1) % len(hwnds)]
        elif active_hwnd in hwnds:
            current_index = hwnds.index(active_hwnd)
            next_hwnd = hwnds[(current_index + 1) % len(hwnds)]
        else:
            next_hwnd = hwnds[0]

        activate_window(next_hwnd)
        self._last_switched_hwnd = next_hwnd
        logger.info("Hotkey switch: activated window %s", next_hwnd)

    def poll_hotkey(self):
        self._refresh_hotkey_binding()
        if not get_switch_window_enabled():
            return

        if not self._is_target_process_foreground():
            return

        if self.hotkey_monitor.poll_triggered():
            self._switch_to_next_window(enumerate_windows())

    def schedule_live_settings_refresh(self):
        if self._live_refresh_queued:
            return
        self._live_refresh_queued = True
        QTimer.singleShot(0, self._apply_live_settings)

    def _apply_live_settings(self):
        self._live_refresh_queued = False
        self._refresh_hotkey_binding()

        if not get_overlay_enabled():
            self._close_all_overlays()
            return

        active_hwnd = self.get_active_window()
        show_overlays = self._should_show_overlays(active_hwnd)
        hide_active = get_hide_active_window_overlay()

        for hwnd, overlay in list(self.overlays.items()):
            overlay.sync_size()

            if not show_overlays:
                if overlay.isVisible():
                    overlay.hide()
                continue

            if hide_active and hwnd == active_hwnd:
                if overlay.isVisible():
                    overlay.hide()
            elif not overlay.isVisible():
                overlay.show()
                overlay.update_thumbnail_rect()

    def refresh_windows(self):
        self._refresh_hotkey_binding()

        if not get_overlay_enabled():
            self._close_all_overlays()
            return

        windows = enumerate_windows()
        native_instances = self._build_native_instance_label_map()

        current_hwnds = {w.hwnd: w for w in windows}
        active_hwnd = self.get_active_window()
        show_overlays = self._should_show_overlays(active_hwnd)

        # Remove closed windows
        for hwnd in list(self.overlays.keys()):
            if hwnd not in current_hwnds:
                overlay = self.overlays.pop(hwnd)
                self._overlay_windows.pop(hwnd, None)
                overlay.close()
                overlay.deleteLater()
                logger.info(f"Removed overlay for window {hwnd}")

        # Add or update windows
        for window in windows:
            label_text = display_label(window.title, window.pid)
            if window.hwnd not in self.overlays:
                overlay = LivePreviewTile(window.hwnd, label_text)
                self.overlays[window.hwnd] = overlay
                overlay.position_changed.connect(
                    lambda x, y, target_hwnd=window.hwnd: self._on_overlay_tile_position_changed(target_hwnd, x, y)
                )

                saved_position = self._resolve_saved_tile_position(native_instances, label_text)
                if saved_position is not None:
                    overlay.move(saved_position[0], saved_position[1])
                else:
                    # Default position (top-left offset)
                    offset = 50 + (len(self.overlays) - 1) * get_preview_tile_width()
                    overlay.move(offset, 50)
                
                try:
                    self._overlay_windows[window.hwnd] = int(overlay.winId())
                except (TypeError, ValueError, RuntimeError):
                    self._overlay_windows.pop(window.hwnd, None)
                
                logger.info(f"Added overlay for window {window.hwnd} [{label_text}]")
                
            else:
                overlay = self.overlays[window.hwnd]
                # Re-compute label in case config changed
                label_text = display_label(window.title, window.pid)
                if overlay.label_text != label_text:
                    overlay.label_text = label_text
                    overlay.label.setText(label_text)
                overlay.sync_size()

            if not show_overlays:
                if overlay.isVisible():
                    overlay.hide()
                continue

            # Hide overlay if this client is active and config enables it
            if get_hide_active_window_overlay() and window.hwnd == active_hwnd:
                if overlay.isVisible():
                    overlay.hide()
            elif not overlay.isVisible():
                overlay.show()
                overlay.update_thumbnail_rect()
