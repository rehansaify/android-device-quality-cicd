"""Executable package entrypoint for python -m device_quality."""

import sys

from device_quality.runner import main

if __name__ == "__main__":
    sys.exit(main())
