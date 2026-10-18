# ESC E: the Form Feed deep dive

The technical heart of muse-print. If you only read one page of these
docs, make it [The Journey](the-journey.md); this page is the protocol
reference behind it.

## The problem, precisely

`dymoprint`'s normal print path ends with `skipLines(margin)` — the host
sends N blank raster lines to advance the stock so the label's end reaches
the tear bar. The host is *assuming* a fixed number of lines per label
pitch. Any discrepancy between the assumed pitch and the real one —
mechanical tolerance, thermal expansion, rounding in the line count —
becomes a registration error, and because each print starts where the last
one stopped, the error **accumulates**: label 2 off by ε, label 3 off by
2ε, and so on.

The printer's physical button doesn't have this problem, because the
button doesn't count lines.

## What the button does

The LabelWriter 450 series has a **label-gap sensor** in the paper path.
The label stock has detectable gaps between labels. When you press the
button, the firmware feeds the motor forward until the sensor sees the next
gap, then advances a fixed small distance to the tear bar and stops. It's a
closed loop: the printer measures where the stock actually is.

## ESC E

The Dymo printer protocol exposes this as **Form Feed**: `ESC` `E`
(bytes `0x1B 0x45`). Per the LabelWriter 450 Series Technical Reference,
it "can be used after every label." The firmware performs the same
gap-seek the button triggers.

In `dymoprint` 2.5.0 (`dymoprint/labeler.py`):

```python
def cut(self):
    """Set instruction to trigger cutting of the tape. (MLF)"""
    cmd = [ESC, ord("E")]
    self.buildCommand(cmd)
```

(The name is a historical misnomer — the 450 Turbo has no cutter; on this
model the command is a form feed.) Nothing in dymoprint's print path calls
it. muse-print calls it after every label.

## The exact byte sequence per label

`LabelPrinter.print_image()` builds one USB transaction:

1. `ESC C 0` — tape color (from dymoprint's `rawPrintLabel` convention)
2. For each bitmap row: `bytesPerLine` + `SYN` + row bytes
3. `skipLines(100)` — 100 blank lines, **small on purpose**
4. `ESC E` — Form Feed: firmware gap-seeks to the tear bar
5. `ESC A` — status request

## Why the trailing margin must be small

This is the gotcha that cost a round of test labels. The gap sensor looks
*forward* — it finds the *next* gap from wherever the stock currently sits.
If you feed a full label pitch of blanks and *then* send ESC E, the current
label's gap is already behind the sensor, so the firmware seeks the
*following* gap: **two pitches of feed**, and the label overshoots the tear
bar.

The 100 blank lines in step 3 only move the printed area clear of the
thermal head. The current label's gap is still ahead of the sensor, so
ESC E finds the right one. The rule:

> **Small margin + ESC E = one pitch. Full margin + ESC E = two pitches.**

## Failure mode

If the gap sensor ever fails to see a gap (wrong stock, sensor dirty),
the firmware falls back to a maximum feed defined in NVRAM (around 7.5" on
the 450 series) — the label would feed far too long. This never happened
during development, and with the microscope camera it would be visible
immediately, but it's worth knowing the failure is loud, not subtle.

## Protocol notes (unverified in dymoprint)

The protocol also defines a **Short Form Feed**, `ESC G` (`0x1B 0x47`),
intended for positioning *between* labels of a multi-copy job, and a status
bit (`ESC A` response, bit 1) reporting top-of-form. dymoprint 2.5.0
exposes neither, so muse-print implements multi-copy as repeated
print + ESC E cycles — verified behavior rather than protocol speculation.
