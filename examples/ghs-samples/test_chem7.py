"""Test chemical label v7: all black diamonds, smaller, shifted up."""
import sys
sys.path.insert(0, "/home/marcocaggioni/ghs")
sys.path.insert(0, "/home/marcocaggioni/.local/lib/python3.13/site-packages")
from PIL import Image, ImageDraw, ImageFont
import math, array
from dymoprint.dymo_print_engines import DymoLabeler, detect_device
import usb.util

CX = 810
# Shifted up and compressed: 40px spacing, centered at y=115
ROW_Y = [35, 75, 115, 155, 195]
ROW_X = [
    [CX],
    [CX - 45, CX + 45],
    [CX - 90, CX, CX + 90],
    [CX - 45, CX + 45],
    [CX],
]

BLACKOUT_SIZE = 75  # smaller (was 90)

def draw_diamond(draw, cx, cy, size, fill):
    r = size // 2
    draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)

H = 280
W = 1000
img = Image.new("1", (W, H), 0)
d = ImageDraw.Draw(img)
font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
# Text moved up 15px
d.text((20, 5), "Acetone", font=font_big, fill=1)
d.text((20, 75), "Owner: Marco C.", font=font, fill=1)
d.text((20, 120), "Tel: 555-0100", font=font, fill=1)
d.text((20, 165), "Exp: 2027-06-30", font=font, fill=1)

# ALL 9 blacked out (no symbols yet - register positions first)
for row_idx in range(5):
    for cx in ROW_X[row_idx]:
        cy = ROW_Y[row_idx]
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
print("CHEM TEST 7 PRINTED (all black, shifted up)")
