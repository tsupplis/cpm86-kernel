#!/usr/bin/env python3
"""Compact HELP indexer input without changing its eight-column tab display."""
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
original = path.read_bytes()
def compact(line):
    def spaces(match):
        column = len(line[:match.start()].expandtabs(8))
        remaining = len(match[0])
        result = bytearray()
        while remaining:
            width = 8 - column % 8
            if width > 1 and remaining >= width:
                result.append(9)
                remaining -= width
                column += width
            else:
                result.append(32)
                remaining -= 1
                column += 1
        return bytes(result)
    return re.sub(rb' {2,}', spaces, line)
compacted = b'\n'.join(compact(line) for line in original.split(b'\n'))
assert compacted.expandtabs(8) == original.expandtabs(8), 'HELP display changed'
path.write_bytes(compacted)
