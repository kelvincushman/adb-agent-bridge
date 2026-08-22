"""Device actions: tap, text, swipe, key, screenshot."""
import base64
from pathlib import Path

ADB_IME = "com.android.adbkeyboard/.AdbIME"
_SHELL_SPECIALS = set("\\'\"`&|;<>()[]{}*?~#$^")


def tap(device, target):
    """target: an Element (taps its bounds center) or an (x, y) pair."""
    x, y = target.center if hasattr(target, "center") else target
    device.shell(f"input tap {x} {y}")


def text(device, s, clear=False):
    if clear:
        _ensure_ime(device)
        device.shell("am broadcast -a ADB_CLEAR_TEXT")
    if not s:
        return
    # fast path only for text `input text` types verbatim: % is a device-side
    # placeholder (%s = space) and a leading - can parse as a flag
    if s.isascii() and s.isprintable() and "%" not in s and not s.startswith("-"):
        device.shell("input text " + _escape(s))
    else:  # everything else via ADBKeyboard, base64 to dodge shell quoting
        _ensure_ime(device)
        b64 = base64.b64encode(s.encode()).decode()
        device.shell(f"am broadcast -a ADB_INPUT_B64 --es msg {b64}")


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
    device.ime_ready = True
