"""Batch print 5 Head & Shoulders ingredient labels."""
import sys, time
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

# (name, display_name, signal_word, h_codes, show_dict)
CHEMICALS = [
    ("Water", "Water", None, None,
     {}),
    ("Sodium Laureth Sulfate", "Sodium Laureth Sulfate", "WARNING", "H315 H319",
     {(3, 1): "exclam"}),
    ("Sodium Lauryl Sulfate", "Sodium Lauryl Sulfate", "DANGER", "H228 H302+H332 H315 H318 H335 H412",
     {(0, 0): "acid", (3, 0): "flamme", (3, 1): "exclam"}),
    ("Cocamidopropyl Betaine", "Cocamidopropyl Betaine", "WARNING", "H315 H319 H412",
     {(3, 1): "exclam", (2, 0): "pollu"}),
    ("Sodium Xylenesulfonate", "Sodium Xylenesulfonate", "WARNING", "H319",
     {(3, 1): "exclam"}),
]

font_name = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
font_sig = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)

def print_label(name, signal, h_codes, show):
    H, W = 350, 1000
    img = Image.new("1", (W, H), 0)
    d = ImageDraw.Draw(img)
    y = 15
    d.text((20, y), name, font=font_name, fill=1); y += 45
    if signal:
        d.text((20, y), signal, font=font_sig, fill=1); y += 40
    d.text((20, y), "Owner: Marco C.", font=font, fill=1); y += 35
    d.text((20, y), "Tel: 555-0100", font=font, fill=1); y += 35
    if h_codes:
        d.text((20, y), h_codes, font=font, fill=1)
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
    lr = img.transpose(Image.ROTATE_270)
    ls = lr.tobytes()
    rl = int(math.ceil(img.height / 8))
    rows = [ls[i:i+rl] for i in range(0, len(ls), rl)]
    matrix = [array.array("B", r).tolist() for r in rows]
    det = detect_device()
    lm = DymoLabeler(det.devout, det.devin, synwait=64, tape_size_mm=12)
    lm.tapeColor(0)
    for row in matrix:
        lm.line(row)
    lm.skipLines(100); lm.cut(); lm.statusRequest(); lm.sendCommand()
    usb.util.dispose_resources(det.dev)
    print(f"PRINTED: {name}", flush=True)

for name, disp, sig, h, show in CHEMICALS:
    print_label(disp, sig, h, show)
    time.sleep(2)
print("ALL 5 DONE")
