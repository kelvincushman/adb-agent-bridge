class FakeDevice:
    """Records shell commands; returns queued replies (empty string when exhausted)."""

    def __init__(self, shell_returns=None):
        self.calls = []
        self.ime_ready = False
        self._returns = list(shell_returns or [])

    def shell(self, cmd):
        self.calls.append(cmd)
        return self._returns.pop(0) if self._returns else ""

    def exec_out(self, cmd):
        self.calls.append(cmd)
        return b"PNGDATA"
