"""Test chemical label v6: larger blackouts to fill red diamonds, adjusted vertical fit."""
import sys
sys.path.insert(0, "/home/marcocaggioni/ghs")
sys.path.insert(0, "/home/marcocaggioni/.local/lib/python3.13/site-packages")
from PIL import Image, ImageDraw, ImageFont
from ghs_symbols import ghs_symbol_1bit
import math, array
from dymoprint.dymo_print_engines import DymoLabeler, detect_device
import usb.util

CX = 810
# Compressed vertical: 48px spacing to fit 5 rows in 280px with 90px diamonds
ROW_Y = [48, 96, 144, 192, 240]
ROW_X = [
    [CX],
    [CX - 45, CX + 45],
    [CX - 90, CX, CX + 90],
    [CX - 45, CX + 45],
    [CX],
]

SYMBOL_SIZE = 60
BLACKOUT_SIZE = 90  # larger to fully cover red outlines

def draw_diamond(draw, cx, cy, size, fill):
    r = size // 2
    draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)

H = 280
W = 1000
img = Image.new("1", (W, H), 0)
d = ImageDraw.Draw(img)
font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
d.text((20, 20), "Acetone", font=font_big, fill=1)
d.text((20, 90), "Owner: Marco C.", font=font, fill=1)
d.text((20, 135), "Tel: 555-0100", font=font, fill=1)
d.text((20, 180), "Exp: 2027-06-30", font=font, fill=1)

symbols = {(1, 0): "flamme", (1, 1): "exclam"}

for row_idx in range(5):
    for pos_idx, cx in enumerate(ROW_X[row_idx]):
        cy = ROW_Y[row_idx]
        if (row_idx, pos_idx) in symbols:
            sym = ghs_symbol_1bit(symbols[(row_idx, pos_idx)], size=SYMBOL_SIZE)
            x0 = cx - SYMBOL_SIZE // 2
            y0 = cy - SYMBOL_SIZE // 2
            mask = sym.point(lambda p: 255 if p else 0)
            img.paste(1, (x0, y0), mask)
        else:
            draw_diamond(d, cx, cy, BLACKOUT_SIZE, fill=1)

label_rotated = img.transpose(Image.ROTATE_270)
labelstream = label_rotated.tobytes()
row_len = int(math.ceil(img.height / 8))
rows = [labelstream[i:i+row_len] for i in range(0, len(labelstream), row_len)]
matrix = [array.array("B", r).tolist() for r in rows]
detected = detect_device()
lm = DymoLabeler(detected.devout, detected.devin, synwait=64, tape_size_mm=12)
lm.tapeColor(0)
for row in matrix:
    lm.line(row)
lm.skipLines(100)
lm.cut()
lm.statusRequest()
lm.sendCommand()
usb.util.dispose_resources(detected.dev)
print("CHEM TEST 6 PRINTED")
