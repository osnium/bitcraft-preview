import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32

def activate_window(hwnd: int):
    # Check if window is minimized
    if user32.IsIconic(hwnd):
        # 9 is SW_RESTORE
        user32.ShowWindowAsync(hwnd, 9)
    # Regardless of state, bring it to the foreground
    user32.SetForegroundWindow(hwnd)
