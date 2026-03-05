import ctypes
from ctypes import wintypes
import logging

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
logger = logging.getLogger("bitcraft_preview")

SW_RESTORE = 9
SW_SHOW = 5

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010

VK_MENU = 0x12
KEYEVENTF_KEYUP = 0x0002


def _to_hwnd(hwnd: int) -> int | None:
    try:
        value = int(hwnd)
        if value <= 0:
            return None
        return value
    except (TypeError, ValueError):
        return None


def _attach_and_focus(target_hwnd: int) -> bool:
    foreground = user32.GetForegroundWindow()
    if foreground == target_hwnd:
        return True

    target_thread = user32.GetWindowThreadProcessId(target_hwnd, None)
    foreground_thread = user32.GetWindowThreadProcessId(foreground, None)
    current_thread = kernel32.GetCurrentThreadId()

    attached_to_foreground = False
    attached_to_target = False

    try:
        if foreground_thread and foreground_thread != current_thread:
            attached_to_foreground = bool(user32.AttachThreadInput(current_thread, foreground_thread, True))

        if target_thread and target_thread != current_thread:
            attached_to_target = bool(user32.AttachThreadInput(current_thread, target_thread, True))

        user32.BringWindowToTop(target_hwnd)
        user32.SetForegroundWindow(target_hwnd)
        user32.SetFocus(target_hwnd)
    finally:
        if attached_to_target:
            user32.AttachThreadInput(current_thread, target_thread, False)
        if attached_to_foreground:
            user32.AttachThreadInput(current_thread, foreground_thread, False)

    return user32.GetForegroundWindow() == target_hwnd


def _force_foreground_fallback(target_hwnd: int):
    # Temporary topmost toggle often breaks through z-order issues without leaving permanent topmost state.
    user32.SetWindowPos(target_hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
    user32.SetWindowPos(target_hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)

    # ALT key press/release is a known Windows-compatible nudge for foreground permission.
    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)

    user32.BringWindowToTop(target_hwnd)
    user32.SetForegroundWindow(target_hwnd)

def activate_window(hwnd: int):
    target_hwnd = _to_hwnd(hwnd)
    if target_hwnd is None:
        return

    if not user32.IsWindow(target_hwnd):
        return

    if user32.IsIconic(target_hwnd):
        user32.ShowWindowAsync(target_hwnd, SW_RESTORE)
    else:
        user32.ShowWindowAsync(target_hwnd, SW_SHOW)

    if _attach_and_focus(target_hwnd):
        return

    _force_foreground_fallback(target_hwnd)

    if user32.GetForegroundWindow() != target_hwnd:
        logger.debug("Foreground switch may have been denied by Windows for hwnd=%s", target_hwnd)
