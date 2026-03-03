import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32

def activate_window(hwnd: int):
    # Try restoring if minimized
    user32.ShowWindowAsync(hwnd, 9) # 9 is SW_RESTORE
    user32.SetForegroundWindow(hwnd)
