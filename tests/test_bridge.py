from pathlib import Path

from conftest import FakeDevice

from adb_agent_bridge import Bridge

FIXTURE = (Path(__file__).parent / "fixtures" / "compose_screen.xml").read_text()


def _plain_bridge(shell_returns):
    b = Bridge()
    b.device = FakeDevice(shell_returns=shell_returns)
    b._server_port = None  # no server probing in tests
    return b


def test_prefetch_ui_serves_the_next_ui_call():
    b = _plain_bridge([FIXTURE])
    b.prefetch_ui()
    assert len(b.ui()) == 6
    assert len(b.device.calls) == 1  # served from the prefetched dump


def test_failed_prefetch_falls_back_to_fresh_dump():
    b = _plain_bridge(["", "bad", FIXTURE])
    b.prefetch_ui()  # both dump attempts fail; error is boxed, not raised
    assert len(b.ui()) == 6  # fresh dump succeeds
    assert len(b.device.calls) == 3
