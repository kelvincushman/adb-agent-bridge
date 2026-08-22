# Build Plan: ADB Agent Bridge (ponytail / YAGNI edition)

> Canonical build spec. After approval, copy to
> `/Users/kelvincushman/adb-agent-bridge/PLAN.md` and commit it, so a fresh
> (cleared-context) session can build it cold.

## Context

ContentSwarm's phone control is slow and inaccurate because it was built for
humans, not agents:

- **Blind pixel loop:** `screencap -p` (1–2 MB, ~0.5–1s) → vision model guesses
  `(x,y)` (~1–3s) → `input tap`. Models regress raw pixels poorly, so taps miss.
- **Text dance:** `phone_agent/actions/handler.py::_handle_type` swaps IME with
  **four 1s sleeps (~4s) per field**, and the IME hides app media pickers (seen live).

We want fast, accurate agent→phone control, packaged as a public reusable tool
**ADB Agent Bridge** (`kelvincushman/adb-agent-bridge`, **Apache-2.0**,
attribution to Kelvin Lee in `LICENSE`+`NOTICE`+README; clean-room, ADBKeyboard
credited as inspiration only).

## The ponytail reset (why v1 builds almost nothing new)

My first plan was a signed Kotlin accessibility service + companion IME + socket
server + overlay app + CI signing + Python client — hundreds of lines of
net-new Android across 5 milestones. The laziness ladder kills most of it:

**"Already a native feature?" — yes.** Android ships, over plain ADB, on every
device with nothing installed:
- **`uiautomator dump`** → full view hierarchy as XML: every node's `text`,
  `resource-id`, `content-desc`, `class`, `bounds`, `clickable`, `scrollable`.
  **This IS the accessibility tree — for free.** Tier-1 semantic addressing with
  zero on-device code: parse XML → find element by text/id → `input tap <center>`.
  Element-center taps can't miss.
- **`input text` / `input tap` / `input swipe` / `input keyevent`** — all built in.
- **`ADBKeyboard`** (already installed on the phone) handles the unicode text
  case via broadcast. The 4s cost was **our sleeps**, not the keyboard — switch
  IME **once per session** and drop the sleeps.

**"Already a dependency?" — yes.** `Pillow` is already in ContentSwarm.
Set-of-Marks (tier 2) is host-side: screenshot + the `bounds` from
`uiautomator dump` → PIL draws numbered boxes → model picks a number → tap that
element's center. No on-device overlay app.

**Result:** the entire accuracy + text-speed win needs **one host-side Python
package** and **no Android build, no APK signing, no accessibility-service
maintenance, no install step** (uiautomator is already there). We only build the
native Kotlin service later *if measured latency demands it* (see v2).

## v1 — ADB Agent Bridge as a pure-Python library (ships this week)

Repo `kelvincushman/adb-agent-bridge`:

```
adb-agent-bridge/
├── LICENSE            # Apache-2.0
├── NOTICE             # "ADB Agent Bridge © 2026 Kelvin Lee" + attribution requirement
├── README.md          # Kelvin Lee dev; install; usage; credit; ADBKeyboard-inspiration note
├── pyproject.toml     # package: adb-agent-bridge; console script: aab; deps: Pillow only
├── adb_agent_bridge/
│   ├── __init__.py
│   ├── device.py      # thin adb runner: persistent `adb shell` per device (one process, piped cmds — avoids per-command adb spawn)
│   ├── ui.py          # `dump()` -> parse uiautomator XML -> [Element{id,text,desc,cls,bounds,clickable,...}]; find(text=/id=/desc=)
│   ├── actions.py     # tap(element|xy|grid), text(str) [input text ASCII fast-path; ADBKeyboard broadcast for unicode; IME switched once], swipe, key, screenshot
│   ├── marks.py       # Set-of-Marks: screenshot + bounds -> PIL numbered overlay + legend
│   └── cli.py         # `aab ui|tap|text|marks|screenshot <serial>` for standalone use
└── tests/             # pytest against captured uiautomator XML fixtures (no device needed)
```

Core API (`Bridge(serial)`):
- `ui()` → list of elements (parsed `uiautomator dump`)
- `find(text=/id=/desc=)` → element; `tap(element)` → `input tap` at bounds center
- `tap(xy=)` / `tap(grid="C7")`
- `text(s, element=None, clear=False)` → ASCII via `input text`; unicode via ADBKeyboard broadcast; IME switched once, cached, no per-call sleeps
- `marks()` → (annotated_png_path, legend) for the vision fallback tier
- `swipe(...)`, `key(code)`, `screenshot(path)`

Three-tier addressing, same as before but all host-side: **semantic (`find`+`tap`) → marks/grid → raw xy**.

**Latency reality (measure, don't guess):** `uiautomator dump` is ~200–800ms —
slower than a socket service would be, but far faster and far more accurate than
the 2–5s vision loop, at zero build cost. Ship it, measure it, and only escalate
to v2 if the dump time is the proven bottleneck.

## v2 — native service, ONLY if v1 latency proves insufficient (documented, not built now)

If measured `uiautomator dump` latency is the bottleneck at fleet scale, add an
optional on-device Kotlin AccessibilityService exposing the tree + actions over a
persistent `LocalServerSocket` (`adb forward`), which the same Python client
speaks to transparently (`Bridge` auto-detects: socket if present, else
uiautomator). This is a **later** milestone gated on real numbers — not v1 scope.
Keep the note in the repo README so intent is clear; do not build until needed.

## ContentSwarm integration (separate PR, in ContentSwarm repo)

- **New** `phone_agent/bridge.py` — use `adb-agent-bridge` (`pip` dep); `is_available()` = can we `uiautomator dump`.
- **Modify** `phone_agent/actions/handler.py` — `_handle_type` drops the 4 sleeps and switches IME once; `_handle_tap` taps element-center when the action carries a target text/id, else xy. `ActionResult` contract unchanged; ADB path stays as the fallback.
- **Modify** `phone_agent/flows.py` — recorder also stores target element text/id so replay is layout-robust, xy as fallback.
- **Modify** `phone_agent/api.py` — `GET /phones/<n>/ui`; bridge field in `/status`.
- **Modify** `contentswarm_cli.py` — `contentswarm ui <phone>`.
- **New** `orphus/skills/contentswarm-bridge/SKILL.md` — semantic-first control; update `phone-operator`.
- Follows ContentSwarm `CLAUDE.md`: branch → docs same PR → CodeRabbit → GPT Sol gate → merge; commits authored **Kelvin Lee**, no AI attribution.

## Milestones (each a small PR)

- **M1** repo + `device.py`/`ui.py` + `tap`/`text`/`screenshot` + pytest on XML fixtures. Ship `aab` CLI. Apache-2.0/NOTICE/README.
- **M2** Set-of-Marks (`marks.py`) + grid.
- **M3** ContentSwarm integration (bridge backend, no-sleep text, element taps, `/ui`, skill).
- **M4 (conditional)** native socket service — only if M1–M3 latency measurements justify it.

## Verification

- **No device:** pytest parses committed `uiautomator dump` XML fixtures → correct elements/bounds/centers; `text()` chooses ASCII vs unicode path correctly (mock adb).
- **On the connected Samsung SM-S721B:** `aab ui` dumps X's compose screen; `find(text="Post")` + `tap` posts; `text()` sets a caption instantly (no 4s dance); `marks()` overlay taps land on element centers. This is the exact flow that was painful live.
- **Regression:** ContentSwarm falls back to the old ADB path when `uiautomator dump` is unavailable.
- **Latency log:** record `uiautomator dump` time per call to decide whether v2 is ever needed.

## Risks & mitigations

- **Thin/absent tree** (games/canvas/some WebView) → marks/xy fallback tiers.
- **`FLAG_SECURE`** screens → screenshot flagged secure, already handled.
- **`uiautomator dump` occasionally fails mid-animation** → retry once, then fall back to vision.
- **Unicode text** → ADBKeyboard broadcast path retained; IME switched once.
- **License** → clean-room; never copy ADBKeyboard (GPL) source; Apache-2.0 + NOTICE credit.

## First build-session checklist (after context clear)

1. `git init` `kelvincushman/adb-agent-bridge`; add Apache-2.0 LICENSE + NOTICE (Kelvin Lee) + this PLAN.md.
2. Build M1 (pure Python, Pillow-only) and verify on the connected phone tonight.
3. M2, then M3 ContentSwarm integration through the CodeRabbit + GPT Sol gate.
4. Only consider M4 native service if dump latency is a measured problem.
