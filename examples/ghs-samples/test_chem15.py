"""Test chemical label v15: all 9 GHS pictograms."""
import sys
sys.path.insert(0, "/home/marcocaggioni/ghs")
sys.path.insert(0, "/home/marcocaggioni/.local/lib/python3.13/site-packages")
from PIL import Image, ImageDraw, ImageFont
from ghs_symbols import ghs_symbol_1bit
import math, array
from dymoprint.dymo_print_engines import DymoLabeler, detect_device
import usb.util

CX = 805
ROW_Y = [48, 100, 152, 204, 256]
ROW_X = [
    [CX],
    [CX - 48, CX + 48],
    [CX - 96, CX, CX + 96],
    [CX - 48, CX + 48],
    [CX],
]

SYMBOL_SIZE = 50  # fit inside diamond outlines

# All 9 pictograms in diamond arrangement order
symbols = {
    (0, 0): "explos",
    (1, 0): "flamme", (1, 1): "rondflam",
    (2, 0): "bottle", (2, 1): "acid", (2, 2): "skull",
    (3, 0): "exclam", (3, 1): "silhouette",
    (4, 0): "pollu",
}

H = 350
W = 1000
img = Image.new("1", (W, H), 0)
d = ImageDraw.Draw(img)
font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
d.text((20, 20), "Acetone", font=font_big, fill=1)
d.text((20, 90), "Owner: Marco C.", font=font, fill=1)
d.text((20, 135), "Tel: 555-0100", font=font, fill=1)
d.text((20, 180), "Exp: 2027-06-30", font=font, fill=1)

for row_idx in range(5):
    for pos_idx, cx in enumerate(ROW_X[row_idx]):
        cy = ROW_Y[row_idx]
        key = symbols[(row_idx, pos_idx)]
        sym = ghs_symbol_1bit(key, size=SYMBOL_SIZE)
        x0 = cx - SYMBOL_SIZE // 2
        y0 = cy - SYMBOL_SIZE // 2
        mask = sym.point(lambda p: 255 if p else 0)
        img.paste(1, (x0, y0), mask)

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
print("CHEM TEST 15 PRINTED (all 9 pictograms)")
