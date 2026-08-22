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


def test_text_prefers_adbkeyboard_even_for_ascii():
    # measured: broadcast ~0.1-0.4s vs `input text` ~2s, so it wins when installed
    d = FakeDevice()
    actions.text(d, "hello world")
    b64 = base64.b64encode(b"hello world").decode()
    assert d.calls[-1] == f"am broadcast -a ADB_INPUT_B64 --es msg {b64}"


def test_text_falls_back_to_input_text_without_adbkeyboard():
    d = FakeDevice(shell_returns=["", "", "com.samsung.android.honeyboard/..."])
    actions.text(d, "it's (fine)")
    assert d.calls[-1] == "input text it\\'s%s\\(fine\\)"
    assert d.ime_unavailable
    actions.text(d, "again")  # no repeated IME probing once known-missing
    assert d.calls[-1] == "input text again"
    assert not any(c.startswith("ime ") for c in d.calls[-2:])


def test_text_percent_without_adbkeyboard_raises():
    import pytest
    d = FakeDevice(shell_returns=["", "", "honeyboard"])
    with pytest.raises(RuntimeError):
        actions.text(d, "Error: %s")


def test_text_unicode_uses_adbkeyboard_broadcast():
    d = FakeDevice()
    actions.text(d, "héllo 👋")
    b64 = base64.b64encode("héllo 👋".encode()).decode()
    assert d.calls == [
        f"ime enable {actions.ADB_IME}",
        f"ime set {actions.ADB_IME}",
        "settings get secure default_input_method",
        f"am broadcast -a ADB_INPUT_B64 --es msg {b64}",
    ]


def test_text_with_percent_avoids_input_text():
    # `input text` treats %s as a space placeholder; literal % must not hit it
    d = FakeDevice()
    actions.text(d, "Error: %s not found")
    assert d.calls[-1].startswith("am broadcast -a ADB_INPUT_B64")


def test_text_leading_dash_avoids_input_text():
    d = FakeDevice()
    actions.text(d, "-1")
    assert d.calls[-1].startswith("am broadcast -a ADB_INPUT_B64")


def test_ensure_ime_raises_when_adbkeyboard_missing():
    import pytest
    d = FakeDevice(shell_returns=["", "", "com.samsung.android.honeyboard/..."])
    with pytest.raises(RuntimeError):
        actions.text(d, "héllo")
    assert not d.ime_ready


def test_ime_switched_once_per_session():
    d = FakeDevice()
    actions.text(d, "héllo")
    actions.text(d, "wörld")
    assert len([c for c in d.calls if c.startswith("ime ")]) == 2  # enable+set, once


def test_text_clear_broadcasts_clear_first():
    d = FakeDevice()
    actions.text(d, "hi", clear=True)
    b64 = base64.b64encode(b"hi").decode()
    assert d.calls == [
        f"ime enable {actions.ADB_IME}",
        f"ime set {actions.ADB_IME}",
        "settings get secure default_input_method",
        "am broadcast -a ADB_CLEAR_TEXT",
        f"am broadcast -a ADB_INPUT_B64 --es msg {b64}",
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
