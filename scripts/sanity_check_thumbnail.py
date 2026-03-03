import ctypes
import os
import sys
from ctypes import wintypes
import psutil

# Need PySide6 for minimal window
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import Qt

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi
kernel32 = ctypes.windll.kernel32

DWM_TNP_VISIBLE = 0x8
DWM_TNP_RECTDESTINATION = 0x1
DWM_TNP_OPACITY = 0x4

class DWM_THUMBNAIL_PROPERTIES(ctypes.Structure):
    _fields_ = [
        ("dwFlags", wintypes.DWORD),
        ("rcDestination", wintypes.RECT),
        ("rcSource", wintypes.RECT),
        ("opacity", ctypes.c_ubyte),
        ("fVisible", wintypes.BOOL),
        ("fSourceClientAreaOnly", wintypes.BOOL),
    ]

# For EnumWindows
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

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
                if proc.name().lower() == "notepad.exe" or "notepad" in title.lower() or proc.name().lower() == "bitcraft.exe":
                    found_windows.append((hwnd, pid.value, proc.name(), title))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    return True

user32.EnumWindows(WNDENUMPROC(enum_windows_proc), 0)

print(f"Found {len(found_windows)} windows:")
for i, window in enumerate(found_windows):
    print(f"[{i}] HWND: {window[0]}, PID: {window[1]}, EXE: {window[2]}, TITLE: {window[3]}")

if not found_windows:
    print("Could not find any suitable process (Looking for BitCraft.exe or notepad.exe as test fallback).")
    sys.exit()

target_window = found_windows[0]
target_hwnd = target_window[0]

class MainWindow(QMainWindow):
    def __init__(self, target_hwnd, target_title):
        super().__init__()
        self.setWindowTitle(f"Preview: {target_title}")
        self.resize(640, 480)
        self.target_hwnd = target_hwnd
        self.thumbnail_handle = None
        
        lbl = QLabel(target_title, self)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: white; background: rgba(0,0,0,150); padding: 5px;")
        lbl.adjustSize()
        lbl.move(10, 10)
        
    def showEvent(self, event):
        super().showEvent(event)
        self.register_thumbnail()
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_thumbnail()
        
    def register_thumbnail(self):
        hthumb = ctypes.c_void_p()
        # DwmRegisterThumbnail(dest, src, &handle)
        hr = dwmapi.DwmRegisterThumbnail(int(self.winId()), self.target_hwnd, ctypes.byref(hthumb))
        if hr == 0:
            self.thumbnail_handle = hthumb
            print(f"Registered thumbnail successfully: handle {self.thumbnail_handle.value}")
            self.update_thumbnail()
        else:
            print(f"Failed to register thumbnail. HRESULT: {hr}")

    def update_thumbnail(self):
        if self.thumbnail_handle:
            props = DWM_THUMBNAIL_PROPERTIES()
            props.dwFlags = DWM_TNP_VISIBLE | DWM_TNP_RECTDESTINATION | DWM_TNP_OPACITY
            props.fVisible = True
            props.opacity = 255
            
            # fill entire window
            props.rcDestination.left = 0
            props.rcDestination.top = 0
            props.rcDestination.right = self.width()
            props.rcDestination.bottom = self.height()
            
            hr = dwmapi.DwmUpdateThumbnailProperties(self.thumbnail_handle, ctypes.byref(props))
            if hr != 0:
                print(f"Failed to update thumbnail. HRESULT: {hr}")
                
    def closeEvent(self, event):
        if self.thumbnail_handle:
            dwmapi.DwmUnregisterThumbnail(self.thumbnail_handle)
        super().closeEvent(event)


app = QApplication(sys.argv)
win = MainWindow(target_hwnd, target_window[3])
win.show()
sys.exit(app.exec())
