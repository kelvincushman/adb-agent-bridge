from pathlib import Path

import pytest
from conftest import FakeDevice

from adb_agent_bridge import ui

FIXTURE = (Path(__file__).parent / "fixtures" / "compose_screen.xml").read_text()


def test_parse_elements():
    els = ui.parse(FIXTURE)
    assert len(els) == 6
    post = next(e for e in els if e.text == "Post")
    assert post.id == "com.twitter.android:id/button_tweet"
    assert post.clickable
    assert post.bounds == (880, 120, 1040, 220)
    assert post.center == (960, 170)


def test_parse_flags():
    els = ui.parse(FIXTURE)
    gallery = next(e for e in els if e.id.endswith("/gallery"))
    assert gallery.scrollable and not gallery.clickable
    drafts = next(e for e in els if e.text == "Drafts")
    assert not drafts.clickable and drafts.enabled


def test_find_by_text_case_insensitive():
    els = ui.parse(FIXTURE)
    assert ui.find(els, text="post").id == "com.twitter.android:id/button_tweet"


def test_find_by_id_suffix():
    els = ui.parse(FIXTURE)
    assert ui.find(els, id="tweet_text").cls == "android.widget.EditText"


def test_find_by_desc():
    els = ui.parse(FIXTURE)
    assert ui.find(els, desc="add photos").clickable


def test_find_no_match_returns_none():
    assert ui.find(ui.parse(FIXTURE), text="does-not-exist") is None


def test_find_requires_a_criterion():
    with pytest.raises(ValueError):
        ui.find(ui.parse(FIXTURE))


def test_dump_retries_once_on_bad_output():
    d = FakeDevice(shell_returns=["", FIXTURE])
    els = ui.dump(d)
    assert len(els) == 6
    assert len(d.calls) == 2
    assert isinstance(d.last_dump_ms, int)


def test_dump_raises_after_two_failures():
    d = FakeDevice(shell_returns=["", "killed"])
    with pytest.raises(RuntimeError):
        ui.dump(d)
