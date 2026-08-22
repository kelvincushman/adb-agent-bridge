"""Optional fast dump backend: an on-device uiautomator2-style server.

Install openatx/android-uiautomator-server's two APKs on a device and keep
its instrumentation running; it serves the same hierarchy XML as
`uiautomator dump` over HTTP in ~0.1-0.3s instead of 2-3s. Bridge probes
once per session and silently falls back to plain dumps when absent, so
devices without the server keep working unchanged.
"""
import json
import time
from urllib.request import Request, urlopen

from . import ui

DEVICE_PORT = "tcp:9008"  # android-uiautomator-server's fixed port
PING_TIMEOUT_S = 0.5
DUMP_TIMEOUT_S = 10


def connect(device):
    """Forwarded local port if the device runs a UI server, else None."""
    try:
        port = device.forward(DEVICE_PORT)
        with urlopen(f"http://127.0.0.1:{port}/ping", timeout=PING_TIMEOUT_S) as r:
            if r.read().strip().lower() == b"pong":
                return port
    except OSError:
        pass
    return None


def dump(device, port):
    """Hierarchy via the server — same XML as `uiautomator dump`, same parser."""
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1,
        "method": "dumpWindowHierarchy", "params": [False],
    }).encode()
    t0 = time.monotonic()
    req = Request(f"http://127.0.0.1:{port}/jsonrpc/0", data=payload,
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=DUMP_TIMEOUT_S) as r:
        xml_text = json.loads(r.read())["result"]
    device.last_dump_ms = round((time.monotonic() - t0) * 1000)
    return ui.parse(xml_text)
