"""Thin adb runner: one subprocess call per command.

ponytail: per-command adb spawn costs ~30ms while uiautomator dump costs
200-800ms; add a persistent shell only if last_dump_ms logging blames spawn.
"""
import subprocess


class Device:
    def __init__(self, serial=None):
        self.serial = serial
        self.ime_ready = False    # set by actions._ensure_ime, once per session
        self.last_dump_ms = None  # set by ui.dump: measure before optimizing

    def _run(self, args, binary=False):
        cmd = ["adb"] + (["-s", self.serial] if self.serial else []) + args
        r = subprocess.run(cmd, capture_output=True, timeout=15)
        if r.returncode != 0:
            err = r.stderr.decode(errors="replace").strip()
            raise RuntimeError(f"adb {args[0]} failed: {err or r.returncode}")
        return r.stdout if binary else r.stdout.decode(errors="replace")

    def shell(self, cmd):
        return self._run(["shell", cmd])

    def exec_out(self, cmd):
        return self._run(["exec-out", cmd], binary=True)
