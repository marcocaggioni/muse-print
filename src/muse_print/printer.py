"""USB printing for Dymo LabelWriter printers with sensor-accurate registration.

The key insight of this module: after the bitmap is sent, it issues a
**Form Feed** (``ESC E``, ``0x1B 0x45``) instead of blindly feeding a
fixed number of blank lines to reach the tear point. The printer firmware
uses its label-gap sensor to find the next gap and stops exactly at the
tear bar — the USB equivalent of pressing the printer's physical button.

This eliminates the registration drift that accumulates when the host
counts blank lines (see ``docs/esc-e.md``).
"""

from __future__ import annotations

import array
import math
import time

import usb.util
from PIL import Image

from . import render

#: Blank lines fed after the bitmap before Form Feed. Just enough to move
#: the printed area clear of the thermal head — the gap sensor is still
#: ahead, so ESC E then finds the *next* label gap.
#:
#: WARNING: do NOT raise this to a full label pitch. A full-pitch margin
#: plus ESC E feeds two pitches and overshoots the tear point.
TRAILING_BLANK_LINES = 100

#: USB vendor:product for the LabelWriter 450 Turbo.
DYMO_VENDOR_ID = 0x0922
DYMO_PRODUCT_ID = 0x0021


class PrinterNotFoundError(RuntimeError):
    """Raised when no Dymo printer is reachable over USB."""


class LabelPrinter:
    """A Dymo LabelWriter on USB, with drift-free label registration."""

    def __init__(self, tape_size_mm: int = 12, verbose: bool = False):
        self.tape_size_mm = tape_size_mm
        self.verbose = verbose

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def print_text(self, text: str, copies: int = 1, **render_kwargs) -> None:
        """Render *text* and print it *copies* times.

        Every copy ends with a Form Feed, so each one starts from the same
        registration — like pressing the printer's button before every label.
        """
        if copies < 1:
            raise ValueError("copies must be >= 1")
        img = render.render_text(text, **render_kwargs)
        for i in range(copies):
            if self.verbose and copies > 1:
                print(f"Copy {i + 1}/{copies} …")
            self.print_image(img)

    def print_image(self, img: Image.Image) -> None:
        """Print a 1-bit PIL image, then Form Feed to the tear point."""
        label_matrix = self._image_to_matrix(img)
        device = self._detect()
        try:
            # Imported here so the module imports cleanly on machines
            # without dymoprint installed.
            from dymoprint.dymo_print_engines import DymoLabeler

            lm = DymoLabeler(
                device.devout, device.devin, synwait=64,
                tape_size_mm=self.tape_size_mm,
            )
            lm.tapeColor(0)
            for row in label_matrix:
                lm.line(row)
            # Small margin only — the gap sensor is still ahead of us.
            lm.skipLines(TRAILING_BLANK_LINES)
            # ESC E: firmware seeks the next label gap via its sensor and
            # advances to the tear bar. This is the whole trick.
            lm.cut()
            lm.statusRequest()
            lm.sendCommand()
        finally:
            usb.util.dispose_resources(device.dev)
        # Give the firmware a beat to finish feeding before we return.
        time.sleep(0.5)

    def form_feed(self) -> None:
        """Advance to the next label's tear point without printing.

        Useful to re-sync registration manually — the USB equivalent of
        tapping the printer's button once.
        """
        device = self._detect()
        try:
            from dymoprint.dymo_print_engines import DymoLabeler

            lm = DymoLabeler(
                device.devout, device.devin, synwait=64,
                tape_size_mm=self.tape_size_mm,
            )
            lm.cut()
            lm.statusRequest()
            lm.sendCommand()
        finally:
            usb.util.dispose_resources(device.dev)

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _detect(self):
        from dymoprint.detect import detect_device

        try:
            return detect_device()
        except (SystemExit, RuntimeError) as exc:
            raise PrinterNotFoundError(
                "No Dymo printer found on USB.\n"
                "Checklist:\n"
                "  - printer plugged in and powered on (USB ID 0922:0021)\n"
                "  - your user is in the 'lp' group "
                "(sudo usermod -aG lp $USER, then log out/in)\n"
                "    so /dev/bus/usb/* is readable without sudo"
            ) from exc

    @staticmethod
    def _image_to_matrix(img: Image.Image) -> list[list[int]]:
        """Convert a 1-bit PIL image to dymoprint's row-major byte matrix."""
        if img.mode != "1":
            img = img.convert("1")
        # Rows must span the label width; the first row is the left edge.
        rotated = img.transpose(Image.ROTATE_270)
        stream: bytes = rotated.tobytes()
        row_len = int(math.ceil(img.height / 8))
        if len(stream) // row_len != img.width:
            raise ValueError("Internal bitmap conversion error")
        rows = [stream[i : i + row_len] for i in range(0, len(stream), row_len)]
        return [array.array("B", r).tolist() for r in rows]


def print_text(text: str, copies: int = 1, verbose: bool = False, **render_kwargs) -> None:
    """One-shot convenience API: render *text* and print it.

    Example:
        >>> from muse_print import print_text
        >>> print_text("Giulia")
    """
    LabelPrinter(verbose=verbose).print_text(text, copies=copies, **render_kwargs)
