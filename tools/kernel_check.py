#!/usr/bin/env python3
"""Guard kernel comment/style edits against emitted-byte or reference drift."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path, source=False):
    data = path.read_bytes()
    if source:
        data = data.replace(b'\r\n', b'\n')
    return hashlib.sha256(data).hexdigest()


def image_map(path):
    """Read ASM86 load records, stopping at EOF or DOS text EOF.

    DOS tools may leave stale bytes after Ctrl-Z when overwriting a longer
    output. Compare emitted addresses, not record wrapping or stale tails.
    Keep CODE/DATA/STACK/EXTRA byte spaces distinct.
    """
    result = {}
    for line in path.read_bytes().split(b'\x1a', 1)[0].splitlines():
        if not line.strip():
            continue
        if not line.startswith(b':'):
            raise ValueError(f'{path}: malformed HEX record')
        record = bytes.fromhex(line[1:].decode('ascii'))
        if len(record) != record[0] + 5 or sum(record) & 255:
            raise ValueError(f'{path}: bad HEX length/checksum')
        kind = record[3]
        if kind == 1:
            break
        if kind in (0x81, 0x82, 0x83, 0x84):
            address = int.from_bytes(record[1:3], 'big')
            for offset, byte in enumerate(record[4:-1]):
                key = kind, address + offset
                if key in result and result[key] != byte:
                    raise ValueError(f'{path}: conflicting bytes at {key}')
                result[key] = byte
    if not result:
        raise ValueError(f'{path}: no assembled load bytes')
    return result


def check(root):
    manifest = json.loads((root / 'tools/kernel-baseline.json').read_text())
    for name, expected in manifest['frozen_sources'].items():
        if digest(root / name, source=True) != expected:
            raise ValueError(f'{name}: frozen reference source changed')
    for name, expected in manifest['images'].items():
        if digest(root / name) != expected:
            raise ValueError(f'{name}: differs from the pinned kernel baseline')
    for name, expected in manifest.get('module_hashes', {}).items():
        emitted = image_map(root / name)
        payload = json.dumps(sorted((kind, address, byte)
                                    for (kind, address), byte in emitted.items()),
                             separators=(',', ':')).encode()
        if hashlib.sha256(payload).hexdigest() != expected:
            raise ValueError(f'{name}: emitted bytes differ from the EXP baseline')
        print(f'PASS: {name} matches its pre-cleanup baseline ({len(emitted)} bytes)')
    variants = manifest.get('variant_differences')
    if variants:
        standard = image_map(root / variants['standard'])
        expanded = image_map(root / variants['expanded'])
        differences = [[kind, address, standard.get((kind, address)),
                        expanded.get((kind, address))]
                       for kind, address in sorted(standard.keys() | expanded.keys())
                       if standard.get((kind, address)) != expanded.get((kind, address))]
        if differences != variants['bytes']:
            raise ValueError('unexpected standard/EXP BIOS differences')
        print('PASS: standard/EXP BIOS differ only in status color and version digit')
    for maintained, original in manifest['module_pairs']:
        left, right = image_map(root / maintained), image_map(root / original)
        if left != right:
            changed = sorted(k for k in left.keys() | right.keys()
                             if left.get(k) != right.get(k))
            kind, address = changed[0]
            raise ValueError(f'{maintained}: differs from {original} at '
                             f'record {kind:02X}, offset {address:04X}')
        print(f'PASS: {maintained} matches {original} ({len(left)} emitted bytes)')
    if (root / 'cpm.sys').read_bytes() != (root / 'cpmorg.sys').read_bytes():
        raise ValueError('cpm.sys differs from cpmorg.sys')
    print('PASS: complete kernel images and frozen references match the baseline')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        check(args.root)
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f'FAIL: {exc}')
