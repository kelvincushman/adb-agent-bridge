import io
from pathlib import Path

import pytest
from conftest import FakeDevice
from PIL import Image

from adb_agent_bridge import marks, ui

FIXTURE = (Path(__file__).parent / "fixtures" / "compose_screen.xml").read_text()


def _png_bytes(size=(1080, 2340)):
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format="PNG")
    return buf.getvalue()


def test_annotate_numbers_interactive_elements(tmp_path):
    els = ui.parse(FIXTURE)
    out = tmp_path / "marks.png"
    path, legend = marks.annotate(_png_bytes(), els, out)
    assert path == out and out.exists()
    assert Image.open(out).size == (1080, 2340)
    # clickable or scrollable, in document order: Post, EditText, gallery, ImageView
    assert [legend[n].id for n in sorted(legend)] == [
        "com.twitter.android:id/button_tweet",
        "com.twitter.android:id/tweet_text",
        "com.twitter.android:id/gallery",
        "",
    ]
    assert legend[1].center == (960, 170)  # model says "1" -> tap this


def test_grid_to_xy_square_cells():
    d = FakeDevice(shell_returns=["Physical size: 1080x2340"])
    assert marks.grid_to_xy(d, "A1") == (54, 54)
    assert marks.grid_to_xy(d, "C7") == (270, 702)
    assert len(d.calls) == 1  # screen size cached after first call


def test_grid_to_xy_rejects_out_of_range():
    d = FakeDevice(shell_returns=["Physical size: 1080x2340"])
    with pytest.raises(ValueError):
        marks.grid_to_xy(d, "Z1")
    with pytest.raises(ValueError):
        marks.grid_to_xy(d, "A99")
