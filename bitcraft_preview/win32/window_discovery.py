from dataclasses import dataclass
import typing
import ctypes
from ctypes import wintypes
import psutil
import logging

from bitcraft_preview.win32.title_parse import parse_sandbox_name

@dataclass
class ClientWindow:
    hwnd: int
    pid: int
    title: str
    sandbox_name: typing.Optional[str]

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

logger = logging.getLogger("bitcraft_preview")

def enumerate_windows() -> list[ClientWindow]:
    found_windows = []
    
    def enum_windows_proc(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                
                try:
                    proc = psutil.Process(pid.value)
                    if proc.name().lower() == "bitcraft.exe":
                        # Skip MelonLoader consoles
                        if "MelonLoader".lower() in title.lower():
                            return True
                            
                        sandbox_name = parse_sandbox_name(title)
                        found_windows.append(ClientWindow(
                            hwnd=hwnd,
                            pid=pid.value,
                            title=title,
                            sandbox_name=sandbox_name
                        ))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        return True

    user32.EnumWindows(WNDENUMPROC(enum_windows_proc), 0)
    return found_windows
