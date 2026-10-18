"""Compliant GHS label for Sodium Lauryl Sulfate (CAS 151-21-3).
Pictograms per SDS: GHS02 (flamme), GHS05 (acid), GHS07 (exclam). Signal word: DANGER.
All other diamonds blacked out."""
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
SYMBOL_SIZE = 85
BLACKOUT_SIZE = 65

def draw_diamond(draw, cx, cy, size, fill):
    r = size // 2
    draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)

# SLS pictogram positions (standard GHS layout):
# (0,0)=acid SHOW | (1,0)=silhouette OUT | (1,1)=bottle OUT
# (2,0)=pollu OUT | (2,1)=explos OUT | (2,2)=skull OUT
# (3,0)=flamme SHOW | (3,1)=exclam SHOW | (4,0)=rondflam OUT
show = {(0, 0): "acid", (3, 0): "flamme", (3, 1): "exclam"}

H = 350
W = 1000
img = Image.new("1", (W, H), 0)
d = ImageDraw.Draw(img)
font_name = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
font_danger = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
d.text((20, 15), "Sodium Lauryl Sulfate", font=font_name, fill=1)
d.text((20, 60), "DANGER", font=font_danger, fill=1)
d.text((20, 105), "Owner: Marco C.", font=font, fill=1)
d.text((20, 140), "Tel: 555-0100", font=font, fill=1)
d.text((20, 175), "Exp: 2027-12-31", font=font, fill=1)
d.text((20, 210), "H228 H302+H332 H315", font=font, fill=1)
d.text((20, 245), "H318 H335 H412", font=font, fill=1)

for row_idx in range(5):
    for pos_idx, cx in enumerate(ROW_X[row_idx]):
        cy = ROW_Y[row_idx]
        if (row_idx, pos_idx) in show:
            sym = ghs_symbol_1bit(show[(row_idx, pos_idx)], size=SYMBOL_SIZE)
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
print("SLS COMPLIANT LABEL PRINTED")
