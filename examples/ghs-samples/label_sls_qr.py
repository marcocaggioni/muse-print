"""Compliant GHS label for Sodium Lauryl Sulfate with QR code to PubChem."""
import sys
sys.path.insert(0, "/home/marcocaggioni/ghs")
sys.path.insert(0, "/home/marcocaggioni/.local/lib/python3.13/site-packages")
from PIL import Image, ImageDraw, ImageFont
from ghs_symbols import ghs_symbol_1bit
import math, array
from dymoprint.dymo_print_engines import DymoLabeler, detect_device
import usb.util

# QR code: try qrcode lib, else skip
try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False

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

# QR code to PubChem (SLS, CID 3423265) in white space below text
if HAS_QR:
    url = "https://pubchem.ncbi.nlm.nih.gov/compound/3423265"
    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("1")
    # Invert: we need 1=black for our pipeline
    qr_img = qr_img.point(lambda p: 1 if p == 0 else 0)
    qw, qh = qr_img.size
    # Place at bottom-left white space
    img.paste(qr_img, (20, H - qh - 10))
    d.text((20 + qw + 10, H - 30), "PubChem", font=font, fill=1)

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
print("SLS LABEL WITH QR PRINTED")
