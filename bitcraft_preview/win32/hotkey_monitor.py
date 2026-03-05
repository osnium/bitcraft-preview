import ctypes
import logging


logger = logging.getLogger("bitcraft_preview")
user32 = ctypes.windll.user32


# Modifier token -> virtual key code.
MODIFIER_VK = {
    "CTRL": 0x11,
    "CONTROL": 0x11,
    "SHIFT": 0x10,
    "ALT": 0x12,
    "WIN": 0x5B,
    "WINDOWS": 0x5B,
}


# Common non-alphanumeric keys.
KEY_VK = {
    "TAB": 0x09,
    "SPACE": 0x20,
    "ENTER": 0x0D,
    "RETURN": 0x0D,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "UP": 0x26,
    "DOWN": 0x28,
    "LEFT": 0x25,
    "RIGHT": 0x27,
}


MOUSE_ALIAS = {
    "MOUSE1": 0x01,
    "MOUSE2": 0x02,
    "MOUSE3": 0x04,
    "MOUSE4": 0x05,  # XBUTTON1
    "MOUSE5": 0x06,  # XBUTTON2
    "XBUTTON1": 0x05,
    "XBUTTON2": 0x06,
}


def _vk_for_token(token: str) -> int | None:
    tok = token.upper().strip()
    if not tok:
        return None

    if tok in MOUSE_ALIAS:
        return MOUSE_ALIAS[tok]

    if len(tok) == 1 and "A" <= tok <= "Z":
        return ord(tok)

    if len(tok) == 1 and "0" <= tok <= "9":
        return ord(tok)

    if tok.startswith("F") and tok[1:].isdigit():
        fn_index = int(tok[1:])
        if 1 <= fn_index <= 24:
            return 0x70 + (fn_index - 1)

    return KEY_VK.get(tok)


def parse_hotkey_spec(spec: str | None) -> tuple[list[int], int] | None:
    if spec is None:
        return None

    tokens = [t.strip() for t in spec.replace(" ", "").split("+") if t.strip()]
    if not tokens:
        return None

    modifiers: list[int] = []
    main_key: int | None = None

    for token in tokens:
        upper = token.upper()
        if upper in MODIFIER_VK:
            modifiers.append(MODIFIER_VK[upper])
            continue

        vk = _vk_for_token(upper)
        if vk is None:
            return None
        if main_key is not None:
            return None
        main_key = vk

    if main_key is None:
        return None

    deduped_modifiers = list(dict.fromkeys(modifiers))
    return deduped_modifiers, main_key


class GlobalHotkeyMonitor:
    """Poll-based global hotkey monitor supporting keyboard and mouse buttons."""

    def __init__(self):
        self._modifiers: list[int] = []
        self._main_key: int | None = None
        self._spec: str = ""
        self._pressed = False

    @property
    def spec(self) -> str:
        return self._spec

    def set_hotkey(self, spec: str | None) -> bool:
        parsed = parse_hotkey_spec(spec)
        if not parsed:
            logger.warning("Ignoring invalid switch_window_hotkey value: %r", spec)
            return False

        modifiers, main_key = parsed
        self._modifiers = modifiers
        self._main_key = main_key
        self._spec = (spec or "").strip()
        self._pressed = False
        logger.info("Updated switch-window hotkey to '%s'", self._spec)
        return True

    def poll_triggered(self) -> bool:
        if self._main_key is None:
            return False

        # Bit 0x8000 set means key is currently down.
        main_down = bool(user32.GetAsyncKeyState(self._main_key) & 0x8000)
        mods_down = all(user32.GetAsyncKeyState(vk) & 0x8000 for vk in self._modifiers)
        now_pressed = main_down and mods_down

        # Rising-edge detection prevents repeats while holding the key/button.
        triggered = now_pressed and not self._pressed
        self._pressed = now_pressed
        return triggered
