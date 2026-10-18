# Quickstart

Get from a fresh Raspberry Pi to your first perfectly-registered label in
about ten minutes.

## What you need

- Raspberry Pi 4 (or similar) running Raspberry Pi OS / Debian 13 (trixie)
- Dymo LabelWriter 450 Turbo, plugged in via USB and powered on
- Internet access for `pip`

## 1. USB access

The printer speaks raw USB — no CUPS, no print spooler. Your user needs
permission to open the USB device:

```bash
sudo usermod -aG lp $USER
```

Then **log out and back in** (group membership only applies to new logins).
Verify:

```bash
lsusb | grep -i dymo
# Bus 001 Device 004: ID 0922:0021 Dymo-CoStar Corp. LabelWriter 450 Turbo
```

## 2. Install

```bash
pip install --break-system-packages muse-print
```

(The `--break-system-packages` flag is required on Debian 13 — see
[Drivers](drivers.md) for why.)

## 3. Print

```bash
muse-print "Hello World"
```

Tear off your label at the tear bar. Now print three in a row:

```bash
muse-print -n 3 "Giulia"
```

All three land in exactly the same place. That's the whole point of this
project — see [The Journey](the-journey.md) for why that's hard.

## 4. From Python

```python
from muse_print import print_text

print_text("Stella")
print_text("Alessandro", copies=2)
```

## Useful commands

```bash
muse-print --help            # all options
muse-print --feed-only        # advance to the tear point without printing
                             # (USB equivalent of tapping the printer button)
muse-print --font-size 120 "Small text"
```

## Troubleshooting

**`No Dymo printer found on USB`**
: Printer unplugged or powered off, or you're not in the `lp` group yet
  (remember to log out/in after `usermod`).

**USB timeouts / device goes silent mid-print**
: Reset the USB port (needs sudo once):
  ```bash
  echo 0 | sudo tee /sys/bus/usb/devices/1-1.2/authorized
  echo 1 | sudo tee /sys/bus/usb/devices/1-1.2/authorized
  ```
  The exact device path (`1-1.2`) varies — find yours under
  `/sys/bus/usb/devices/`.

**Text looks shifted to one side**
: The 450 Turbo biases output toward one edge. `render_text()` applies a
  left shift (default 90 px) to compensate; tune `left_shift` if your
  stock differs. See [Python API](api.md).
