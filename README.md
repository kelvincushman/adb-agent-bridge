# ADB Agent Bridge

Fast, accurate agent→Android control over plain ADB. Nothing to install on the
device: the accessibility tree Android already exposes via `uiautomator dump`
gives every element's text, resource-id, content-desc, and bounds — so an agent
taps element centers instead of guessing pixels from screenshots.

By Kelvin Lee. Apache-2.0.

## Why

Vision-loop phone control (screenshot → model guesses x,y → tap) is slow
(2–5s/action) and inaccurate. The view hierarchy is free, structured, and
exact. Semantic addressing first; vision only as a fallback tier.

## Install

```sh
pip install adb-agent-bridge   # or: pip install -e . from a checkout
```

Requires `adb` on PATH and a device with USB debugging. For unicode/emoji text
input, install [ADBKeyboard](https://github.com/senzhk/ADBKeyBoard) on the
device (ASCII works without it).

## Usage

```python
from adb_agent_bridge import Bridge

b = Bridge()                      # or Bridge("SERIAL") with multiple devices
b.find(text="Post")               # -> Element(text='Post', id=..., bounds=...)
b.tap(b.find(text="Post"))        # taps the element's center — can't miss
b.tap((540, 1200))                # raw coordinates still available
b.text("hello world")             # instant, no IME dance
b.text("héllo 👋")                # unicode via ADBKeyboard broadcast
b.screenshot("screen.png")
```

CLI:

```sh
aab ui                    # dump elements (one per line, dump latency on stderr)
aab tap --text Post       # tap by text / --id / --desc, or: aab tap 540 1200
aab text "a caption"      # --clear to empty the field first
aab screenshot out.png
```

## How it works

- `ui()` runs `uiautomator dump` (~200–800ms) and parses the XML.
- `tap(element)` taps the element's bounds center via `input tap`.
- `text()` uses `input text` for ASCII; non-ASCII goes through ADBKeyboard's
  `ADB_INPUT_B64` broadcast. The IME is switched once per session — no sleeps.
- Dump latency is recorded per call (`Bridge.device.last_dump_ms`): measure
  before optimizing.

## Roadmap

- Set-of-Marks overlays (numbered screenshot annotations) for screens with a
  thin/absent view tree.
- A native on-device accessibility service is deliberately **not** built:
  `uiautomator dump` already provides the tree. It will only be added if
  measured dump latency proves insufficient at scale.

## Credits

ADBKeyboard by senzhk inspired the unicode input approach (see NOTICE). This
project contains no ADBKeyboard code.
