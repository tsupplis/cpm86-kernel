#!/usr/bin/env python3
"""Entry point for the a86 reconstruction tools; the code lives in a86/."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from a86.cli import main

if __name__ == '__main__':
    main()
