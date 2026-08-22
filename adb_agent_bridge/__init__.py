"""ADB Agent Bridge: fast, accurate agent-to-Android control over plain ADB."""
from . import actions
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
        actions.tap(self.device, target)

    def text(self, s, clear=False):
        actions.text(self.device, s, clear=clear)

    def swipe(self, x1, y1, x2, y2, ms=300):
        actions.swipe(self.device, x1, y1, x2, y2, ms)

    def key(self, code):
        actions.key(self.device, code)

    def screenshot(self, path):
        return actions.screenshot(self.device, path)
