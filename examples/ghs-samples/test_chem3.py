"""Test chemical label v3: corrected grid alignment."""
import sys
sys.path.insert(0, "/home/marcocaggioni/ghs")
sys.path.insert(0, "/home/marcocaggioni/.local/lib/python3.13/site-packages")
from PIL import Image, ImageDraw, ImageFont
from ghs_symbols import ghs_symbol_1bit
import math, array
from dymoprint.dymo_print_engines import DymoLabeler, detect_device
import usb.util

# CORRECTED coordinates (v3): shifted up, larger squares
GRID_COL_X = [705, 795, 885]
GRID_ROW_Y = [50, 120, 190]  # was [75, 140, 205] - shifted up 25px
SYMBOL_SIZE = 75  # was 60 - larger to fill diamonds

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

symbols = {(0, 1): "flamme", (0, 2): "exclam"}

for row in range(3):
    for col in range(3):
        cx = GRID_COL_X[col]
        cy = GRID_ROW_Y[row]
        x0 = cx - SYMBOL_SIZE // 2
        y0 = cy - SYMBOL_SIZE // 2
        if (row, col) in symbols:
            sym = ghs_symbol_1bit(symbols[(row, col)], size=SYMBOL_SIZE)
            mask = sym.point(lambda p: 255 if p else 0)
            img.paste(1, (x0, y0), mask)
        else:
            d.rectangle([x0, y0, x0 + SYMBOL_SIZE, y0 + SYMBOL_SIZE], fill=1)

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
print("CHEM TEST 3 PRINTED")
