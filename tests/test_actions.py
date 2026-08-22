import base64

from conftest import FakeDevice

from adb_agent_bridge import actions, ui

ELEMENT = ui.Element(
    text="Post", id="", desc="", cls="", bounds=(880, 120, 1040, 220),
    clickable=True, scrollable=False, enabled=True,
)


def test_tap_element_center():
    d = FakeDevice()
    actions.tap(d, ELEMENT)
    assert d.calls == ["input tap 960 170"]


def test_tap_xy():
    d = FakeDevice()
    actions.tap(d, (540, 1200))
    assert d.calls == ["input tap 540 1200"]


def test_text_ascii_fast_path_escapes():
    d = FakeDevice()
    actions.text(d, "it's (fine)")
    assert d.calls == ["input text it\\'s%s\\(fine\\)"]


def test_text_unicode_uses_adbkeyboard_broadcast():
    d = FakeDevice()
    actions.text(d, "héllo 👋")
    b64 = base64.b64encode("héllo 👋".encode()).decode()
    assert d.calls == [
        f"ime enable {actions.ADB_IME}",
        f"ime set {actions.ADB_IME}",
        f"am broadcast -a ADB_INPUT_B64 --es msg {b64}",
    ]


def test_ime_switched_once_per_session():
    d = FakeDevice()
    actions.text(d, "héllo")
    actions.text(d, "wörld")
    assert len([c for c in d.calls if c.startswith("ime ")]) == 2  # enable+set, once


def test_text_clear_broadcasts_clear_first():
    d = FakeDevice()
    actions.text(d, "hi", clear=True)
    assert d.calls == [
        f"ime enable {actions.ADB_IME}",
        f"ime set {actions.ADB_IME}",
        "am broadcast -a ADB_CLEAR_TEXT",
        "input text hi",
    ]


def test_swipe_and_key():
    d = FakeDevice()
    actions.swipe(d, 540, 1600, 540, 400)
    actions.key(d, 66)
    assert d.calls == ["input swipe 540 1600 540 400 300", "input keyevent 66"]


def test_screenshot_writes_png_bytes(tmp_path):
    d = FakeDevice()
    out = tmp_path / "s.png"
    actions.screenshot(d, out)
    assert out.read_bytes() == b"PNGDATA"
    assert d.calls == ["screencap -p"]
