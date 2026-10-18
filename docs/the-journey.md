# The Journey

*An engineering log: how a Sunday-morning label printer turned into an
eleven-byte fix. October 18, 2026.*

## The setup

The starting point was a Raspberry Pi 4 already running as a
[Muse Gadget](https://github.com/marcocaggioni/muselab) — Debian 13, paired,
controllable by conversation. The goal was simple, the kind of thing that
should take five minutes: plug in a **Dymo LabelWriter 450 Turbo** over USB
and print name tags by asking in chat. "Print a label saying Giulia."

The printer enumerates as USB ID `0922:0021`. The label stock is the wide
name-badge kind, with a red diamond grid pre-printed along one edge.

## The driver hunt

First surprise: Debian trixie's `printer-driver-dymo` package is
**empty** — docs only, no driver. CUPS was a dead end before it started.

The Muse gadget went looking and found
[**dymoprint**](https://github.com/computerlyrik/dymoprint) 2.5.0, an
open-source tool that talks to LabelWriters over **raw USB**, no CUPS
involved. Installed with:

```bash
pip install --break-system-packages dymoprint
```

(The `--break-system-packages` flag is Debian 13's way of making you
acknowledge you're installing outside `apt` — see [Drivers](drivers.md).)
The printing user was added to the `lp` group so `/dev/bus/usb` is readable
without sudo.

## First success

The first label printed on the first try: text rendered with PIL into a
1-bit bitmap (pixel value 1 = burned black), converted to the printer's
row-major byte format, streamed over USB. Name tags for the family came out
looking right. Calibration settled quickly:

- Image height 280 px, DejaVuSans-Bold at 180 pt, auto-scaled for long names
- 180 px of blank lead-in before the text
- Text shifted left 90 px — the 450 Turbo biases output toward one edge

It felt done. It wasn't.

## The drift

The requirement was casual — print a few name tags in a row — and that's
exactly what broke it. The pattern was unmistakable:

> The first label, printed right after pressing the printer's physical
> button, is perfect. The second is slightly off. The third is worse.

Every print started from wherever the *previous* print had left the stock,
and the error accumulated. The only known-good state was "just pressed the
button." Something had to re-establish that state before every print —
without a finger.

## Giving Muse eyes

The fix for "I can't see what's happening" was a USB microscope camera
pointed at the printer's output slot. The loop became:

```bash
# on the Pi: print, photograph, shrink, transfer
python3 print-label.py "D1"
ffmpeg -y -f v4l2 -s 320x240 -i /dev/video0 -frames:v 1 -q:v 20 d1.jpg
python3 shrink.py d1.jpg d1s.jpg   # 160x120 grayscale, ~2 KB
base64 -w0 d1s.jpg                # pipe home through ssh, decode, view
```

Print. Look. Measure. Adjust. Up to five prints per round, button-press
resets between rounds. This is the loop that made everything below
possible — and the photo at the top of this page is that loop, running:

![The autonomous learning loop: a Raspberry Pi 4 with Sense HAT running the Muse Gadget, a USB microscope camera aimed at the Dymo LabelWriter 450 Turbo, with a freshly printed "F3" test label coming out.](images/learning-setup.jpg)

*The autonomous learning loop in action: Raspberry Pi 4 with Sense HAT
(rainbow LEDs) running the Muse Gadget, USB microscope camera aimed at the
Dymo LabelWriter 450 Turbo, with a freshly printed "F3" test label coming
out of the slot. The camera let Muse see where each print started and ended
and iterate without touching the printer.*

## The investigation

With the camera running, the drift was measured, not guessed. A sequence of
three prints showed the label sticking out less each time — the feed was
consistently *short*. Bumping the assumed pitch from 1287 to 1400 lines
helped one round and drifted the next. Chasing the pitch number was whack-a-
molecule: the number was never quite right because **counting lines from
the host is open-loop**. Any error — mechanical, thermal, rounding —
accumulates forever.

Meanwhile, one fact kept nagging: *the button always works.* Pressing the
printer's physical button feeds the stock to exactly the right place, every
time. So the printer *knows* where the tear point is. The question became:
can USB ask the printer to do what the button does?

## The breakthrough

Yes. The Dymo printer protocol (documented in the LabelWriter 450 Series
Technical Reference) includes a **Form Feed** command: `ESC E`, bytes
`0x1B 0x45`. When the firmware receives it, it feeds the stock forward
until its **label-gap sensor** detects the next gap between labels, then
advances to the tear bar and stops. That is precisely what the physical
button does — and the technical reference notes it "can be used after every
label."

And dymoprint already implements it — as `DymoLabeler.cut()`
(`cmd = [ESC, ord("E")]`) — but nothing in the normal print path ever calls
it. The button-equivalent was sitting in the driver the whole time, unused.

## The gotcha

The naive fix — "just append ESC E after printing" — overshoots. The old
code fed a full label pitch of blank lines *and then* ESC E sought the
*following* gap: two pitches of feed, label ruined. The margin before the
Form Feed must be **small**: just enough blank lines to move the printed
area clear of the thermal head (100 lines), leaving the gap sensor still
ahead of the current label's gap. Then ESC E finds the *right* gap.

The final sequence per label:

1. Stream the text bitmap
2. Feed 100 blank lines (clear the head, gap still ahead)
3. `ESC E` — firmware seeks the next gap via its sensor, stops at the tear bar

## Verification

Three consecutive prints, no button presses between them, photographed by
the microscope camera: all three labels stick out to exactly the same
point. The drift is gone — not tuned away, but *structurally* gone, because
every print now re-registers against the printer's own sensor instead of
the host's line count.

## Lessons learned

1. **The hardware knows more than the host.** The printer had a gap sensor
   the whole time; the original approach ignored it and counted lines
   instead. When the device can close the loop, let it.
2. **Make the system observable before optimizing it.** The camera turned
   "the pitch is probably 1287" into measured evidence. Every wrong turn
   (bumping the pitch, the overshoot experiment) was cheap because the
   result was visible in seconds.
3. **Read the protocol.** The answer was in the technical reference and in
   the driver's own source (`cut()`), hiding in plain sight. Eleven bytes —
   `0x1B 0x45` — replaced an entire calibration problem.
4. **Beware additive fixes.** ESC E on top of the old full-pitch margin
   fed two pitches. The new mechanism replaced the old one; it didn't stack
   on it.

---

*Continue to the [ESC E deep dive](esc-e.md) for the protocol details, or
[Drivers](drivers.md) to reproduce the setup from scratch.*
