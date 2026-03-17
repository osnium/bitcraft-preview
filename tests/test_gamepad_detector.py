import unittest
from unittest.mock import patch

from bitcraft_preview.win32.gamepad_detector import GamepadDetector


class _FakeXInput:
    def __init__(self, connected_indices=None) -> None:
        self.connected_indices = set(connected_indices or [])

    def XInputGetState(self, user_index, _state_ptr):
        return 0 if user_index in self.connected_indices else 1167


class GamepadDetectorTests(unittest.TestCase):
    def test_is_connected_true_when_any_slot_connected(self) -> None:
        detector = GamepadDetector()
        with patch.object(detector, "_load_xinput_library", return_value=_FakeXInput({1})):
            self.assertTrue(detector.is_connected())

    def test_is_connected_false_when_all_slots_disconnected(self) -> None:
        detector = GamepadDetector()
        with patch.object(detector, "_load_xinput_library", return_value=_FakeXInput()):
            self.assertFalse(detector.is_connected())

    def test_is_connected_false_when_library_unavailable(self) -> None:
        detector = GamepadDetector()
        with patch.object(detector, "_load_xinput_library", return_value=None):
            self.assertFalse(detector.is_connected())


if __name__ == "__main__":
    unittest.main()
