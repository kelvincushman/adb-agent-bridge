"""`aab` CLI: ui | tap | text | screenshot."""
import argparse
import sys

from . import Bridge


def main(argv=None):
    p = argparse.ArgumentParser(prog="aab", description="ADB Agent Bridge")
    p.add_argument("-s", "--serial", help="device serial (adb -s)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ui", help="dump UI elements")

    t = sub.add_parser("tap", help="tap by --text/--id/--desc, --grid C7, or x y")
    t.add_argument("--text")
    t.add_argument("--id")
    t.add_argument("--desc")
    t.add_argument("--grid", help="grid cell like C7")
    t.add_argument("xy", nargs="*", type=int)

    m = sub.add_parser("marks", help="write a numbered Set-of-Marks screenshot")
    m.add_argument("path", nargs="?", default="marks.png")

    x = sub.add_parser("text", help="type text into the focused field")
    x.add_argument("string")
    x.add_argument("--clear", action="store_true", help="empty the field first")

    s = sub.add_parser("screenshot", help="save a PNG")
    s.add_argument("path")

    w = sub.add_parser("swipe", help="swipe x1 y1 x2 y2")
    w.add_argument("coords", nargs=4, type=int)
    w.add_argument("--ms", type=int, default=300)

    k = sub.add_parser("key", help="send a keyevent code (66 = ENTER)")
    k.add_argument("code", type=int)

    a = p.parse_args(argv)
    b = Bridge(a.serial)
    try:
        _dispatch(a, b, t)
    except (RuntimeError, ValueError) as e:  # ValueError: bad --grid cells
        sys.exit(f"aab: {e}")


def _dispatch(a, b, t):
    if a.cmd == "ui":
        for e in b.ui():
            flags = "".join(f" {f}" for f in ("clickable", "scrollable")
                            if getattr(e, f))
            print(f"{e.cls} text={e.text!r} id={e.id!r} desc={e.desc!r} "
                  f"center={e.center}{flags}")
        print(f"# dump took {b.device.last_dump_ms}ms ({b.backend})", file=sys.stderr)
    elif a.cmd == "tap":
        if len(a.xy) == 2:
            b.tap(tuple(a.xy))
        elif a.grid:
            b.tap(a.grid)
        elif a.text or a.id or a.desc:
            el = b.find(text=a.text, id=a.id, desc=a.desc)
            if el is None:
                sys.exit("aab: no matching element")
            b.tap(el)
        else:
            t.error("give --text/--id/--desc, --grid, or two coordinates")
    elif a.cmd == "marks":
        path, legend = b.marks(a.path)
        for n, e in legend.items():
            print(f"{n}: text={e.text!r} id={e.id!r} desc={e.desc!r} center={e.center}")
        print(f"wrote {path}")
    elif a.cmd == "text":
        b.text(a.string, clear=a.clear)
    elif a.cmd == "screenshot":
        b.screenshot(a.path)
    elif a.cmd == "swipe":
        b.swipe(*a.coords, ms=a.ms)
    elif a.cmd == "key":
        b.key(a.code)


if __name__ == "__main__":
    main()
