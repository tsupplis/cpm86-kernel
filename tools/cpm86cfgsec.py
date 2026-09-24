#!/usr/bin/env python3
"""Write the CP/M-86 BIOS configuration sector into a diskette image.

pcbios.a86 (LOAD_CFGSEC) reads cylinder 0, head 0, sector 2 into CFG_BUF and
only applies it when the first word is 0DDB2h. APPLY_CFG then consumes:

    +00  word  magic, must be 0DDB2h
    +02  word  MDSKSEG   - memory disk (M:) segment
    +04  byte  VFLAG     - write verify enabled
    +05  byte  DSKPRM+0  - first diskette parameter byte
    +10  20    CFG_PFK_SCAN, copied verbatim into KEYBUF
    +40  byte  CFG_SNDFLG - sound flag, 0FFh to keep the BIOS default beeps

That last field is why the "-at" images run atinit on boot: the BIOS stuffs it
into the keyboard buffer, so the CCP reads it as if it had been typed. It is
copied with `mov cx,0014h`, so the command may not exceed 20 bytes including
its terminating CR.

The whole 512-byte sector is cleared first when no valid sector is present. It
also carries CFG_FIDDSMEM, CFG_SNDFLG, the CFG_SERFLG/CFG_IOFLAG/CFG_PFKFLAG
switches and CFG_PFKTBL, and mkfs.cpm leaves the system tracks filled with 0E5h.
Left alone, CFG_FIDDSMEM would read 0E5E5h and the 1.44 MB Feature aborts the
boot with "FIDDS memory request is too large".

When the image already carries a valid sector its settings are kept and only
the startup command is written, so an "-at" image can be derived from its plain
counterpart without disturbing anything else.
"""

import sys

SECTOR = 0x200
SECTOR_LEN = 512
MAGIC = 0xDDB2
MDSKSEG = 0xD000
VFLAG = 0x00
DSKPRM0 = 0xCF
KEYBUF_OFF = SECTOR + 0x10
KEYBUF_LEN = 0x14
SNDFLG_OFF = SECTOR + 0x40
SNDFLG = 0xFF


def main(argv):
    if len(argv) != 3:
        sys.exit(f"usage: {argv[0]} <image> <startup-command>")
    image, command = argv[1], argv[2]

    keys = (command + "\r").encode("ascii") if command else b""
    if len(keys) > KEYBUF_LEN:
        sys.exit(f"startup command exceeds {KEYBUF_LEN} bytes with its CR")

    with open(image, "rb") as fh:
        data = bytearray(fh.read())

    if int.from_bytes(data[SECTOR:SECTOR + 2], "little") != MAGIC:
        data[SECTOR:SECTOR + SECTOR_LEN] = bytes(SECTOR_LEN)
        data[SECTOR:SECTOR + 6] = (
            MAGIC.to_bytes(2, "little")
            + MDSKSEG.to_bytes(2, "little")
            + bytes([VFLAG, DSKPRM0])
        )
        data[SNDFLG_OFF] = SNDFLG

    data[KEYBUF_OFF:KEYBUF_OFF + KEYBUF_LEN] = keys.ljust(KEYBUF_LEN, b"\0")

    with open(image, "wb") as fh:
        fh.write(bytes(data))


if __name__ == "__main__":
    main(sys.argv)
