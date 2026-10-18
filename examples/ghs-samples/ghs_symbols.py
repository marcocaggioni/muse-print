"""GHS hazard pictograms as 1-bit PIL images for thermal printing.

Source: Wikimedia Commons GHS pictogram SVGs (public domain, sourced from
UNECE — the UN Economic Commission for Europe, the official GHS publisher).
Files: https://commons.wikimedia.org/wiki/File:GHS-pictogram-<name>.svg

The SVGs contain three layers: a red diamond border, a white inner diamond,
and the black hazard symbol. Since the Dymo label stock has the red diamond
pre-printed, this module strips the red + white layers and returns only the
black symbol as a 1-bit PIL image (pixel value 1 = burned/black, per the
dymoprint convention used by muse-print).

Requires: cairosvg (pip install cairosvg), Pillow

Example:
    from ghs_symbols import ghs_symbol_1bit, GHS_NAMES
    img = ghs_symbol_1bit("skull", size=100)  # GHS06 skull and crossbones
    img.save("skull.png")
"""

import io
import os
import re
import xml.etree.ElementTree as ET

import cairosvg
from PIL import Image

# Maps short key -> (GHS code, description, Commons filename stem)
GHS_SYMBOLS = {
    "explos":     ("GHS01", "Exploding bomb",       "GHS-pictogram-explos.svg"),
    "flamme":     ("GHS02", "Flame",                "GHS-pictogram-flamme.svg"),
    "rondflam":   ("GHS03", "Flame over circle",    "GHS-pictogram-rondflam.svg"),
    "bottle":     ("GHS04", "Gas cylinder",         "GHS-pictogram-bottle.svg"),
    "acid":       ("GHS05", "Corrosion",            "GHS-pictogram-acid.svg"),
    "skull":      ("GHS06", "Skull and crossbones", "GHS-pictogram-skull.svg"),
    "exclam":     ("GHS07", "Exclamation mark",     "GHS-pictogram-exclam.svg"),
    "silhouette": ("GHS08", "Health hazard",        "GHS-pictogram-silhouette.svg"),
    "pollu":      ("GHS09", "Environment",          "GHS-pictogram-pollu.svg"),
}

# Conventional 3x3 layout order (row-major), matching common GHS reference posters
GHS_GRID_ORDER = [
    ["explos", "flamme", "rondflam"],
    ["bottle", "acid",   "skull"],
    ["exclam", "silhouette", "pollu"],
]

# Calibrated grid positions on the Dymo bitmap (from camera calibration,
# 2026-10-18). The label stock has a pre-printed 3x3 red diamond grid;
# these are the diamond centers in bitmap pixels. The bitmap is 280px tall;
# the text area (chemical name, owner, phone, expiration) occupies x=0-600.
# Each pictogram is rendered at ~60x60px to fit inside the red outlines.
GRID_COL_X = [705, 795, 885]   # diamond centers, left to right
GRID_ROW_Y = [75, 140, 205]     # diamond centers, top to bottom
SYMBOL_SIZE = 60                # pictogram render size (px)
TEXT_AREA_MAX_X = 600           # text must stay left of this

# Directory containing the downloaded SVG files (next to this module)
SVG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))

_RED_WHITE_FILLS = {
    "#f00", "#ff0000", "red",
    "#fff", "#ffffff", "white",
}


def _fill_of(elem):
    """Read fill color from the fill attribute or the style attribute."""
    fill = (elem.get("fill") or "").lower().strip()
    if not fill:
        style = elem.get("style") or ""
        m = re.search(r"fill\s*:\s*([^;]+)", style, re.I)
        if m:
            fill = m.group(1).lower().strip()
    return fill


def ghs_symbol_1bit(key, size=100, svg_dir=None):
    """Return the GHS symbol for *key* as a 1-bit PIL image.

    Args:
        key: one of the keys in GHS_SYMBOLS (e.g. "skull", "flamme").
        size: output image is size x size pixels.
        svg_dir: directory with the SVG files (defaults to this module's dir).

    Returns:
        PIL Image in mode "1": pixel value 1 = burned/black (dymoprint
        convention), 0 = paper/white. Symbol only — no diamond border.
    """
    if key not in GHS_SYMBOLS:
        raise KeyError(f"Unknown GHS symbol {key!r}. Choose from: {sorted(GHS_SYMBOLS)}")
    svg_dir = svg_dir or SVG_DIR
    svg_path = os.path.join(svg_dir, GHS_SYMBOLS[key][2])

    tree = ET.parse(svg_path)
    root = tree.getroot()
    # Strip the red diamond border and white background; keep the black symbol.
    # Works whether fills are attributes or inside style="...".
    for elem in list(root.iter()):
        if elem.tag.split("}")[-1] in ("path", "rect", "circle", "polygon", "ellipse"):
            if _fill_of(elem) in _RED_WHITE_FILLS:
                for parent in root.iter():
                    if elem in list(parent):
                        parent.remove(elem)
                        break

    svg_bytes = ET.tostring(root, encoding="unicode").encode()
    png = cairosvg.svg2png(bytestring=svg_bytes,
                           output_width=size, output_height=size)
    img = Image.open(io.BytesIO(png))
    bg = Image.new("RGB", img.size, "white")
    bg.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
    gray = bg.convert("L")
    # 1 = dark/symbol (burned), 0 = light/paper
    return gray.point(lambda p: 1 if p < 128 else 0, mode="1")


def place_symbols(base_img, symbols):
    """Paste GHS symbols onto a 1-bit label bitmap at the calibrated grid.

    Args:
        base_img: PIL Image in mode "1" (the label bitmap under construction).
                  Pixel value 1 = burned/black, 0 = paper (dymoprint convention).
        symbols: dict mapping (row, col) -> symbol key, e.g.
                 {(0, 0): "flamme", (1, 1): "skull"}.
                 Rows 0-2 top to bottom, cols 0-2 left to right.

    Returns:
        The same image with symbols pasted (in place).
    """
    for (row, col), key in symbols.items():
        sym = ghs_symbol_1bit(key, size=SYMBOL_SIZE)
        x = GRID_COL_X[col] - SYMBOL_SIZE // 2
        y = GRID_ROW_Y[row] - SYMBOL_SIZE // 2
        # Paste: symbol pixel 1 -> set base pixel to 1 (burned).
        # In mode "1", use the symbol as its own mask after converting
        # 1-bit values to a mask (255 where symbol is black).
        mask = sym.point(lambda p: 255 if p else 0)
        base_img.paste(1, (x, y), mask)
    return base_img


def blackout_grid(base_img):
    """Fill all 9 diamond positions solid black (chemical has no hazards).

    Per Marco's spec: if the chemical has no risk, all squares are blacked out.
    """
    from PIL import ImageDraw
    draw = ImageDraw.Draw(base_img)
    for cy in GRID_ROW_Y:
        for cx in GRID_COL_X:
            # Fill a 60x60 square centered on the diamond (covers the outline)
            draw.rectangle(
                [cx - SYMBOL_SIZE // 2, cy - SYMBOL_SIZE // 2,
                 cx + SYMBOL_SIZE // 2, cy + SYMBOL_SIZE // 2],
                fill=1,
            )
    return base_img


if __name__ == "__main__":
    # Build a contact sheet of all 9 symbols for visual check
    tiles = []
    for row in GHS_GRID_ORDER:
        for key in row:
            sym = ghs_symbol_1bit(key, size=120)
            view = sym.convert("L").point(lambda p: 0 if p > 0 else 255)
            tiles.append(view)
    sheet = Image.new("L", (120 * 3, 120 * 3), 255)
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 3) * 120, (i // 3) * 120))
    sheet.save(os.path.join(SVG_DIR, "ghs-contact-sheet.png"))
    print("Contact sheet saved.")
