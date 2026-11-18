#!/usr/bin/env python3
"""Check native floppy hooks, preserved BIOS sites and module boundaries."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The frozen reference pins unrelated BIOS instructions, including CALL
# displacements. Only the two native floppy hooks intentionally differ.
HOOKS = {
    "BDOS stack": (0x0B31, 3),
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
            name, label, hex(start), "preserved BIOS instruction changed")
    assert image[0x4c86:0x4c8a] == b'FDN1', (name, 'native capability missing')
    import sys
    sys.path.insert(0, str(ROOT / 'commands/hdmaint'))
    from check_capacity import symbols
    names = symbols(ROOT / ('pcbios.sym' if name == 'cpm.sys' else 'pcbioexp.sym'))
    for site, opcode, target in [(0x2d18, 0xe9, 'FDRESET'),
                                 (0x2d4f, 0xe8, 'FDREGS')]:
        assert image[site] == opcode, (name, hex(site), 'native hook opcode')
        displacement = int.from_bytes(image[site+1:site+3], 'little', signed=True)
        assert site+3+displacement == names[target], (name, target, 'native hook target')
    assert image[0x2d62:0x2d8f] == reference[0x2d62:0x2d8f], (name, 'hard-disk CHS changed')
    print(f"PASS: {name}: {len(HOOKS)} preserved hooks, 2 native hooks, native marker and HD CHS")

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
