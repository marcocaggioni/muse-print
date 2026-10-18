# Chemical labels (GHS)

muse-print can print **GHS-compliant chemical labels** on Dymo label stock
that comes pre-printed with a grid of red hazard-diamond outlines. You supply
the chemical name, owner, and which hazards apply; the printer fills each
diamond with the correct pictogram — or blacks it out solid when that hazard
does not apply.

## The label stock

The stock is a wide Dymo-compatible label (2¼″) with **nine red GHS diamond
outlines** pre-printed on the right side. The nine diamonds are arranged as a
larger diamond — 1-2-3-2-1 rows — not a square 3×3 grid:

```
          ◆            row 0: 1 diamond (top)
        ◆   ◆          row 1: 2 diamonds
      ◆   ◆   ◆        row 2: 3 diamonds (widest)
        ◆   ◆          row 3: 2 diamonds
          ◆            row 4: 1 diamond (bottom)
```

The white area on the left carries the chemical name, owner name, telephone
number, and expiration date.

## The nine pictograms

The symbols are the official GHS pictograms, sourced as SVG from Wikimedia
Commons (`File:GHS-pictogram-<name>.svg`) — public domain, traced from the
official UNECE artwork. The module strips the red/white border layers from
each SVG and rasterizes just the black symbol.

| Key | GHS | Pictogram |
|-----|-----|-----------|
| `explos` | GHS01 | Exploding bomb |
| `flamme` | GHS02 | Flame |
| `rondflam` | GHS03 | Flame over circle (oxidizer) |
| `bottle` | GHS04 | Gas cylinder |
| `acid` | GHS05 | Corrosion |
| `skull` | GHS06 | Skull and crossbones |
| `exclam` | GHS07 | Exclamation mark |
| `silhouette` | GHS08 | Health hazard (torso) |
| `pollu` | GHS09 | Environment (dead tree/fish) |

They sit in the **standard GHS positions** within the diamond arrangement:

- Top: `acid` (corrosion)
- Row 1: `silhouette` (left), `bottle` (right)
- Row 2: `pollu` (left), `explos` (center), `skull` (right)
- Row 3: `flamme` (left), `exclam` (right)
- Bottom: `rondflam` (oxidizer)

## Blackout rule

A diamond left empty is ambiguous — did the printer miss it, or does the
hazard not apply? The convention implemented here: **every diamond that does
not carry a pictogram is filled solid black**. A fully blacked-out grid means
"no GHS hazards apply." This matches the reference GHS label layouts, where
non-applicable diamonds are obscured rather than left blank.

## Geometry

The registration was dialed in over a print–photograph–adjust loop against
the physical label stock (see [The camera loop](camera.md)). Final values,
for a 1000×350 px image printed through the standard ESC E pipeline:

- Image height `H = 350` (taller than the 280 px text labels, to reach the
  top of the physical label)
- Center X `CX = 805`
- Row Y positions `[48, 100, 152, 204, 256]` (52 px vertical spacing)
- Horizontal offsets: ±48 px for the 2-diamond rows, ±96 px for the
  3-diamond row
- Pictogram size 85 px, blackout diamond size 65 px

Because the Dymo's coordinate mapping needed empirical discovery (see
[The Journey](the-journey.md)), treat these numbers as calibrated constants
for this specific label stock, not as derivable values.

## Example: Sodium Lauryl Sulfate

Sodium lauryl sulfate (CAS 151-21-3) is classified **GHS02 + GHS05 + GHS07**
with signal word **DANGER** (H228 flammable solid, H302+H332 harmful if
swallowed/inhaled, H315 skin irritation, H318 serious eye damage, H335
respiratory irritation, H412 harmful to aquatic life). The printed label
shows:

- Product name, signal word **DANGER**, owner, telephone, expiration date
- Flame, corrosion, and exclamation pictograms in their standard diamond
  positions
- The remaining six diamonds blacked out solid
- Hazard statement codes (H228, H302+H332, H315, H318, H335, H412)
- A **QR code** linking to the compound's PubChem page, placed in the
  white space below the text

## The module

`examples/ghs-samples/ghs_symbols.py` provides:

- `ghs_symbol_1bit(key, size)` — rasterize one pictogram to a 1-bit PIL image
- `GRID` constants and a `draw_diamond` helper for the 1-2-3-2-1 layout
- `blackout_grid(img)` — fill all nine diamonds (the no-hazard case)

The folder also carries all nine SVGs, pre-rendered 1-bit PNGs, a contact
sheet, and the full series of calibration test scripts (`test_chem*.py`)
plus the finished label scripts (`label_sls.py`, `label_sls_qr.py`).

## Try it

```bash
# From the repo:
python examples/ghs-samples/label_sls_qr.py
```

Adapt `label_sls_qr.py`: change the `show` dict to map your chemical's
applicable `(row, pos)` positions to pictogram keys, update the text fields,
and print. Everything else — geometry, blackouts, the ESC E pipeline — stays
the same.
