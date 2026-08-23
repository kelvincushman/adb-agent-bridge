"""Set-of-Marks overlays and grid addressing — the vision fallback tier."""
import io
import re

from PIL import Image, ImageDraw, ImageFont

GRID_COLS = 10  # columns A-J, square cells, rows numbered from 1 at the top


def annotate(png_bytes, elements, out_path):
    """Number every clickable/scrollable element on the screenshot.

    Returns (out_path, legend) where legend maps mark number -> Element:
    the model picks a number, you tap legend[n].
    """
    marked = [e for e in elements if e.clickable or e.scrollable]
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=28)
    for n, e in enumerate(marked, 1):
        left, top, right, bottom = e.bounds
        draw.rectangle((left, top, right, bottom), outline="red", width=3)
        label = str(n)
        draw.rectangle((left, top, left + 8 + 16 * len(label), top + 32), fill="red")
        draw.text((left + 4, top + 2), label, fill="white", font=font)
    img.save(out_path)
    return out_path, dict(enumerate(marked, 1))


def grid_to_xy(device, cell):
    """'C7' -> pixel center of that cell. ValueError if off-screen."""
    m = re.fullmatch(r"([A-Za-z])(\d+)", cell)
    if not m:
        raise ValueError(f"bad grid cell {cell!r}, expected like 'C7'")
    col = ord(m.group(1).upper()) - ord("A")
    row = int(m.group(2)) - 1
    w, h = _screen_size(device)
    cw = w / GRID_COLS
    x, y = round((col + 0.5) * cw), round((row + 0.5) * cw)
    if col >= GRID_COLS or row < 0 or y > h:
        raise ValueError(f"grid cell {cell!r} is off a {w}x{h} screen")
    return (x, y)


def _screen_size(device):
    if getattr(device, "screen_size", None) is None:
        out = device.shell("wm size")
        # input coords follow the override resolution when one is set
        m = (re.search(r"Override size:\s*(\d+)x(\d+)", out)
             or re.search(r"(\d+)x(\d+)", out))
        if not m:
            raise RuntimeError("could not read screen size from `wm size`")
        device.screen_size = (int(m.group(1)), int(m.group(2)))
    return device.screen_size
