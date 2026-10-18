#!/usr/bin/env python3
"""Basic muse-print example: render a name tag and print it.

Run: python examples/basic.py "Giulia"
Requires a Dymo LabelWriter 450 Turbo on USB (see docs/quickstart.md).
"""

import sys

from muse_print import LabelPrinter, PrinterNotFoundError, render_text


def main() -> int:
    text = sys.argv[1] if len(sys.argv) > 1 else "Giulia"

    # Render first, so you can inspect (or save) the bitmap before printing.
    img = render_text(text)
    print(f"Rendered {img.width}x{img.height} 1-bit bitmap.")
    img.save("/tmp/muse-print-preview.png")
    print("Preview saved to /tmp/muse-print-preview.png")

    try:
        LabelPrinter(verbose=True).print_image(img)
    except PrinterNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f'Printed: "{text}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
