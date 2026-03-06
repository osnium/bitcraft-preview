import base64
import ctypes
from ctypes import wintypes


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


crypt32 = ctypes.windll.crypt32
kernel32 = ctypes.windll.kernel32

CRYPTPROTECT_UI_FORBIDDEN = 0x1
CRYPTPROTECT_LOCAL_MACHINE = 0x4


def _to_data_blob(data: bytes) -> DATA_BLOB:
    if not data:
        return DATA_BLOB(0, None)
    buffer = (ctypes.c_byte * len(data))(*data)
    return DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))


def _blob_to_bytes(blob: DATA_BLOB) -> bytes:
    if blob.cbData == 0 or not blob.pbData:
        return b""
    return bytes(ctypes.string_at(blob.pbData, blob.cbData))


def protect_text(plain_text: str, use_machine_scope: bool = True) -> str:
    """Encrypt text using Windows DPAPI and return base64 payload."""
    input_blob = _to_data_blob(plain_text.encode("utf-8"))
    output_blob = DATA_BLOB()

    flags = CRYPTPROTECT_UI_FORBIDDEN
    if use_machine_scope:
        flags |= CRYPTPROTECT_LOCAL_MACHINE

    ok = crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        flags,
        ctypes.byref(output_blob),
    )
    if not ok:
        raise ctypes.WinError()

    try:
        encrypted = _blob_to_bytes(output_blob)
        return base64.b64encode(encrypted).decode("ascii")
    finally:
        if output_blob.pbData:
            kernel32.LocalFree(output_blob.pbData)


def unprotect_text(cipher_text_b64: str) -> str:
    """Decrypt a base64-encoded DPAPI payload and return plain text."""
    encrypted = base64.b64decode(cipher_text_b64.encode("ascii"))
    input_blob = _to_data_blob(encrypted)
    output_blob = DATA_BLOB()

    ok = crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    )
    if not ok:
        raise ctypes.WinError()

    try:
        plain = _blob_to_bytes(output_blob)
        return plain.decode("utf-8")
    finally:
        if output_blob.pbData:
            kernel32.LocalFree(output_blob.pbData)
