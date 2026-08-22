"""Parse `uiautomator dump` XML into elements and find them semantically."""
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass

_BOUNDS = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")
# dump to a file then cat: `uiautomator dump /dev/tty` is unreliable across Android versions
_DUMP_CMD = "uiautomator dump /sdcard/aab_ui.xml >/dev/null 2>&1 && cat /sdcard/aab_ui.xml"


@dataclass(frozen=True)
class Element:
    text: str
    id: str
    desc: str
    cls: str
    bounds: tuple
    clickable: bool
    scrollable: bool
    enabled: bool

    @property
    def center(self):
        left, top, right, bottom = self.bounds
        return ((left + right) // 2, (top + bottom) // 2)


def parse(xml_text):
    els = []
    for node in ET.fromstring(xml_text).iter("node"):
        m = _BOUNDS.match(node.get("bounds", ""))
        if not m:
            continue
        left, top, right, bottom = map(int, m.groups())
        els.append(Element(
            text=node.get("text", ""),
            id=node.get("resource-id", ""),
            desc=node.get("content-desc", ""),
            cls=node.get("class", ""),
            bounds=(left, top, right, bottom),
            clickable=node.get("clickable") == "true",
            scrollable=node.get("scrollable") == "true",
            enabled=node.get("enabled") == "true",
        ))
    return els


def dump(device):
    for _ in range(2):  # ponytail: one retry covers dumps that fail mid-animation
        t0 = time.monotonic()
        xml_text = device.shell(_DUMP_CMD)
        device.last_dump_ms = round((time.monotonic() - t0) * 1000)
        if "<hierarchy" in xml_text:
            return parse(xml_text)
    raise RuntimeError("uiautomator dump failed twice; fall back to screenshot/vision tier")


def find(elements, text=None, id=None, desc=None):
    """First element matching all given criteria: text/desc substring
    (case-insensitive), id exact or suffix after the last '/'."""
    if text is None and id is None and desc is None:
        raise ValueError("find() needs text=, id= or desc=")
    for e in elements:
        if text is not None and text.lower() not in e.text.lower():
            continue
        if id is not None and e.id != id and not e.id.endswith("/" + id):
            continue
        if desc is not None and desc.lower() not in e.desc.lower():
            continue
        return e
    return None
