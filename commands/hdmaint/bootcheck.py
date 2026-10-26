"""Validate boot images and remove only known absolute-segment declarations."""
from pathlib import Path
import sys


def normalize(source, destination):
    # ASM86 emits these declaration-only AUX records for symbolic JMPF targets.
    # No executable data is removed. Unexpected declarations fail the build.
    expected = {
        "mbr": [b":02000085006019", b":02000085000079"],
        "bootsect": [b":0200008507C0B2", b":02000085302029"],
        "loader": [],
    }[source.stem]
    lines = source.read_bytes().splitlines()
    declarations = [line for line in lines if len(line) >= 9 and line.startswith(b":")
                    and int(line[7:9], 16) >= 0x85]
    if declarations != expected:
        raise SystemExit(f"Unexpected absolute-segment records: {declarations!r}")
    destination.write_bytes(b"\r\n".join(line for line in lines
                                         if line not in expected) + b"\r\n")


def compare(reference):
    image = reference.read_bytes()
    # Original CMD: 128-byte header, 159h paragraphs of CODE, then DATA.
    data = image[128 + 0x159 * 16:]
    for name, offset, size in (("mbr", 0x0efe, 512),
                               ("bootsect", 0x10fe, 512),
                               ("loader", 0x18fe, 6144)):
        actual = Path(name + ".bin").read_bytes()
        if actual != data[offset:offset + size]:
            raise SystemExit(f"{name}: boot image differs from the original")
        if name == "bootsect" and actual != data[0x12fe:0x14fe]:
            raise SystemExit("Secondary boot-sector copy differs")
        print(f"PASS: {name}: {size} bytes match the original")


if __name__ == "__main__":
    if sys.argv[1] == "normalize":
        normalize(Path(sys.argv[2]), Path(sys.argv[3]))
    elif sys.argv[1] == "compare":
        compare(Path(sys.argv[2]))
    else:
        raise SystemExit("Expected normalize or compare")
