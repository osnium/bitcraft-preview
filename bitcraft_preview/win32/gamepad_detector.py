from __future__ import annotations

import ctypes
from ctypes import wintypes


ERROR_SUCCESS = 0


class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", wintypes.DWORD),
        ("Gamepad", XINPUT_GAMEPAD),
    ]


class GamepadDetector:
    """Detect whether any XInput gamepad is connected on Windows."""

    def __init__(self, max_users: int = 4) -> None:
        self._max_users = max_users

    def is_connected(self) -> bool:
        xinput = self._load_xinput_library()
        if xinput is None:
            return False

        get_state = getattr(xinput, "XInputGetState", None)
        if get_state is None:
            return False

        # Some test doubles and wrapper callables don't support ctypes metadata attributes.
        try:
            get_state.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]
            get_state.restype = wintypes.DWORD
        except Exception:
            pass

        for user_index in range(self._max_users):
            state = XINPUT_STATE()
            try:
                result = int(get_state(user_index, ctypes.byref(state)))
            except Exception:
                return False
            if result == ERROR_SUCCESS:
                return True
        return False

    def _load_xinput_library(self):
        windll = getattr(ctypes, "windll", None)
        if windll is None:
            return None

        for library_name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
            try:
                return getattr(windll, library_name)
            except Exception:
                continue
        return None
