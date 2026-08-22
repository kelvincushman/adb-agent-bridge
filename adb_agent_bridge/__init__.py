"""ADB Agent Bridge: fast, accurate agent-to-Android control over plain ADB."""
from . import actions
from . import marks as _marks
from . import ui as _ui
from .device import Device
from .ui import Element

__all__ = ["Bridge", "Device", "Element"]


class Bridge:
    def __init__(self, serial=None):
        self.device = Device(serial)

    def ui(self):
        return _ui.dump(self.device)

    def find(self, text=None, id=None, desc=None):
        return _ui.find(self.ui(), text=text, id=id, desc=desc)

    def tap(self, target):
        """target: Element, (x, y), or a grid cell string like 'C7'."""
        if isinstance(target, str):
            target = _marks.grid_to_xy(self.device, target)
        actions.tap(self.device, target)

    def marks(self, out_path="marks.png"):
        els = self.ui()  # slow dump first, screenshot right after: overlay matches
        return _marks.annotate(self.device.exec_out("screencap -p"), els, out_path)

    def text(self, s, clear=False):
        actions.text(self.device, s, clear=clear)

    def swipe(self, x1, y1, x2, y2, ms=300):
        actions.swipe(self.device, x1, y1, x2, y2, ms)

    def key(self, code):
        actions.key(self.device, code)

    def screenshot(self, path):
        return actions.screenshot(self.device, path)
