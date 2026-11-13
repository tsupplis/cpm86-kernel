#!/usr/bin/env python3
"""Preserve the fixed kernel byte signatures used by the 144FEAT patches."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The frozen reference provides the exact old bytes expected by 144PAT2 and
# 144BLDR2. Include the CALL displacement in patch W, not just its address.
HOOKS = {
    "BDOS stack": (0x0B31, 3),
    "floppy reset": (0x2D18, 44),
    "floppy geometry": (0x2D4F, 17),
    "sector buffer": (0x2BEB, 3),
    "track buffer": (0x2D95, 3),
    "break stack": (0x2EB7, 3),
    "FIDD display (W)": (0x3E89, 7),
    "cold start (X)": (0x3D15, 9),
    "RAM disk (Y)": (0x3DF9, 25),
    "FIDD request (Z)": (0x3E59, 7),
}
reference = (ROOT / "cpmorg.sys").read_bytes()[128:]
for name in ("cpm.sys", "cpmexp.sys"):
    image = (ROOT / name).read_bytes()[128:]
    for label, (start, length) in HOOKS.items():
        assert image[start:start + length] == reference[start:start + length], (
            name, label, hex(start), "144FEAT signature changed")
    print(f"PASS: {name}: all {len(HOOKS)} fixed 144FEAT hook signatures")

# The 8080-model kernel places every module's code/data in one address space.
# Individual module baselines cannot detect cross-module overwrite.
from kernel_check import image_map
for modules in (("ccp", "bdos", "pcbios"), ("ccpexp", "bdosexp", "pcbioexp")):
    occupied = {}
    for module in modules:
        for (kind, address), byte in image_map(ROOT / (module + ".h86")).items():
            assert address not in occupied, (hex(address), occupied.get(address), module,
                                             "kernel modules overlap")
            occupied[address] = module
    print("PASS: no emitted CCP/BDOS/BIOS overlaps:", ", ".join(modules))
