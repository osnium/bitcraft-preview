import ctypes
from ctypes import wintypes
import logging

dwmapi = ctypes.windll.dwmapi

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

# just provide the interface so UI class can call it directly or make wrappers
def register_thumbnail(dest_hwnd: int, src_hwnd: int) -> int:
    hthumb = ctypes.c_void_p()
    # DwmRegisterThumbnail(dest, src, &handle)
    hr = dwmapi.DwmRegisterThumbnail(dest_hwnd, src_hwnd, ctypes.byref(hthumb))
    if hr == 0:
        return hthumb.value
    else:
        # Check if the thumbnail is already registered or other error
        pass
    return None

def update_thumbnail(hthumb: int, dest_rect) -> None:
    # dest_rect expects tuple (left, top, right, bottom)
    if hthumb:
        props = DWM_THUMBNAIL_PROPERTIES()
        props.dwFlags = DWM_TNP_VISIBLE | DWM_TNP_RECTDESTINATION | DWM_TNP_OPACITY
        props.fVisible = True
        props.opacity = 255
        
        props.rcDestination.left = dest_rect[0]
        props.rcDestination.top = dest_rect[1]
        props.rcDestination.right = dest_rect[2]
        props.rcDestination.bottom = dest_rect[3]
        
        dwmapi.DwmUpdateThumbnailProperties(hthumb, ctypes.byref(props))

def unregister_thumbnail(hthumb: int) -> None:
    if hthumb:
        dwmapi.DwmUnregisterThumbnail(hthumb)
