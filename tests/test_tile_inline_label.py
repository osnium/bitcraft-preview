import unittest
from unittest.mock import call, patch

from PySide6.QtCore import QPoint

from bitcraft_preview.ui.tile import LivePreviewTile


class _FakeLabel:
    def __init__(self, visible=False, hwnd=222):
        self._visible = visible
        self._hwnd = hwnd
        self.show_calls = 0
        self.raise_calls = 0
        self.move_calls = []

    def isVisible(self):
        return self._visible

    def show(self):
        self._visible = True
        self.show_calls += 1

    def raise_(self):
        self.raise_calls += 1

    def move(self, point):
        self.move_calls.append(point)

    def height(self):
        return 24

    def winId(self):
        return self._hwnd


class _FakeTileWindow:
    def __init__(self):
        self.raise_calls = 0

    def raise_(self):
        self.raise_calls += 1


class LivePreviewTileInlineLabelTests(unittest.TestCase):
    def _tile(self, *, visible=True, label_visible=False):
        tile = LivePreviewTile.__new__(LivePreviewTile)
        tile.label = _FakeLabel(visible=label_visible)
        tile.isVisible = lambda: visible
        tile.height = lambda: 200
        tile.mapToGlobal = lambda point: QPoint(50, 60)
        tile.winId = lambda: 111
        tile.raise_ = _FakeTileWindow().raise_
        return tile

    def test_sync_inline_label_shows_moves_and_stacks_label(self):
        tile = self._tile(visible=True, label_visible=False)

        with (
            patch("bitcraft_preview.ui.tile.INLINE_LABEL", True),
            patch("bitcraft_preview.ui.tile.user32.SetWindowPos", return_value=1) as set_window_pos,
        ):
            tile._sync_inline_label_window(ensure_visible=True)

        self.assertEqual(tile.label.show_calls, 1)
        self.assertEqual(tile.label.move_calls, [QPoint(50, 60)])
        set_window_pos.assert_called_once_with(
            111,
            222,
            0,
            0,
            0,
            0,
            0x0001 | 0x0002 | 0x0010,
        )

    def test_sync_inline_label_falls_back_to_raise_when_native_stack_fails(self):
        tile = self._tile(visible=True, label_visible=True)

        with (
            patch("bitcraft_preview.ui.tile.INLINE_LABEL", True),
            patch("bitcraft_preview.ui.tile.user32.SetWindowPos", return_value=0),
        ):
            tile._sync_inline_label_window()

        self.assertEqual(tile.label.raise_calls, 1)

    def test_sync_inline_label_can_bring_hovered_pair_to_foreground(self):
        tile = self._tile(visible=True, label_visible=True)

        with (
            patch("bitcraft_preview.ui.tile.INLINE_LABEL", True),
            patch("bitcraft_preview.ui.tile.user32.SetWindowPos", return_value=1) as set_window_pos,
        ):
            tile._sync_inline_label_window(bring_to_foreground=True)

        self.assertEqual(
            set_window_pos.call_args_list,
            [
                call(222, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010),
                call(111, 222, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010),
            ],
        )

    def test_bring_to_foreground_promotes_non_inline_tile(self):
        tile = self._tile(visible=True, label_visible=False)

        with (
            patch("bitcraft_preview.ui.tile.INLINE_LABEL", False),
            patch("bitcraft_preview.ui.tile.user32.SetWindowPos", return_value=1) as set_window_pos,
        ):
            tile._bring_to_foreground()

        set_window_pos.assert_called_once_with(
            111,
            -1,
            0,
            0,
            0,
            0,
            0x0001 | 0x0002 | 0x0010,
        )


if __name__ == "__main__":
    unittest.main()