# SendInput через Win32 API с hardware scan codes (для DirectX игр).

import ctypes
import time
from ctypes import wintypes

INPUT_KEYBOARD = 1
INPUT_MOUSE = 0

KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

SCAN_CODES = {
    "a": 0x1E, "b": 0x30, "c": 0x2E, "d": 0x20, "e": 0x12,
    "f": 0x21, "g": 0x22, "h": 0x23, "i": 0x17, "j": 0x24,
    "k": 0x25, "l": 0x26, "m": 0x32, "n": 0x31, "o": 0x18,
    "p": 0x19, "q": 0x10, "r": 0x13, "s": 0x1F, "t": 0x14,
    "u": 0x16, "v": 0x2F, "w": 0x11, "x": 0x2D, "y": 0x15,
    "z": 0x2C,
    "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05,
    "5": 0x06, "6": 0x07, "7": 0x08, "8": 0x09,
    "9": 0x0A, "0": 0x0B,
    "space": 0x39,
    "enter": 0x1C,
    "esc": 0x01,
    "tab": 0x0F,
    "shift": 0x2A,
    "ctrl": 0x1D,
    "alt": 0x38,
    "up": 0x48, "down": 0x50, "left": 0x4B, "right": 0x4D,
}


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", _MOUSEINPUT),
        ("ki", _KEYBDINPUT),
        ("hi", _HARDWAREINPUT),
    ]


class _INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", _INPUT_UNION),
    ]


_user32 = ctypes.WinDLL("user32", use_last_error=True)
_SendInput = _user32.SendInput
_SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(_INPUT), ctypes.c_int)
_SendInput.restype = wintypes.UINT


def _key_event(scan_code: int, down: bool) -> None:
    flags = KEYEVENTF_SCANCODE
    if not down:
        flags |= KEYEVENTF_KEYUP
    inp = _INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki = _KEYBDINPUT(
        wVk=0,
        wScan=scan_code,
        dwFlags=flags,
        time=0,
        dwExtraInfo=None,
    )
    n = _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))
    if n != 1:
        err = ctypes.get_last_error()
        raise OSError(f"SendInput failed (err={err}). Запусти от АДМИНА.")


def tap(key: str, hold: float = 0.05) -> None:
    sc = SCAN_CODES.get(key.lower())
    if sc is None:
        raise ValueError(f"Неизвестная клавиша: {key}")
    _key_event(sc, True)
    time.sleep(hold)
    _key_event(sc, False)


def key_down(key: str) -> None:
    sc = SCAN_CODES.get(key.lower())
    if sc is None:
        raise ValueError(f"Неизвестная клавиша: {key}")
    _key_event(sc, True)


def key_up(key: str) -> None:
    sc = SCAN_CODES.get(key.lower())
    if sc is None:
        raise ValueError(f"Неизвестная клавиша: {key}")
    _key_event(sc, False)


def click(x: int, y: int) -> None:
    _user32.SetCursorPos(int(x), int(y))
    time.sleep(0.05)

    inp = _INPUT()
    inp.type = INPUT_MOUSE
    inp.mi = _MOUSEINPUT(
        dx=0, dy=0, mouseData=0,
        dwFlags=MOUSEEVENTF_LEFTDOWN, time=0, dwExtraInfo=None,
    )
    _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))
    time.sleep(0.05)

    inp.mi.dwFlags = MOUSEEVENTF_LEFTUP
    _SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False
