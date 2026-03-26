import unittest
from unittest.mock import patch

from PySide6.QtCore import QPoint, Qt

from bitcraft_preview.ui.tile import LivePreviewTile


class _FakePointValue:
    def __init__(self, point):
        self._point = point

    def toPoint(self):
        return self._point


class _FakeMouseEvent:
    def __init__(self, point, button=Qt.MouseButton.LeftButton):
        self._point = point
        self._button = button
        self.accepted = False

    def button(self):
        return self._button

    def globalPosition(self):
        return _FakePointValue(self._point)

    def accept(self):
        self.accepted = True


class _FakeFrameGeometry:
    def __init__(self, top_left):
        self._top_left = top_left

    def topLeft(self):
        return self._top_left


class _FakeSignal:
    def __init__(self):
        self.calls = []

    def emit(self, *args):
        self.calls.append(args)


class LivePreviewTileDragLockTests(unittest.TestCase):
    def _tile(self, start_point=QPoint(100, 100)):
        tile = LivePreviewTile.__new__(LivePreviewTile)
        tile.target_hwnd = 777
        tile.dragging = False
        tile._drag_moved = False
        tile.drag_start_position = None
        tile.window_start_position = None
        tile.zoomed_in = False
        tile.original_rect = None
        tile.position_changed = _FakeSignal()
        tile._moves = []
        tile._current_pos = start_point
        tile.frameGeometry = lambda: _FakeFrameGeometry(tile._current_pos)
        tile.move = lambda point: self._move_tile(tile, point)
        return tile

    def _move_tile(self, tile, point):
        tile._current_pos = point
        tile._moves.append(point)

    def test_locked_tile_does_not_start_drag_or_emit_position_change(self):
        tile = self._tile()
        press_event = _FakeMouseEvent(QPoint(120, 140))
        move_event = _FakeMouseEvent(QPoint(170, 190))
        release_event = _FakeMouseEvent(QPoint(170, 190))

        with (
            patch("bitcraft_preview.ui.tile.get_lock_overlay_tiles", return_value=True),
            patch("bitcraft_preview.ui.tile.get_hover_zoom_enabled", return_value=False),
            patch("bitcraft_preview.ui.tile.QWidget.mouseMoveEvent", return_value=None),
            patch("bitcraft_preview.ui.tile.activate_window") as activate_window,
        ):
            tile.mousePressEvent(press_event)
            tile.mouseMoveEvent(move_event)
            tile.mouseReleaseEvent(release_event)

        self.assertFalse(tile.dragging)
        self.assertEqual(tile._moves, [])
        self.assertEqual(tile.position_changed.calls, [])
        activate_window.assert_not_called()
        self.assertTrue(press_event.accepted)
        self.assertTrue(release_event.accepted)

    def test_unlocked_tile_moves_and_emits_position_change(self):
        tile = self._tile()
        press_event = _FakeMouseEvent(QPoint(120, 140))
        move_event = _FakeMouseEvent(QPoint(170, 190))
        release_event = _FakeMouseEvent(QPoint(170, 190))

        with (
            patch("bitcraft_preview.ui.tile.get_lock_overlay_tiles", return_value=False),
            patch("bitcraft_preview.ui.tile.get_hover_zoom_enabled", return_value=False),
            patch("bitcraft_preview.ui.tile.activate_window") as activate_window,
        ):
            tile.mousePressEvent(press_event)
            tile.mouseMoveEvent(move_event)
            tile.mouseReleaseEvent(release_event)

        self.assertFalse(tile.dragging)
        self.assertEqual(tile._moves, [QPoint(150, 150)])
        self.assertEqual(tile.position_changed.calls, [(150, 150)])
        activate_window.assert_not_called()
        self.assertTrue(move_event.accepted)
        self.assertTrue(release_event.accepted)

    def test_locked_tile_click_still_activates_target_window(self):
        tile = self._tile()
        press_event = _FakeMouseEvent(QPoint(120, 140))
        release_event = _FakeMouseEvent(QPoint(122, 142))

        with (
            patch("bitcraft_preview.ui.tile.get_lock_overlay_tiles", return_value=True),
            patch("bitcraft_preview.ui.tile.get_hover_zoom_enabled", return_value=False),
            patch("bitcraft_preview.ui.tile.activate_window") as activate_window,
        ):
            tile.mousePressEvent(press_event)
            tile.mouseReleaseEvent(release_event)

        activate_window.assert_called_once_with(777)
        self.assertEqual(tile.position_changed.calls, [])
        self.assertIsNone(tile.drag_start_position)
        self.assertIsNone(tile.window_start_position)


if __name__ == "__main__":
    unittest.main()