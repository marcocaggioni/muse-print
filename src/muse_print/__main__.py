"""Support ``python -m muse_print "Some Text"``."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
