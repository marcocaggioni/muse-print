"""Batch reprint 5 H&S ingredient labels: new tel 513-568-5604 + source QR codes."""
import sys, time
sys.path.insert(0, "/home/marcocaggioni/ghs")
sys.path.insert(0, "/home/marcocaggioni/.local/lib/python3.13/site-packages")
from PIL import Image, ImageDraw, ImageFont
from ghs_symbols import ghs_symbol_1bit
import math, array
from dymoprint.dymo_print_engines import DymoLabeler, detect_device
import usb.util
import qrcode

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
TEL = "513-568-5604"

def draw_diamond(draw, cx, cy, size, fill):
    r = size // 2
    draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)

# (display_name, signal_word, h_codes, show_dict, qr_url)
CHEMICALS = [
    ("Water", None, None, {},
     "https://pubchem.ncbi.nlm.nih.gov/compound/962"),
    ("Sodium Laureth Sulfate", "WARNING", "H315 H319",
     {(3, 1): "exclam"},
     "https://www.echemi.com/produce/pr2504021103-detergent-raw-material-sodium-lauryl-sulfate-sles-70-cas-68585-34-2.html"),
    ("Sodium Lauryl Sulfate", "DANGER", "H228 H302+H332 H315 H318 H335 H412",
     {(0, 0): "acid", (3, 0): "flamme", (3, 1): "exclam"},
     "https://old.scharlab.com/docs/msds/descargarpdf.php?path=SO0499_EN.pdf&idid=EN"),
    ("Cocamidopropyl Betaine", "WARNING", "H315 H319 H412",
     {(3, 1): "exclam", (2, 0): "pollu"},
     "https://www.echemi.com/sds/cocoamidopropyl-betaine-pd20150901289.html"),
    ("Sodium Xylenesulfonate", "WARNING", "H319",
     {(3, 1): "exclam"},
     "https://www.echemi.com/sds/sodiumxylenesulfonate-pid_Seven8792.html"),
]

font_name = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
font_sig = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)

def print_label(name, signal, h_codes, show, qr_url):
    H, W = 350, 1000
    img = Image.new("1", (W, H), 0)
    d = ImageDraw.Draw(img)
    y = 12
    d.text((20, y), name, font=font_name, fill=1); y += 42
    if signal:
        d.text((20, y), signal, font=font_sig, fill=1); y += 38
    d.text((20, y), "Owner: Marco C.", font=font, fill=1); y += 32
    d.text((20, y), f"Tel: {TEL}", font=font, fill=1); y += 32
    if h_codes:
        d.text((20, y), h_codes, font=font, fill=1)
    # QR code to source URL, bottom-center
    qr = qrcode.QRCode(box_size=2, border=1)
    qr.add_data(qr_url); qr.make(fit=True)
    qi = qr.make_image(fill_color="black", back_color="white").convert("1")
    qi = qi.point(lambda p: 1 if p == 0 else 0)
    qw, qh = qi.size
    img.paste(qi, (W // 2 - qw // 2, H - qh - 8))
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

for name, sig, h, show, url in CHEMICALS:
    print_label(name, sig, h, show, url)
    time.sleep(2)
print("ALL 5 REPRINTED")
