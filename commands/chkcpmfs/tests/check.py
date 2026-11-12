"""Exercise the actual CHKCPMFS binary with synthetic BDOS directory records."""
from pathlib import Path
import struct
import subprocess
import tempfile

COMMAND = Path(__file__).resolve().parents[1]


def entry(name, blocks=(), *, user=0, extent=0, records=0, module=0, wide=False):
    stem, suffix = name.upper().split(".")
    assert 0 < len(stem) <= 8 and len(suffix) <= 3
    result = bytearray(32)
    result[0] = user
    result[1:12] = (stem.ljust(8) + suffix.ljust(3)).encode("ascii")
    result[12], result[14], result[15] = extent, module, records
    assert len(blocks) <= (8 if wide else 16)
    for index, block in enumerate(blocks):
        if wide:
            struct.pack_into("<H", result, 16 + index * 2, block)
        else:
            result[16 + index] = block
    return bytes(result)


def cases(version):
    system = [
        entry("CCPM.SYS", range(start, start + count), extent=extent, records=rc)
        for start, count, extent, rc in (
            (1, 16, 1, 128), (17, 16, 3, 128), (33, 16, 5, 128),
            (49, 16, 7, 128), (65, 16, 9, 128), (81, 14, 11, 88))
    ]
    other_users = [
        entry("USER1.TXT", [95], user=1, records=1),
        entry("USER15.TXT", [96], user=15, records=1),
    ]
    yield "system-and-users", system + other_users, {}, [
        "Directory entries scanned: 8  block references checked: 96",
        "Consistency errors: 0",
    ]
    yield "crosslink-system", system + [
        entry("USER1.TXT", [1], user=1, records=1),
    ], {}, [
        "USER 1 FILE USER1   .TXT: BLOCK 1 IS REFERENCED MORE THAN ONCE",
        "Consistency errors: 1",
    ]
    damaged_system = list(system)
    damaged_extent = bytearray(damaged_system[4])
    damaged_extent[16] = 1
    damaged_system[4] = bytes(damaged_extent)
    yield "crosslink-in-system", damaged_system, {}, [
        "USER 0 FILE CCPM    .SYS: BLOCK 1 IS REFERENCED MORE THAN ONCE",
        "Consistency errors: 1",
    ]
    yield "sparse", [entry("SPARSE.DAT", [1, 0, 3], records=48)], {}, [
        "block references checked: 2", "Consistency errors: 0",
    ]
    yield "allocated-past-record-count", [
        entry("FIRST.DAT", [1, 0, 0, 2], records=16),
        entry("SECOND.DAT", [2], records=1),
    ], {}, [
        "block references checked: 3",
        "BLOCK 2 IS REFERENCED MORE THAN ONCE",
        "Consistency errors: 1",
    ]
    yield "reserved-both-bytes", [
        entry("RESERVED.DAT", [2, 9], records=32),
    ], {"AL0": 0xA0, "AL1": 0x40}, [
        "BLOCK 2 IS RESERVED FOR THE DIRECTORY",
        "BLOCK 9 IS RESERVED FOR THE DIRECTORY",
        "Consistency errors: 2",
    ]
    yield "single-byte-limit", [
        entry("LIMIT.DAT", [157, 158], records=32),
    ], {}, [
        "block references checked: 2", "BLOCK 158 IS OUTSIDE THE DISK",
        "Consistency errors: 1",
    ]
    yield "wide-blocks", [
        entry("FIRST.DAT", [300, 600], records=32, wide=True),
        entry("SECOND.DAT", [300, 601], records=32, wide=True),
    ], {"DSM": 600, "EXM": 0}, [
        "block references checked: 4",
        "BLOCK 300 IS REFERENCED MORE THAN ONCE",
        "BLOCK 601 IS OUTSIDE THE DISK",
        "Consistency errors: 2",
    ]
    yield "cdos-large-volume", [
        entry("LARGE.DAT", [4031], records=64, wide=True),
        entry("LARGE.DAT", [3000], extent=2, records=64, wide=True),
    ], {"BSH": 6, "BLM": 63, "DSM": 4031, "DRM": 1023,
        "EXM": 1, "AL0": 0xf0}, ["Consistency errors: 0"]
    yield "large-volume-last-block", [
        entry("LAST.DAT", [4031,4032], records=128, wide=True),
    ], {"BSH": 6, "BLM": 63, "DSM": 4031, "DRM": 1023,
        "EXM": 1, "AL0": 0xf0}, ["BLOCK 4032 IS OUTSIDE THE DISK"]
    yield "invalid-extent", [
        entry("BAD.DAT", [1], extent=0x20, module=0x40, records=129),
    ], {}, [
        "RECORD COUNT EXCEEDS 128",
        "RESERVED EXTENT BITS ARE SET",
        "Consistency errors: 2",
    ]
    yield "extent-capacity", [
        entry("TOOBIG.DAT", [1], records=65, wide=True),
    ], {"BSH": 3, "DSM": 600, "EXM": 0,
        "EXPECTED_SEARCHES": 0,"EXPECTED_DMA_SETS": 1,"EXPECTED_RO_QUERIES": 0,
        "EXPECTED_PROTECTS": 0,"EXPECTED_RESETS": 0,"EXPECTED_FINAL_RO": 0,
        "EXPECTED_USER_SETS": 0,"EXPECTED_USER_MASK": 0}, [
        "ERROR: inconsistent or unsupported DPB; scan stopped.",
    ]
    yield "special-and-empty", [
        entry("LABEL.DAT", user=0x20),
        entry("STAMP.DAT", user=0x21),
        entry("XFCB.DAT", user=0x10),
        entry("DELETED.DAT", user=0xE5),
    ], {}, [
        "Directory entries scanned: 0  block references checked: 0",
        "Consistency errors: 0",
    ]
    yield "empty-directory", [], {}, [
        "Directory entries scanned: 0  block references checked: 0",
        "Consistency errors: 0",
    ]
    yield "duplicate-extent", [
        entry("SAME.DAT", [1], records=1),
        entry("SAME.DAT", [2], records=1),
    ], {}, [
        "DUPLICATE EXTENT GROUP 0",
        "Consistency errors: 1",
    ]
    yield "duplicate-extent-exm", [
        entry("MASKED.DAT", [1], extent=0, records=128),
        entry("MASKED.DAT", [2], extent=1, records=1),
    ], {"EXM": 1}, [
        "DUPLICATE EXTENT GROUP 0",
        "Consistency errors: 1",
    ]
    yield "distinct-extent-groups-exm", [
        entry("MASKED.DAT", [1], extent=0, records=128),
        entry("MASKED.DAT", [2], extent=2, records=1),
    ], {"EXM": 1}, [
        "Consistency errors: 0",
    ]
    yield "same-name-different-users", [
        entry("USERFILE.DAT", [1], user=0, records=1),
        entry("USERFILE.DAT", [2], user=1, records=1),
    ], {}, [
        "Directory entries scanned: 2  block references checked: 2",
        "Consistency errors: 0",
    ]
    readonly_name = bytearray(entry("ATTR.DAT", [2], records=1))
    readonly_name[9] |= 0x80
    yield "same-extent-ignore-attributes", [
        entry("ATTR.DAT", [1], records=1),
        bytes(readonly_name),
    ], {}, [
        "DUPLICATE EXTENT GROUP 0",
        "Consistency errors: 1",
    ]
    yield "directory-table-limit", [], {
        "DRM": 2048, "EXPECTED_SEARCHES": 0,
        "EXPECTED_DMA_SETS": 1, "EXPECTED_RO_QUERIES": 0,
        "EXPECTED_PROTECTS": 0, "EXPECTED_RESETS": 0,
        "EXPECTED_FINAL_RO": 0, "EXPECTED_USER_SETS": 0,
        "EXPECTED_USER_MASK": 0,
    }, ["ERROR: directory exceeds duplicate-check capacity; scan stopped."]
    yield "write-protection-restored", [
        entry("SAFE.DAT", [1], records=1),
    ], {}, [
        "Drive A  DPB block shift",
        "Directory entries scanned: 1  block references checked: 1",
        "Consistency errors: 0",
        "No inconsistencies found in checked entries.",
    ]
    yield "preserve-existing-read-only", [
        entry("SAFE.DAT", [1], records=1),
    ], {
        "INITIAL_RO": 1, "EXPECTED_RO_QUERIES": 1,
        "EXPECTED_PROTECTS": 0, "EXPECTED_RESETS": 0,
        "EXPECTED_FINAL_RO": 1,
    }, [
        "Drive was already read-only; preserving its RO state.",
        "Consistency errors: 0",
    ]
    yield "write-protection-failure", [], {
        "PROTECT_FAIL": 1, "EXPECTED_RO_QUERIES": 2,
        "EXPECTED_PROTECTS": 1, "EXPECTED_RESETS": 0,
        "EXPECTED_SEARCHES": 0, "EXPECTED_DMA_SETS": 1,
        "EXPECTED_FINAL_RO": 0,
        "EXPECTED_USER_SETS": 0, "EXPECTED_USER_MASK": 0,
    }, [
        "ERROR: could not establish drive write protection; scan stopped.",
        ("Check drive status with STAT; use Ctrl-C if needed."
         if (version & 0xff) < 0x30 else
         "Check drive status with SHOW; use SET A: [RW] if needed."),
    ]
    yield "trust-protection-vector-over-status", [], {
        "PROTECT_FAIL": 2, "EXPECTED_RO_QUERIES": 3,
        "EXPECTED_PROTECTS": 1, "EXPECTED_RESETS": 1,
        "EXPECTED_SEARCHES": 16, "EXPECTED_DMA_SETS": 2,
        "EXPECTED_FINAL_RO": 0,
        "EXPECTED_USER_SETS": 17, "EXPECTED_USER_MASK": 65535,
    }, [
        "No inconsistencies found in checked entries.",
    ]
    yield "write-protection-restore-failure", [
        entry("SAFE.DAT", [1], records=1),
    ], {
        "RESTORE_FAIL": 1, "EXPECTED_FINAL_RO": 1,
    }, [
        ("ERROR: drive write protection could not be restored; use Ctrl-C."
         if (version & 0xff) < 0x30 else
         "ERROR: drive write protection could not be restored; use SET A: [RW]."),
        "Scan completed with a state restoration error.",
    ]
    if (version & 0xff) >= 0x41:
        yield "dos-media", [], {
            "DOS_MEDIA": 1, "EXPECTED_SEARCHES": 0, "EXPECTED_DMA_SETS": 1,
            "EXPECTED_RO_QUERIES": 0, "EXPECTED_PROTECTS": 0,
            "EXPECTED_RESETS": 0, "EXPECTED_USER_SETS": 0,
            "EXPECTED_USER_MASK": 0,
        }, ["DOS media detected; no CP/M filesystem scan performed."]
    else:
        yield "dos-probe-gated", [
            entry("SAFE.DAT", [1], records=1),
        ], {"DOS_MEDIA": 1}, [
            "Directory entries scanned: 1  block references checked: 1",
            "Consistency errors: 0",
        ]
    yield "unsupported-dpb", [], {
        "BSH": 8, "EXPECTED_SEARCHES": 0, "EXPECTED_DMA_SETS": 1,
        "EXPECTED_RO_QUERIES": 0, "EXPECTED_PROTECTS": 0,
        "EXPECTED_RESETS": 0, "EXPECTED_USER_SETS": 0,
        "EXPECTED_USER_MASK": 0,
    }, ["ERROR: inconsistent or unsupported DPB; scan stopped."]


    # Layout validation must precede allocation interpretation or protection.
    for tag, bad in [('bad-mask',{'BLM':3}),('bad-exm',{'EXM':2}),
                     ('small-block',{'BSH':2}),('no-track',{'SPT':0}),
                     ('missing-directory',{'AL0':0}),('reserved-outside',{'DSM':0,'AL0':0xc0})]:
        overrides=dict(EXPECTED_SEARCHES=0,EXPECTED_DMA_SETS=1,EXPECTED_RO_QUERIES=0,
                       EXPECTED_PROTECTS=0,EXPECTED_RESETS=0,EXPECTED_FINAL_RO=0,
                       EXPECTED_USER_SETS=0,EXPECTED_USER_MASK=0)
        overrides.update(bad)
        yield tag,[],overrides,['ERROR: inconsistent or unsupported DPB; scan stopped.']
    for shift in range(3,8):
        yield 'valid-geometry-narrow', [entry('LAYOUT.DAT',[2 if shift==3 else 1],records=128)], {
            'BSH':shift,'EXM':(1<<(shift-3))-1,'AL0':0xc0 if shift==3 else 0x80}, ['Consistency errors: 0']
    for shift in range(4,8):
        yield 'valid-geometry-wide', [entry('LAYOUT.DAT',[1],records=128,wide=True)], {
            'BSH':shift,'DSM':600,'EXM':(1<<(shift-4))-1}, ['Consistency errors: 0']


def run_case(folder, image, version, name, entries, overrides, expected):
    assert image[0] == 1 and image[9] == 2, "unexpected CMD segment layout"
    code_size = struct.unpack_from("<H", image, 1)[0] * 16
    data_size = struct.unpack_from("<H", image, 10)[0] * 16
    assert len(image) >= 128 + code_size + data_size
    (folder / "code.bin").write_bytes(image[128:128 + code_size])
    (folder / "data.bin").write_bytes(
        image[128 + code_size:128 + code_size + data_size])
    directory = b"".join(entries)
    if overrides.get('REPAIR_FIXTURE'):
        directory += b'\xe5' * (((overrides.get('DRM',63)+4)//4)*128-len(directory))
    else:
        directory += bytes(max(128, (len(directory) + 127) // 128 * 128) - len(directory))
    (folder / "directory.bin").write_bytes(directory)
    settings = {
        "DIR_ENTRIES": len(entries), "BSH": 4, "EXM": 1, "DSM": 157,
        "DRM": 63,
        "AL0": 0x80, "AL1": 0, "DOS_MEDIA": 0, "INITIAL_DMA": 0x345,
        "BDOS_VERSION": version, "EXPECTED_SEARCHES": 16, "EXPECTED_DMA_SETS": 2,
        "INITIAL_RO": 0, "PROTECT_FAIL": 0, "RESTORE_FAIL": 0,
        "EXPECTED_RO_QUERIES": 3, "EXPECTED_PROTECTS": 1,
        "EXPECTED_RESETS": 1, "EXPECTED_FINAL_RO": 0,
        "INITIAL_USER": 5, "EXPECTED_USER_SETS": 17,
        "EXPECTED_USER_MASK": 65535,
    }
    settings.update(overrides)
    if (version & 0xff) >= 0x41:
        settings["EXPECTED_SEARCHES"] += 1
        settings["EXPECTED_DMA_SETS"] += 2
    if overrides.get('REPAIR_FIXTURE'):
        import re
        mapping = (COMMAND/'chkcpmfs.mp2').read_text(errors='replace')
        public = {name:int(off,16) for off,name in re.findall(r'0000H\s+([0-9A-F]+)H\s+PUB\s+(RAW\w+)',mapping)}
        assert len(public)==5,public
        (folder/'raw.inc').write_text(''.join(f'%define {name} {off}\n' for name,off in public.items()))
    (folder / "case.inc").write_text(
        "".join(f"%define {key} {value}\n" for key, value in settings.items()))
    subprocess.run(
        ["nasm", "-f", "bin", str(COMMAND / "tests/check.asm"),
         "-I", str(folder) + "/", "-o", str(folder / "check.com")],
        cwd=folder, check=True, capture_output=True,
    )
    result = subprocess.run(
        ["emu2", str(folder / "check.com")], cwd=folder,
        capture_output=True, timeout=15,
    )
    output = result.stdout.decode("ascii", errors="replace")
    assert result.returncode == 0, (name, result.returncode, output, result.stderr)
    for text in expected:
        assert text in output, (name, text, output)
    if "Consistency errors: 0" in expected:
        assert "ERROR:" not in output, (name, output)
    if not (settings["DOS_MEDIA"] and (version & 0xff) >= 0x41) and settings["BSH"] <= 7:
        assert "skipped" not in output.lower(), (name, output)
    return output


def main():
    image = (COMMAND / "chkcpmfs.cmd").read_bytes()
    with tempfile.TemporaryDirectory(prefix="chkcpmfs-bdos-") as directory:
        folder = Path(directory)
        total = 0
        for version in (0x0022, 0x1431, 0x1441):
            for name, entries, overrides, expected in cases(version):
                run_case(folder, image, version, name, entries, overrides, expected)
                total += 1
            name, entries, overrides, expected = next(cases(version))
            for tail in ('A: [V]', 'a: /v'):
                run_case(folder, image, version, 'verbose', entries,
                         dict(overrides, TAIL='"'+tail+'"'),
                         expected + ['USER 1 FILE USER1   .TXT', 'USER 15 FILE USER15  .TXT'])
                total += 1
    print(f"PASS: {total} CHKCPMFS synthetic BDOS and DMA cases across three OS versions")


if __name__ == "__main__":
    main()
