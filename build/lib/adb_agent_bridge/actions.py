"""Device actions: tap, text, swipe, key, screenshot."""
import base64
import time
from pathlib import Path

ADB_IME = "com.android.adbkeyboard/.AdbIME"
IME_SETTLE_S = 1.0  # seen live on SM-S721B: a broadcast right after `ime set`
                    # fires before the IME binds to the field and the text drops
_SHELL_SPECIALS = set("\\'\"`&|;<>()[]{}*?~#$^")


def tap(device, target):
    """target: an Element (taps its bounds center) or an (x, y) pair."""
    x, y = target.center if hasattr(target, "center") else target
    device.shell(f"input tap {x} {y}")


def text(device, s, clear=False):
    # measured on SM-S721B: `input text` injects ~35ms per character (2s for a
    # caption) while the ADBKeyboard broadcast commits any string in ~0.1s, so
    # the broadcast is the fast path for ALL text when ADBKeyboard is
    # installed; `input text` is the ASCII-only fallback for devices without it
    if not getattr(device, "ime_unavailable", False):
        try:
            _ensure_ime(device)
        except RuntimeError:
            device.ime_unavailable = True
    if getattr(device, "ime_unavailable", False):
        if clear:
            raise RuntimeError("clear=True needs ADBKeyboard — install it")
        if s:
            _input_text(device, s)
        return
    if clear:
        device.shell("am broadcast -a ADB_CLEAR_TEXT")
    if s:
        b64 = base64.b64encode(s.encode()).decode()  # dodges shell quoting
        device.shell(f"am broadcast -a ADB_INPUT_B64 --es msg {b64}")


def _input_text(device, s):
    # `input text` can't type these: % is a device-side space placeholder
    # (%s = space) and a leading - can parse as a flag
    if not (s.isascii() and s.isprintable() and "%" not in s and not s.startswith("-")):
        raise RuntimeError(f"cannot type {s!r} via input text — install ADBKeyboard")
    device.shell("input text " + _escape(s))


def swipe(device, x1, y1, x2, y2, ms=300):
    device.shell(f"input swipe {x1} {y1} {x2} {y2} {ms}")


def key(device, code):
    device.shell(f"input keyevent {code}")


def screenshot(device, path):
    Path(path).write_bytes(device.exec_out("screencap -p"))
    return path


def _escape(s):
    # `input text` takes %s for space; other specials need device-shell escaping
    return "".join(
        "%s" if c == " " else "\\" + c if c in _SHELL_SPECIALS else c for c in s
    )


def _ensure_ime(device):
    # switch once per session, no sleeps — `ime set` takes effect synchronously
    if device.ime_ready:
        return
    device.shell(f"ime enable {ADB_IME}")
    device.shell(f"ime set {ADB_IME}")
    if ADB_IME not in device.shell("settings get secure default_input_method"):
        raise RuntimeError(
            "ADBKeyboard did not activate — install it for unicode/clear= input"
        )
    time.sleep(IME_SETTLE_S)  # once per session: let the IME bind to the field
    device.ime_ready = True
