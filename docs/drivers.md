# Drivers

What gets installed on the Pi, and why — so you can reproduce this from a
fresh Debian 13 system.

## The short version

| Component | Choice | Why |
|---|---|---|
| Driver | `dymoprint` 2.5.0 via `pip` | Debian's `printer-driver-dymo` is empty; dymoprint speaks raw USB, no CUPS |
| Print pipeline | CUPS: **not used** | Direct USB is simpler and fully sufficient |
| Imaging | Pillow | Render text to 1-bit bitmaps |
| USB | pyusb (via dymoprint) | Raw USB transport |
| Permissions | user in `lp` group | Read/write `/dev/bus/usb/*` without sudo |

## Why not CUPS?

CUPS + a Dymo driver is the "normal" Linux printing path, but on Debian 13
(trixie) the `printer-driver-dymo` package ships **documentation only** —
no actual driver. Rather than backporting a driver or building CUPS filters,
`dymoprint` talks to the printer directly over USB. For a single-purpose
label printer driven by scripts, that's fewer moving parts and one less
daemon to keep alive.

## Installation

```bash
# USB device access (log out/in afterwards)
sudo usermod -aG lp $USER

# dymoprint 2.5.0 — the version this was developed and tested against
pip install --break-system-packages "dymoprint==2.5.0"

# muse-print itself (pulls dymoprint>=2.5.0, Pillow, pyusb)
pip install --break-system-packages muse-print
```

### About `--break-system-packages`

Debian 13's `pip` refuses to install into the system Python without this
flag ("externally managed environment," PEP 668). The alternatives are a
virtualenv or `pipx`; on a single-purpose Pi the flag is the pragmatic
choice. Nothing in this stack conflicts with Debian's own packages.

### Fonts

Text rendering needs a bold font. The default is DejaVu Sans Bold, which
ships with Debian:

```bash
# usually already present; if not:
sudo apt install fonts-dejavu-core
```

`muse_print.render.find_font()` checks `/usr/share/fonts/truetype/dejavu/`
(and the `/usr/share/fonts/TTF/` alternate) and raises a clear error if
neither exists.

## Permissions in detail

`dymoprint` opens the printer as a raw USB device. On Debian,
`/dev/bus/usb/*` nodes are owned by `root:lp`, so membership in the `lp`
group is what lets an unprivileged user print. Verify:

```bash
groups            # lp should be listed (after re-login)
lsusb -d 0922:0021
```

## USB timeouts

Once during development the printer stopped responding to USB transfers
(device present, transfers timing out). The fix was a USB port reset:

```bash
echo 0 | sudo tee /sys/bus/usb/devices/1-1.2/authorized
echo 1 | sudo tee /sys/bus/usb/devices/1-1.2/authorized
```

The path (`1-1.2`) is the physical port and varies by machine — look under
`/sys/bus/usb/devices/` for the entry whose `idVendor`/`idProduct` match
`0922`/`0021`. This needs sudo, but it's a once-in-a-while recovery step,
not part of normal operation.

## What dymoprint gives us (and what it doesn't)

`dymoprint` provides the USB transport and the protocol primitives:
`line()` (raster row), `skipLines()` (blank feed), `statusRequest()`,
and — critically — `cut()`, which sends the Form Feed (`ESC E`) that
muse-print is built around.

What it does *not* do is call `cut()` during normal printing, or manage
label registration at all. That's the gap muse-print fills: see
[ESC E](esc-e.md).
