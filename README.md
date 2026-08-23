# ADB Agent Bridge

Fast, accurate agent→Android control over plain ADB. Nothing to install on the
device: the accessibility tree Android already exposes via `uiautomator dump`
gives every element's text, resource-id, content-desc, and bounds — so an AI
agent taps element centers instead of guessing pixels from screenshots.

**Developed by [Kelvin Lee](https://github.com/kelvincushman)** · Apache-2.0

## Why this exists

This tool came out of running a real fleet of Android phones driven by AI
agents — [ContentSwarm](https://github.com/kelvincushman/ContentSwarm), an
open phone-agent framework for content automation, with
[Orphus](https://github.com/kelvincushman/orphus) as the agent harness
driving it. The stack we inherited was built the way most phone automation
is: **for humans watching a screen, not for agents**. Two things made it
slow and unreliable:

- **The blind pixel loop.** Every action meant: capture a 1–2 MB screenshot,
  send it to a vision model, have the model guess an (x, y) coordinate, then
  `input tap` and hope. 2–5 seconds per action, and vision models regress raw
  pixel coordinates poorly — taps missed, flows derailed, retries compounded.
- **The text dance.** Typing one caption meant swapping the IME with four
  1-second sleeps (~4s per field), and the on-screen keyboard hid the app's
  media picker at exactly the wrong moment.

The fix turned out to require almost nothing new. Android already ships the
whole answer over plain ADB, on every device, with zero on-device install:
`uiautomator dump` returns the full view hierarchy — the same tree an
accessibility service sees — as XML. Parse it host-side, find the element by
its text or id, tap its bounds center. **Element-center taps can't miss.**
Text goes through a broadcast to [ADBKeyboard](https://github.com/senzhk/ADBKeyBoard)
in ~100ms, with the IME switched once per session instead of once per field.

The guiding principle throughout: *the laziest solution that actually works*.
No custom accessibility service, no signed APKs, no on-device daemon — until
measured latency proves one is needed. Every dump is timed
(`Bridge.device.last_dump_ms`) so that decision is made with data, not vibes.

## The three addressing tiers

1. **Semantic** (default): `find(text="Post")` → tap the element's center.
   Exact, layout-robust, no vision model in the loop.
2. **Set-of-Marks / grid** (vision fallback): when the tree is thin (games,
   canvas, some WebViews), `marks()` draws numbered boxes on a screenshot —
   the model picks a number, you tap that element. Or address a 10-column
   grid cell like `"C7"`.
3. **Raw coordinates**: `tap((x, y))` still works when you need it.

## Install

```sh
pip install "adb-agent-bridge @ git+https://github.com/kelvincushman/adb-agent-bridge"
# or from a checkout: pip install -e .
```

(Not yet on PyPI — install from git. Pin a commit SHA with `@<sha>` for
reproducible installs.)

Requirements:

- `adb` on the host PATH, device with USB debugging enabled.
- [ADBKeyboard](https://github.com/senzhk/ADBKeyBoard) on the device for fast
  and unicode text input (recommended). Without it, plain-ASCII text still
  works via `input text`.

## Quick start

```python
from adb_agent_bridge import Bridge

b = Bridge()                      # or Bridge("SERIAL") with multiple devices
b.ui()                            # -> [Element(text=..., id=..., bounds=...), ...]
b.find(text="Post")               # first element whose text matches
b.tap(b.find(text="Post"))        # taps the element's center — can't miss
b.tap((540, 1200))                # raw coordinates
b.tap("C7")                       # grid cell (10 square columns A-J, rows from 1)
b.text("hello world")             # ~100ms, no IME dance
b.text("héllo 👋", clear=True)    # unicode/emoji; clear empties the field first
b.swipe(540, 1600, 540, 400)      # scroll
b.key(66)                         # keyevent (66 = ENTER)
b.screenshot("screen.png")

path, legend = b.marks()          # numbered Set-of-Marks screenshot; the
b.tap(legend[3])                  # vision model picks a number, you tap it

b.prefetch_ui()                   # start the next dump in the background
# ... do other work (e.g. the model decides the next action) ...
b.ui()                            # returns the prefetched result instantly
```

CLI (installed as `aab`):

```sh
aab ui                    # dump elements, one per line (dump latency on stderr)
aab tap --text Post       # tap by text / --id / --desc
aab tap --grid C7         # or grid cell, or: aab tap 540 1200
aab text "a caption"      # --clear to empty the field first
aab marks annotated.png   # numbered overlay + legend for the vision fallback
aab screenshot out.png
aab swipe 540 1600 540 400
aab key 66                # keyevent (66 = ENTER)
aab -s SERIAL ...         # pick a device when several are connected
```

After a session, restore the device's normal keyboard with
`adb shell ime reset` (the bridge leaves ADBKeyboard active for speed).

## Measured performance

All numbers measured live on a Samsung SM-S721B (Galaxy S24 FE), host on USB:

| Operation | Cost | Notes |
|---|---|---|
| `tap` / `swipe` / `key` | ~0.1s | `input` is cheap on modern Android |
| `text()` via ADBKeyboard | ~0.1s | any length, any unicode |
| first `text()` of a session | ~1.5s | one-time IME switch + settle wait |
| `screenshot()` | ~0.8s | `screencap -p` over exec-out |
| `ui()` — `uiautomator dump` | **2.1–3.0s** | the bottleneck: fresh uiautomator process per call |
| `ui()` on very heavy screens | up to ~6s | seen on Facebook Marketplace's tree |
| old vision loop (replaced) | 2–5s/action | plus missed taps and retries |
| old IME text dance (replaced) | ~4s/field | now ~0.1s |

Two findings worth knowing:

- `input text` costs ~35ms **per character** (key events are injected one by
  one), so a 60-char caption takes ~2s. The ADBKeyboard broadcast commits the
  whole string at once — that's why it's the primary text path.
- Switching the IME and broadcasting immediately drops the text: the IME
  hasn't bound to the field yet. One settle wait after the once-per-session
  switch fixes what the old stack worked around with four sleeps per field.

An agent action cycle (dump → find → tap) is therefore ~2.5s, ~95% of it the
dump. Two ways to attack that, both built in:

- **Prefetch** (`prefetch_ui()`): start the next dump right after an action so
  it overlaps the caller's own work — in an agent loop the model's 1–3s of
  thinking hides most of the dump for free. Roughly 2× on real flows, no
  device changes.
- **The optional fast backend** below: ~5–8× flat, one APK install per device.

## Optional fast backend (fleet phones)

Plain devices need nothing and keep working unchanged. For sub-second action
cycles, install [openatx/android-uiautomator-server](https://github.com/openatx/android-uiautomator-server)
(MIT) on the device and keep its instrumentation running:

```sh
adb install app-uiautomator.apk
adb install app-uiautomator-test.apk
adb shell am instrument -w com.github.uiautomator.test/androidx.test.runner.AndroidJUnitRunner
```

It keeps uiautomator alive and serves the same hierarchy XML over HTTP —
Bridge probes for it once per session (`adb forward` + `/ping`) and uses it
automatically; `aab ui` reports which backend served the dump, and if the
server dies mid-session the bridge falls back to plain dumps. Expected dumps:
~0.1–0.3s instead of 2–3s. **Not yet verified against real hardware** — the
plain-ADB path remains the default and the regression baseline.

## Limitations

- Thin or absent view trees (games, canvas-drawn UIs, some WebViews) — use
  the Set-of-Marks / grid fallback tier.
- `FLAG_SECURE` screens refuse screenshots (banking apps, private modes).
- `uiautomator dump` can fail mid-animation; the bridge retries once, then
  raises so callers can fall back to the vision tier.
- Unicode text, `clear=`, and fast typing need ADBKeyboard installed.

## Roadmap

- **Fleet-phone verification of the fast backend** — the HTTP backend ships
  mock-tested; its first live run happens on a fleet device, not a personal
  phone.
- **[ContentSwarm](https://github.com/kelvincushman/ContentSwarm)
  integration** — element-target taps, layout-robust flow recording with
  per-replay run reports, a `/ui` endpoint, and prefetch-during-model-thinking
  — lives downstream of this library, driven by
  [Orphus](https://github.com/kelvincushman/orphus) agents.

## License & credits

Apache-2.0, © 2026 Kelvin Lee. See `LICENSE` and `NOTICE` — redistributions
must retain the attribution notice.

ADBKeyboard by [senzhk](https://github.com/senzhk/ADBKeyBoard) inspired the
unicode input approach and is driven via its documented broadcast intents.
This project contains no ADBKeyboard code.
