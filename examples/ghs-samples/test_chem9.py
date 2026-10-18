"""Test chemical label v9: DIAGNOSTIC - test if Y coordinates are inverted."""
import sys
sys.path.insert(0, "/home/marcocaggioni/ghs")
sys.path.insert(0, "/home/marcocaggioni/.local/lib/python3.13/site-packages")
from PIL import Image, ImageDraw, ImageFont
import math, array
from dymoprint.dymo_print_engines import DymoLabeler, detect_device
import usb.util

CX = 795
# DIAGNOSTIC: shift DOWN 70px in image coordinates (if inverted, appears UP physically)
# Was: [30, 85, 140, 195, 250], now: [100, 155, 210, 265, 320->clamped]
# Actually, let's do a clear test: move to bottom half of image
ROW_Y = [150, 185, 220, 255, 275]  # bottom half
ROW_X = [
    [CX],
    [CX - 45, CX + 45],
    [CX - 90, CX, CX + 90],
    [CX - 45, CX + 45],
    [CX],
]

BLACKOUT_SIZE = 65

def draw_diamond(draw, cx, cy, size, fill):
    r = size // 2
    # Clamp to image bounds
    if cy - r < 0 or cy + r >= 280:
        return
    draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)

H = 280
W = 1000
img = Image.new("1", (W, H), 0)
d = ImageDraw.Draw(img)
font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
# DIAGNOSTIC: text moved DOWN in image (y=150 instead of y=5)
d.text((20, 150), "Acetone", font=font_big, fill=1)
d.text((20, 210), "TEST9", font=font, fill=1)

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
print("CHEM TEST 9 PRINTED (diagnostic: Y inverted?)")
