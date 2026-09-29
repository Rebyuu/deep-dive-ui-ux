# Driving the app

Screenshots and taps must share one coordinate system. Record the device size in that system (`--width/--height` at `session.py init`) and log taps in it; the report converts to percentages.

## iOS simulator

- Boot exactly one simulator, or pass the device/UDID on every call. A second booted simulator silently receives taps.
- Capture: `xcrun simctl io <udid> screenshot <file>`. Images are in pixels (e.g. 1206×2622 at 3×). To read tap targets off a screenshot, scale a copy to point width (`sips -Z <height_pt> in.png --out view.png`): one pixel in the copy is then one point.
- If a simulator control tool can read the accessibility tree, use it to locate targets; otherwise read coordinates off the point-scaled copy.
- Permissions dialogs (camera, microphone, speech, photos) appear on first use: log them as `--action system` steps, they are real UX cost on first run.
- Install a fresh build and uninstall first for a clean first-run state.

## Android emulator

- `adb exec-out screencap -p > file.png`; sizes are in px. Taps via `adb shell input tap x y` also use px, so use `--width/--height` in px.
- `adb shell input swipe x1 y1 x2 y2 ms`, `adb shell input text` (spaces as `%s`).

## Web app

- Use a browser automation tool; set a fixed viewport (e.g. 390×844 for mobile, 1440×900 for desktop) and screenshot at that CSS-px size.
- Log clicks in CSS px of the viewport.

## Recurring tool pitfalls

- **Typing artifacts:** some tools type through a keyboard layout and swap characters (y/z, umlauts, `-`). Note them once as test-tool artifacts in the report; don't count them as app defects. Autocorrect changing words is a real finding, though.
- **No backspace:** some tools cannot send delete keys and type `\b` literally. Clear fields with select-all + cut, or avoid needing to.
- **Stale coordinates:** after a list row disappears (delete) everything below shifts. Re-screenshot before the next tap; an accidental tap caused by the shift is itself a finding about the design.
- **Sheets and scroll position:** after an alert closes, forms may scroll back to an earlier field. Re-screenshot.
- **Long-press:** use a duration of about 1 s. Many hidden features (rename, context menus) live there; try it on every list row.
