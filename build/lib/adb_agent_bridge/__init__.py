"""ADB Agent Bridge: fast, accurate agent-to-Android control over plain ADB."""
import threading

from . import actions
from . import marks as _marks
from . import server as _server
from . import ui as _ui
from .device import Device
from .ui import Element

__all__ = ["Bridge", "Device", "Element"]


class Bridge:
    def __init__(self, serial=None):
        self.device = Device(serial)
        self._server_port = False  # False = not probed, None = no server, int = port
        self._prefetch = None

    @property
    def backend(self):
        return "server" if self._server_port else "uiautomator"

    def ui(self):
        if self._prefetch is not None:
            thread, box = self._prefetch
            self._prefetch = None
            thread.join()
            if "els" in box:
                return box["els"]
            # prefetch failed — fall through to a fresh dump
        return self._dump()

    def prefetch_ui(self):
        """Start the next dump in the background; the next ui() returns it.

        Call right after an action so the ~2-3s dump overlaps the caller's own
        work (e.g. an LLM deciding the next step) instead of adding to it.
        """
        box = {}

        def run():
            try:
                box["els"] = self._dump()
            except Exception as e:
                box["err"] = e

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        self._prefetch = (thread, box)

    def _dump(self):
        if self._server_port is False:
            self._server_port = _server.connect(self.device)
        if self._server_port is not None:
            try:
                return _server.dump(self.device, self._server_port)
            except OSError:
                self._server_port = None  # server gone — plain dumps from here on
        return _ui.dump(self.device)

    def find(self, text=None, id=None, desc=None):
        return _ui.find(self.ui(), text=text, id=id, desc=desc)

    def tap(self, target):
        """target: Element, (x, y), or a grid cell string like 'C7'."""
        if isinstance(target, str):
            target = _marks.grid_to_xy(self.device, target)
        actions.tap(self.device, target)

    def text(self, s, clear=False):
        actions.text(self.device, s, clear=clear)

    def swipe(self, x1, y1, x2, y2, ms=300):
        actions.swipe(self.device, x1, y1, x2, y2, ms)

    def key(self, code):
        actions.key(self.device, code)

    def screenshot(self, path):
        return actions.screenshot(self.device, path)

    def marks(self, out_path="marks.png"):
        els = self.ui()  # slow dump first, screenshot right after: overlay matches
        return _marks.annotate(self.device.exec_out("screencap -p"), els, out_path)
