"""Command-line interface: ``muse-print "Some Text"``."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .printer import LabelPrinter, PrinterNotFoundError
from .render import FONT_SIZE


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="muse-print",
        description=(
            "Print a text label on a Dymo LabelWriter over USB. "
            "Each print ends with a sensor-guided Form Feed (ESC E), so "
            "back-to-back labels never drift out of registration."
        ),
    )
    p.add_argument("text", help="text to print on the label")
    p.add_argument(
        "-n", "--copies", type=int, default=1,
        help="number of copies (default: 1)",
    )
    p.add_argument(
        "--font-size", type=int, default=FONT_SIZE,
        help=f"base font size in points (default: {FONT_SIZE})",
    )
    p.add_argument(
        "--feed-only", action="store_true",
        help="don't print; just advance to the next tear point (ESC E)",
    )
    p.add_argument(
        "-v", "--verbose", action="store_true", help="print progress details",
    )
    p.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    printer = LabelPrinter(verbose=args.verbose)
    try:
        if args.feed_only:
            printer.form_feed()
            print("Advanced to tear point.")
        else:
            printer.print_text(
                args.text, copies=args.copies, font_size=args.font_size,
            )
            print(f'Printed: "{args.text}" x{args.copies}')
    except PrinterNotFoundError as exc:
        print(f"muse-print: error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
