#!/usr/bin/env python3
"""Convert CP/M-86 320K floppy images between physical CHS order and CP/M
logical track order.

pcbios.a86 SETUP_INTREG maps a CP/M track to CHS as:

    track <  40 : cylinder = track,      head = 0
    track >= 40 : cylinder = 79 - track, head = 1

so side 1 is written in *reverse* cylinder order. A raw sector dump of such a
disk stores tracks in CHS order (cyl0/h0, cyl0/h1, cyl1/h0, ...), which is not
the order cpmtools assumes. Untwist before running cpmtools, twist afterwards.

    untwist : physical CHS image -> logical image (for cpmtools)
    twist   : logical image      -> physical CHS image (for real hardware)
"""

import sys

TRACKS = 80
TRACK_LEN = 8 * 512  # 8 sectors of 512 bytes = one CP/M track (SPT=32 records)
IMAGE_LEN = TRACKS * TRACK_LEN


def chs_slot(track):
    """Index of `track` within a CHS-ordered image (cylinder-major, head-minor)."""
    if track < 40:
        cylinder, head = track, 0
    else:
        cylinder, head = 79 - track, 1
    return cylinder * 2 + head


def convert(data, to_logical):
    if len(data) != IMAGE_LEN:
        sys.exit(f"expected a {IMAGE_LEN}-byte 320K image, got {len(data)} bytes")
    out = bytearray(IMAGE_LEN)
    for track in range(TRACKS):
        src, dst = chs_slot(track), track
        if not to_logical:
            src, dst = dst, src
        out[dst * TRACK_LEN:(dst + 1) * TRACK_LEN] = \
            data[src * TRACK_LEN:(src + 1) * TRACK_LEN]
    return bytes(out)


def main(argv):
    if len(argv) != 4 or argv[1] not in ("untwist", "twist"):
        sys.exit(f"usage: {argv[0]} untwist|twist <in.img> <out.img>")
    with open(argv[2], "rb") as fh:
        data = fh.read()
    with open(argv[3], "wb") as fh:
        fh.write(convert(data, to_logical=argv[1] == "untwist"))


if __name__ == "__main__":
    main(sys.argv)
