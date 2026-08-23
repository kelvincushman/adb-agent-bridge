---
name: adb-agent-bridge
description: Control Android phones semantically over plain ADB - read the UI element tree, tap elements by text/id/desc, type instantly, screenshot, and draw Set-of-Marks overlays. Use whenever a task involves driving an Android device, before reaching for screenshot-and-guess vision control.
---

# adb-agent-bridge: semantic Android control

Drive Android devices by element, not by pixel. `uiautomator dump` exposes
every on-screen element's text, resource-id, content-desc, and bounds over
plain ADB - so you tap element centers (cannot miss) and commit text in
~100ms. Vision is the fallback tier, not the default.

## Setup check (run once per session)

```bash
aab --help >/dev/null 2>&1 || pip install adb-agent-bridge
adb devices    # phone must show as "device", not "unauthorized"/"offline"
```

- `unauthorized` -> accept the USB-debugging prompt on the phone's screen.
- No devices -> cable/USB mode, and Developer options > USB debugging on.
- Multiple phones -> add `-s <serial>` to every `aab` call.

## Decision order (cheapest first)

1. **`aab ui`** - the element tree as text. Grep it. Almost every "what is on
   screen / where is X" question is answered here without a screenshot.
2. **`aab tap --text/--id/--desc`** - tap the element wherever it is.
3. **`aab marks out.png`** - numbered overlay + legend for screens with a
   thin tree (games, canvas, some WebViews): pick a number, tap its center.
4. **Raw coordinates / screenshots** - last resort.

## Commands

```bash
aab ui                          # elements: text/id/desc/center, one per line
aab tap --text "Post"           # or --id resource_id, --desc "Close tab"
aab tap --grid C7               # 10 square columns A-J, rows from 1
aab tap 540 1200                # raw coordinates
aab text "a caption" --clear    # ~100ms; --clear empties the field first
aab text "héllo 👋"             # unicode/emoji need ADBKeyboard (below)
aab swipe 540 1600 540 400      # scroll
aab key 66                      # keyevent (66=ENTER, 4=BACK, 3=HOME)
aab marks annotated.png         # Set-of-Marks overlay + printed legend
aab screenshot out.png
```

Python (same capabilities): `from adb_agent_bridge import Bridge`;
`b = Bridge("SERIAL")`; `b.find(text="Post")`, `b.tap(el)`, `b.text(s)`,
`b.prefetch_ui()` to overlap the ~2-3s dump with your own thinking.

## Fast text needs ADBKeyboard (one-time device install)

```bash
curl -LO https://github.com/senzhk/ADBKeyBoard/raw/master/ADBKeyboard.apk
adb install ADBKeyboard.apk
adb shell ime enable com.android.adbkeyboard/.AdbIME
```

Without it, plain-ASCII text still works (slower); unicode and `--clear` do
not. The bridge switches the IME itself when typing; restore the user's
keyboard after a session with `adb shell ime reset`.

## Gotchas

- A UI dump takes ~2-3s (more on heavy screens) - do not poll it in a loop;
  act, then dump once.
- Empty or thin tree -> the app is canvas-drawn: use `aab marks` or a
  screenshot with vision.
- Dump can fail mid-animation; the bridge retries once then raises - treat
  the error as "fall back to screenshot".
- `FLAG_SECURE` screens (banking, private mode) refuse screenshots.
- On someone's personal phone: press HOME before and after, never tap
  Post/Send/Buy without explicit permission, and `adb shell ime reset` when
  done.
