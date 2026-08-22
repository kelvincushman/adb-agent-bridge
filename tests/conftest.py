import pytest


@pytest.fixture(autouse=True)
def _no_ime_settle(monkeypatch):
    from adb_agent_bridge import actions
    monkeypatch.setattr(actions, "IME_SETTLE_S", 0)


class FakeDevice:
    """Records shell commands; returns queued replies (empty string when exhausted)."""

    def __init__(self, shell_returns=None):
        self.calls = []
        self.ime_ready = False
        self._returns = list(shell_returns or [])

    def shell(self, cmd):
        self.calls.append(cmd)
        if self._returns:
            return self._returns.pop(0)
        if cmd == "settings get secure default_input_method":
            return "com.android.adbkeyboard/.AdbIME"  # pretend ADBKeyboard is active
        return ""

    def exec_out(self, cmd):
        self.calls.append(cmd)
        return b"PNGDATA"

    def forward(self, remote):
        self.calls.append(f"forward {remote}")
        return 7912
