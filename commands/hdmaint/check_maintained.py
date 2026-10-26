"""Non-destructive build checks for maintained HDMAINT and its frozen source."""
from pathlib import Path
import hashlib
import struct

FROZEN_SHA256 = "2ad4c897cf7e5ea5bf745aff8fd8847d6b1c587dc526e07e92530b445529e724"
assert hashlib.sha256(Path("hdmtorg.a86").read_bytes()).hexdigest() == FROZEN_SHA256, "Frozen source changed"
raw = Path("hdmaint.cmd").read_bytes()
assert [raw[i] for i in (0, 9, 18, 27)] == [1, 2, 3, 0], "Unexpected CMD groups"
code_size = struct.unpack_from("<H", raw, 1)[0] * 16
data_size = struct.unpack_from("<H", raw, 10)[0] * 16
assert struct.unpack_from("<H", raw, 19)[0] == 0, "EXTRA contains file data"
assert struct.unpack_from("<H", raw, 23)[0] == 0x800, "EXTRA allocation changed"
data = raw[128 + code_size:128 + code_size + data_size]
assert b"version 1.1N" in data, "Missing maintained version banner"
for name, offsets in (("mbr", (0xefe,)), ("bootsect", (0x10fe, 0x12fe)), ("loader", (0x18fe,))):
    payload = Path(name + ".bin").read_bytes()
    for offset in offsets:
        assert data[offset:offset + len(payload)] == payload, f"Embedded {name} differs"
print("PASS: frozen source digest; maintained version, CMD groups and boot images")
