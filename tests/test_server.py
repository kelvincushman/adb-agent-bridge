import json
from pathlib import Path

from conftest import FakeDevice

from adb_agent_bridge import Bridge, server, ui

FIXTURE = (Path(__file__).parent / "fixtures" / "compose_screen.xml").read_text()


class FakeResponse:
    def __init__(self, body):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_connect_returns_port_when_server_pongs(monkeypatch):
    monkeypatch.setattr(server, "urlopen", lambda *a, **k: FakeResponse(b"pong"))
    d = FakeDevice()
    assert server.connect(d) == 7912
    assert d.calls == ["forward tcp:9008"]


def test_connect_returns_none_when_no_server(monkeypatch):
    def refuse(*a, **k):
        raise OSError("connection refused")
    monkeypatch.setattr(server, "urlopen", refuse)
    assert server.connect(FakeDevice()) is None


def test_server_dump_parses_hierarchy(monkeypatch):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "result": FIXTURE}).encode()
    monkeypatch.setattr(server, "urlopen", lambda *a, **k: FakeResponse(body))
    d = FakeDevice()
    els = server.dump(d, 7912)
    assert len(els) == 6
    assert isinstance(d.last_dump_ms, int)


def test_bridge_uses_server_when_present(monkeypatch):
    b = Bridge()
    b.device = FakeDevice()
    monkeypatch.setattr(server, "connect", lambda dev: 7912)
    monkeypatch.setattr(server, "dump", lambda dev, port: ui.parse(FIXTURE))
    assert len(b.ui()) == 6
    assert b.backend == "server"


def test_bridge_falls_back_when_server_dies(monkeypatch):
    b = Bridge()
    b.device = FakeDevice(shell_returns=[FIXTURE])
    monkeypatch.setattr(server, "connect", lambda dev: 7912)

    def die(dev, port):
        raise OSError("server gone")
    monkeypatch.setattr(server, "dump", die)
    els = b.ui()
    assert len(els) == 6  # served by the plain uiautomator dump fallback
    assert b.backend == "uiautomator"
