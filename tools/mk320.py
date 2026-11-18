#!/usr/bin/env python3
"""Create an empty, bootable 320K CP/M image in logical track order.

Run beside the project's diskdefs. Boot inputs are explicit; this helper has
no OS detection, configuration policy, payload installation or track twisting.
"""

import argparse
from pathlib import Path
import subprocess

IMAGE_SIZE = 320 * 1024
BOOT_TRACK_SIZE = 4096
SIDES_OFFSET = 511
LOADER_OFFSET = 0x900
ERASED_BYTE = 0xE5


def initialize_directory(image, label):
    """Reserve CP/M Plus timestamp entries and install a disabled-date label.

    The 64-entry directory starts after the boot track. Every fourth entry
    holds timestamps for the preceding three. Zero label flags preserve the
    original distribution's default: recording dates is initially disabled.
    """
    directory = bytearray([ERASED_BYTE]) * (64 * 32)
    for entry in range(3, 64, 4):
        offset = entry * 32
        directory[offset:offset + 32] = bytes(32)
        directory[offset] = 0x21
    directory[:32] = bytes(32)
    directory[0] = 0x20
    directory[1:12] = label.ljust(11, b' ')
    image.seek(BOOT_TRACK_SIZE)
    image.write(directory)


def create_image(output, boot_file, loader_file, disk_format, label=None):
    """Format output and install the two boot stages in the reserved track.

    The erased configuration sector deliberately retains BIOS defaults.
    Validate boot inputs before creating or overwriting the output image.
    """
    if label is not None:
        label = label.encode('ascii')
        if not 1 <= len(label) <= 11:
            raise ValueError('Volume label must contain 1 to 11 ASCII characters')

    boot_code = boot_file.read_bytes()
    loader_code = loader_file.read_bytes()
    if not 0 < len(boot_code) <= SIDES_OFFSET:
        raise ValueError('Boot code must fit before the sides marker')
    if not 0 < len(loader_code) <= BOOT_TRACK_SIZE - LOADER_OFFSET:
        raise ValueError('Loader must fit within the reserved boot track')

    output.write_bytes(bytes([ERASED_BYTE]) * IMAGE_SIZE)
    subprocess.run(['mkfs.cpm', '-f', disk_format, str(output)], check=True)

    boot_track = bytearray([ERASED_BYTE]) * BOOT_TRACK_SIZE
    boot_track[:len(boot_code)] = boot_code
    boot_track[SIDES_OFFSET] = 1
    boot_track[LOADER_OFFSET:LOADER_OFFSET + len(loader_code)] = loader_code
    with output.open('r+b') as image:
        image.write(boot_track)
        if label is not None:
            initialize_directory(image, label)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--boot', type=Path, required=True)
    parser.add_argument('--loader', type=Path, required=True)
    parser.add_argument('--format', choices=('cpm86-320', 'ccpm86-320'),
                        required=True)
    parser.add_argument('--label', help='CP/M Plus volume label; reserves timestamp slots')
    args = parser.parse_args()
    create_image(args.output, args.boot, args.loader, args.format, args.label)


if __name__ == '__main__':
    main()
