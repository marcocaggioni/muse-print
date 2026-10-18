# The camera loop

How a USB microscope camera turned the printer from a black box into an
observable instrument — and made the ESC E discovery possible.

## Why a camera

Label registration is a *physical* quantity: where does the stock stop?
No amount of code reading answers that; you have to look. A USB microscope
camera (the inexpensive kind sold for soldering inspection) was repositioned
to watch the printer's output slot, giving a tight view of the label as it
emerges and stops.

## The recipe

On the Pi (camera at `/dev/video0`):

```bash
# 1. Capture a frame
ffmpeg -y -f v4l2 -s 320x240 -i /dev/video0 -frames:v 1 -q:v 20 out.jpg

# 2. Shrink it for transfer (160x120 grayscale, ~2 KB)
python3 shrink.py out.jpg out-small.jpg

# 3. Move it to where eyes are (over ssh, as base64)
base64 -w0 out-small.jpg
```

The 320x240 frames were too large to move comfortably; the 160x120
shrinks (~2 KB) were plenty to judge "how far did the label stick out."

`shrink.py` is just Pillow:

```python
from PIL import Image
import sys
img = Image.open(sys.argv[1]).convert("L").resize((160, 120))
img.save(sys.argv[2], quality=30)
```

## The protocol

Each experiment round was:

1. **Print** — up to 5 test labels in a row (named `D1`, `D2`, `D3`… or
   `F1`, `F2`, `F3` for the Form Feed series)
2. **Photograph** — one frame per print, same camera position
3. **Measure** — compare how far each label protrudes
4. **Reset** — press the printer's physical button to re-establish the
   known-good state before the next round

This is what the drift looked like before the fix: `D1` tall, `D2`
shorter, `D3` shortest — the accumulating shortfall, visible in three
frames. And this is what the fix looked like: `F1`, `F2`, `F3` all
protruding to exactly the same point.

## Why it mattered

Three things the camera bought that reasoning alone didn't:

- **The drift was measured, not hypothesized.** "Each label is shorter
  than the last" is a fact you can see, not a theory about pitch.
- **Wrong turns were cheap.** Bumping the assumed pitch, the overshoot
  experiment with full-margin + ESC E — each took one round of prints and
  three photos to evaluate.
- **The fix was proven, not believed.** Three identical frames is the kind
  of evidence that ends a debugging session.

## Reproducing it

You don't need this exact camera. Any USB camera that can see the output
slot works — even a phone on a stand, if you can get the photos back to
your terminal quickly. The key properties are: fixed position, one frame
per print, fast turnaround. The loop matters more than the optics.
