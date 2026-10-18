"""Text → 1-bit bitmap rendering for Dymo label stock.

The bitmap this module produces is tuned for wide name-badge label stock on a
Dymo LabelWriter 450 Turbo. In PIL mode ``'1'``, pixel value 1 is burned
(black) and 0 is left blank.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Calibration defaults.
#
# These were found empirically on a LabelWriter 450 Turbo (Oct 2026) by
# printing, photographing the output with a USB microscope camera, and
# adjusting. They are defaults, not laws — override per call if your stock
# or printer behaves differently.
# ---------------------------------------------------------------------------

#: Height of the rendered bitmap in pixels (label width direction).
IMAGE_HEIGHT = 280

#: Blank pixels before the text starts (label feed direction).
LEAD_IN = 180

#: Horizontal shift applied to the text. The 450 Turbo biases printed output
#: toward one edge; shifting the text left by this many pixels centers it.
LEFT_SHIFT = 90

#: Base font size in points; scaled down automatically if the text is long.
FONT_SIZE = 180

#: Maximum text width in pixels before auto-scaling kicks in.
MAX_TEXT_WIDTH = 900

#: Vertical margin kept clear at top/bottom when auto-scaling.
TEXT_VERTICAL_MARGIN = 60

#: Right padding after the text before the trailing margin.
RIGHT_PADDING = 200

#: Candidate font paths, tried in order.
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
]


def find_font() -> str:
    """Return the first usable bold font path, or raise FileNotFoundError."""
    import os

    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        "No bold DejaVu font found. Tried: " + ", ".join(FONT_CANDIDATES)
    )


def render_text(
    text: str,
    font_size: int = FONT_SIZE,
    image_height: int = IMAGE_HEIGHT,
    lead_in: int = LEAD_IN,
    left_shift: int = LEFT_SHIFT,
    max_text_width: int = MAX_TEXT_WIDTH,
) -> Image.Image:
    """Render *text* to a 1-bit PIL image ready for the label printer.

    Pixel value 1 = burned (black). The image is ``(width, image_height)``
    where width covers the lead-in, the text, and right padding. The caller
    is responsible for the feed *after* the bitmap — see
    :mod:`muse_print.printer` for why the trailing margin must stay small.
    """
    if not text:
        raise ValueError("text must not be empty")

    font_path = find_font()
    font = ImageFont.truetype(font_path, font_size)

    # Measure, then shrink the font if the text would overflow.
    probe = ImageDraw.Draw(Image.new("1", (10, 10), 0))
    bbox = probe.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    scale = min(max_text_width / tw, (image_height - TEXT_VERTICAL_MARGIN) / th, 1.0)
    if scale < 1.0:
        font = ImageFont.truetype(font_path, max(int(font_size * scale), 8))
        bbox = probe.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    width = lead_in + tw + RIGHT_PADDING
    img = Image.new("1", (width, image_height), 0)
    draw = ImageDraw.Draw(img)
    cx = lead_in + 60 - bbox[0] - left_shift
    cy = (image_height - th) // 2 - bbox[1]
    draw.text((cx, cy), text, font=font, fill=1)
    return img
