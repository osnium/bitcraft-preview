from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QPainterPath, QRegion, QPainter, QColor
import ctypes
from bitcraft_preview.win32.dwm_thumbnail import register_thumbnail, update_thumbnail, unregister_thumbnail
from bitcraft_preview.win32.activation import activate_window
from bitcraft_preview.config import INLINE_LABEL, get_preview_opacity, get_hover_zoom_enabled, get_hover_zoom_percent, get_preview_tile_width, get_preview_tile_height

LABEL_OPACITY_BOOST = 0.20

class LivePreviewTile(QWidget):
    def __init__(self, target_hwnd: int, label_text: str, parent=None):
        super().__init__(parent)
        self.target_hwnd = target_hwnd
        self.label_text = label_text
        self.thumbnail_handle = None
        self.dragging = False
        self.drag_start_position = None
        self.window_start_position = None
        self.is_hovered = False
        
        self.original_rect = QRect()
        self.zoomed_in = False
        self._last_label_opacity = None

        # Set window flags for borderless, always-on-top, tool window (no taskbar icon)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        
        # Set translucency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True) # REQUIRED trick to monitor mouse when leaving the inner unzoomed rect!

        self.resize(get_preview_tile_width(), get_preview_tile_height()) # Default size
        self.setup_ui()
        
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # Sandbox label
        self.label = QLabel(self.label_text)

        self._label_shadow = None
        
        # Adjust layout based on config
        if INLINE_LABEL:
            # DWM draws completely over our background surface, so we must make the label its own floating 
            # translucent tool window that syncs with our position to be visible *on top* of the thumbnail!
            self.label.setParent(None)
            self.label.setWindowFlags(
                Qt.WindowType.Tool |
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.WindowTransparentForInput
            )
            self.label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        else:
            # Drop shadow improves readability for embedded labels, but can create
            # noisy layered-window warnings on the inline floating label window.
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(8)
            shadow.setColor(QColor(0, 0, 0, 255))
            shadow.setOffset(2, 2)
            self._label_shadow = shadow
            self.label.setGraphicsEffect(shadow)

            # Spacer so label stays at the bottom
            self.layout.addStretch()
            self.layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)

        self._refresh_label_visuals()

    def _clamp_opacity(self, value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _compute_label_opacity(self) -> float:
        preview_opacity = self._clamp_opacity(get_preview_opacity())
        if preview_opacity <= 0.0:
            return 0.0
        if preview_opacity >= 1.0:
            return 1.0
        return self._clamp_opacity(preview_opacity + LABEL_OPACITY_BOOST)

    def _refresh_label_visuals(self):
        label_opacity = self._compute_label_opacity()
        if self._last_label_opacity is not None and abs(label_opacity - self._last_label_opacity) < 0.001:
            return

        shadow_alpha = int(255 * label_opacity)
        if self._label_shadow is not None:
            self._label_shadow.setColor(QColor(0, 0, 0, shadow_alpha))

        if INLINE_LABEL:
            if self.label.isVisible():
                self.label.setWindowOpacity(label_opacity)
        else:
            self._apply_label_style(label_opacity)

        self._last_label_opacity = label_opacity

    def _apply_label_style(self, opacity: float):
        opacity = self._clamp_opacity(opacity)
        bg_alpha = int(180 * opacity)
        fg_alpha = int(255 * opacity)
        self.label.setStyleSheet(
            f"color: rgba(255,255,255,{fg_alpha}); background-color: rgba(0,0,0,{bg_alpha}); padding: 5px; font-weight: bold; border-radius: 5px;"
        )

    def paintEvent(self, event):
        # We must paint the background for the transparent window to register mouse clicks properly.
        # Otherwise, clicks pass entirely right through the invisible areas.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Invisible hit-testing layer for the entire window
        painter.setBrush(QColor(0, 0, 0, 1)) # Practically transparent
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_start_position = event.globalPosition().toPoint()
            self.window_start_position = self.frameGeometry().topLeft()
            
            if get_hover_zoom_enabled() and self.zoomed_in:
                self._unzoom()
                self.window_start_position = self.frameGeometry().topLeft()

            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging:
            delta = event.globalPosition().toPoint() - self.drag_start_position
            new_pos = self.window_start_position + delta
            self.move(new_pos)
            
            # If dragged while zoomed, update the original rect so it shrinks back to the new drop point
            if self.zoomed_in and hasattr(self, 'original_rect'):
                self.original_rect.moveTo(new_pos)
                
            event.accept()
        else:
            # Not dragging. Since mouseTracking is True, we get move events constantly while hovering.
            # Check if mouse leaves the ORIGINAL rect while zoomed, so we can shrink without waiting for them to leave the gigantic box.
            if get_hover_zoom_enabled() and self.zoomed_in and hasattr(self, 'original_rect') and self.original_rect:
                # globalPosition() is available in mouse move events
                global_pos = event.globalPosition().toPoint()
                
                if not self.original_rect.contains(global_pos):
                    # They left the bounds of the small rect! Turn off zoom.
                    self._unzoom()
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            # Check if it was a fast click vs a drag
            delta = event.globalPosition().toPoint() - self.drag_start_position
            if delta.manhattanLength() < 5:
                activate_window(self.target_hwnd)
            event.accept()


    def enterEvent(self, event):
        super().enterEvent(event)
        self.is_hovered = True
        
        # Always bring hovered window completely to top so it's over other preview tiles!
        self.raise_()
        if INLINE_LABEL and hasattr(self, 'label') and self.label:
            self.label.raise_()
        
        if self.dragging:
            return

        if get_hover_zoom_enabled() and not self.zoomed_in:
            # Check if the mouse actually entered our *original* visible region and not just the overlap part
            # from another zoomed window. This prevents bouncing between two adjacent windows.
            global_pos = self.cursor().pos()
            current_geom = self.geometry()
            if not current_geom.contains(global_pos):
                return # Ignore enter event if the mouse isn't actually inside our unzoomed geometry yet.

            # Save our original unzoomed geometry
            self.original_rect = current_geom
            
            # Use QGuiApplication.screenAt() to find the screen containing the *center* of the window
            # This handles multi-monitor overlapping much better than just using self.screen()
            from PySide6.QtGui import QGuiApplication
            center_point = current_geom.center()
            target_screen = QGuiApplication.screenAt(center_point)
            if not target_screen:
                target_screen = self.screen()
                
            screen_geom = target_screen.availableGeometry()
            scale_factor = get_hover_zoom_percent() / 100.0
            
            new_w = int(self.original_rect.width() * scale_factor)
            new_h = int(self.original_rect.height() * scale_factor)
            
            # Center the zoom slightly
            new_x = self.original_rect.x() - int((new_w - self.original_rect.width()) / 2)
            new_y = self.original_rect.y() - int((new_h - self.original_rect.height()) / 2)
            
            # Keep within screen bounds
            if new_x < screen_geom.left():
                new_x = screen_geom.left()
            if new_y < screen_geom.top():
                new_y = screen_geom.top()
                
            if new_x + new_w > screen_geom.right():
                new_x = screen_geom.right() - new_w
            if new_y + new_h > screen_geom.bottom():
                new_y = screen_geom.bottom() - new_h
                
            # After clamping to screen bounds, ensure the mouse is still inside the new geometry
            # to prevent immediate unzooming (flickering) if the window shifted away from the cursor.
            if global_pos.x() < new_x:
                new_x = global_pos.x()
            elif global_pos.x() >= new_x + new_w:
                new_x = global_pos.x() - new_w + 1
                
            if global_pos.y() < new_y:
                new_y = global_pos.y()
            elif global_pos.y() >= new_y + new_h:
                new_y = global_pos.y() - new_h + 1
                
            self.setGeometry(new_x, new_y, new_w, new_h)
            self.zoomed_in = True

        self.update_thumbnail_rect()
        self._refresh_label_visuals()

    def _unzoom(self):
        # Helper to neatly shrink the window down
        if self.zoomed_in and hasattr(self, 'original_rect') and self.original_rect:
            self.setGeometry(self.original_rect)
            self.zoomed_in = False
            self.update_thumbnail_rect()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        
        # We only consider it a leave if the mouse actually left the zoomed window area.
        # Avoid fake leave events triggered during resize/move if the mouse is still inside
        if self.zoomed_in and self.geometry().contains(self.cursor().pos()):
            return
            
        self.is_hovered = False
        
        if get_hover_zoom_enabled():
            self._unzoom()

        self.update_thumbnail_rect()
        self._refresh_label_visuals()

    def update_inline_label_position(self):
        if INLINE_LABEL and self.label.isVisible():
            # mapToGlobal converts local logical coords to global logical screen coords,
            # which is what move() on a parentless top-level window expects.
            bottom_left = self.mapToGlobal(QPoint(10, self.height() - self.label.height() - 10))
            self.label.move(bottom_left)

    def sync_size(self):
        """Called each refresh tick to apply live config size changes."""
        self._refresh_label_visuals()
        self.update_thumbnail_rect()
        if self.zoomed_in or self.dragging:
            return
        cfg_w = get_preview_tile_width()
        cfg_h = get_preview_tile_height()
        if self.width() != cfg_w or self.height() != cfg_h:
            self.resize(cfg_w, cfg_h)

    def moveEvent(self, event):
        super().moveEvent(event)
        self.update_inline_label_position()

    def showEvent(self, event):
        super().showEvent(event)
        if INLINE_LABEL:
            self.label.show()
            self.update_inline_label_position()
            
        if not self.thumbnail_handle:
            win_id = int(self.winId())
            self.thumbnail_handle = register_thumbnail(win_id, self.target_hwnd)
            self.update_thumbnail_rect()

    def hideEvent(self, event):
        super().hideEvent(event)
        if INLINE_LABEL:
            self.label.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_thumbnail_rect()
        
        if INLINE_LABEL:
            self.update_inline_label_position()

        # Add rounded corners to the OS window mask so the DWM thumbnail is also clipped
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 15, 15)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    def update_thumbnail_rect(self):
        if self.thumbnail_handle:
            # DWM rcDestination expects physical pixels, but Qt geometry is in logical pixels.
            # Multiply by devicePixelRatio so the thumbnail fills the entire window at any DPI scale.
            dpr = self.devicePixelRatio()
            phys_w = int(self.width() * dpr)
            phys_h = int(self.height() * dpr)

            if INLINE_LABEL:
                # The whole window is the thumbnail
                rect = (0, 0, phys_w, phys_h)
            else:
                # DWM renders over the Qt window. We restrict its height 
                # so the QLabel sandbox name below is visible and not covered.
                label_zone = int((self.label.height() + 20) * dpr)  # Label + margins, in physical px
                rect = (0, 0, phys_w, phys_h - label_zone)
            
            # Use configurable opacity (converted 0.0-1.0 to 0-255)
            # If hovered, become fully solid (255)
            current_opacity = 1.0 if self.is_hovered else get_preview_opacity()
            dwm_alpha = int(255 * current_opacity)
            update_thumbnail(self.thumbnail_handle, rect, opacity=dwm_alpha)

    def closeEvent(self, event):
        if self.thumbnail_handle:
            unregister_thumbnail(self.thumbnail_handle)
            self.thumbnail_handle = None
            
        if INLINE_LABEL:
            self.label.close()
            self.label.deleteLater()
            
        super().closeEvent(event)
