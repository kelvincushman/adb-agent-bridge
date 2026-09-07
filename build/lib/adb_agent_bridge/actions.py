"""Device actions: tap, text, swipe, key, screenshot."""
import base64
import re
import time
from pathlib import Path
from urllib.parse import quote, urlparse

ADB_IME = "com.android.adbkeyboard/.AdbIME"
IME_SETTLE_S = 1.0  # seen live on SM-S721B: a broadcast right after `ime set`
                    # fires before the IME binds to the field and the text drops
_SHELL_SPECIALS = set("\\'\"`&|;<>()[]{}*?~#$^")
_PHONE = re.compile(r"^\+?[0-9][0-9 ()-]{2,30}$")
_URI_SCHEMES = {"http", "https", "sms", "smsto", "tel", "geo", "mailto"}


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


def open_uri(device, uri, package=None):
    """Open an allowlisted URI through Android's VIEW intent.

    Values are device-shell quoted as individual arguments. Arbitrary shell
    commands are intentionally not part of the public bridge surface.
    """
    parsed = urlparse(uri)
    if parsed.scheme.lower() not in _URI_SCHEMES:
        raise ValueError(f"unsupported URI scheme: {parsed.scheme or '(none)'}")
    args = ["am", "start", "-W", "-a", "android.intent.action.VIEW", "-d", uri]
    if package:
        if not re.fullmatch(r"[A-Za-z0-9_.]+", package):
            raise ValueError("invalid Android package name")
        args.extend(["-p", package])
    return device.shell_argv(args)


def compose_sms(device, recipient, body=""):
    """Open the default SMS composer. This never presses Send."""
    if not _PHONE.fullmatch(recipient):
        raise ValueError("recipient must be a phone number")
    number = re.sub(r"[ ()-]", "", recipient)
    uri = f"smsto:{number}"
    if body:
        uri += f"?body={quote(body, safe='')}"
    return open_uri(device, uri)


def compose_whatsapp(device, recipient, body=""):
    """Open a WhatsApp conversation/composer. This never presses Send."""
    if not _PHONE.fullmatch(recipient):
        raise ValueError("recipient must be a phone number with country code")
    number = re.sub(r"[^0-9]", "", recipient)
    uri = f"https://wa.me/{number}"
    if body:
        uri += f"?text={quote(body, safe='')}"
    return open_uri(device, uri, package="com.whatsapp")


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
