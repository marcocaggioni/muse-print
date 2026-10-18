# Python API

## One-shot printing

```python
from muse_print import print_text

print_text("Giulia")               # one label
print_text("Stella", copies=3)     # three copies, each re-registered via ESC E
print_text("Long name here", font_size=140)
```

## Rendering text to bitmaps

```python
from muse_print import render_text

img = render_text("Giulia")
img.save("label.png")              # 1-bit PNG; pixel 1 = burned (black)

# Tune the calibration:
img = render_text(
    "Giulia",
    font_size=180,      # base size; auto-shrinks if the text is long
    image_height=280,   # bitmap height in px (label width direction)
    lead_in=180,        # blank px before the text starts
    left_shift=90,      # compensates the 450 Turbo's edge bias
    max_text_width=900, # shrink-to-fit threshold
)
```

`render_text` returns a PIL `Image` in mode `'1'`. Width covers lead-in +
text + right padding; the caller (or `LabelPrinter`) handles the feed after
the bitmap.

## The printer class

```python
from muse_print import LabelPrinter

printer = LabelPrinter(tape_size_mm=12, verbose=True)
printer.print_text("Giulia", copies=2)
printer.print_image(render_text("Custom"))  # print a pre-rendered bitmap
printer.form_feed()                          # advance to tear point, no print
```

`print_image()` sends the bitmap, a small 100-line trailing margin, then
`ESC E` (Form Feed) — the sensor-guided registration described in
[ESC E](esc-e.md). `form_feed()` sends just the `ESC E`: the USB
equivalent of tapping the printer's button.

Raises `PrinterNotFoundError` (a `RuntimeError`) with a checklist when no
Dymo is reachable on USB.

## Command line

```bash
muse-print "Giulia"
muse-print -n 3 "Stella"
muse-print --font-size 120 "Small"
muse-print --feed-only     # re-sync registration without printing
python -m muse_print "Giulia"
```

## Calibration constants

Defaults live in `muse_print.render` (`IMAGE_HEIGHT`, `LEAD_IN`,
`LEFT_SHIFT`, `FONT_SIZE`, …) and `muse_print.printer`
(`TRAILING_BLANK_LINES = 100`). They were calibrated on a LabelWriter 450
Turbo with wide name-badge stock in October 2026; override per-call if
your stock or printer differs. The one constant you should **not** raise
is `TRAILING_BLANK_LINES` — see [the gotcha](esc-e.md#why-the-trailing-margin-must-be-small).
