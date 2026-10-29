#!/usr/bin/env python3
"""Prove that the kernel guards reject drift without modifying real outputs."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import kernel_check

ROOT = Path(__file__).resolve().parents[1]


def changed_hex(data):
    lines = data.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith(b':'):
            record = bytearray.fromhex(line[1:].decode().strip())
            if record[3] == 0x81 and record[0]:
                record[4] ^= 1
                record[-1] = -sum(record[:-1]) & 255
                lines[i] = b':' + record.hex().upper().encode() + b'\r\n'
                return b''.join(lines)
    raise AssertionError('No CODE load record')


class KernelGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='kernel-guard-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'tools').mkdir()
        manifest = ROOT / 'tools/kernel-baseline.json'
        shutil.copyfile(manifest, self.root / 'tools/kernel-baseline.json')
        m = json.loads(manifest.read_text())
        files = set(m['images']) | set(m['frozen_sources']) | set(m['module_hashes'])
        files.update(name for pair in m['module_pairs'] for name in pair)
        for name in files:
            shutil.copyfile(ROOT / name, self.root / name)

    def verify(self):
        with contextlib.redirect_stdout(io.StringIO()):
            kernel_check.check(self.root)

    def mutate(self, name):
        path = self.root / name
        data = bytearray(path.read_bytes())
        data[128] ^= 1
        path.write_bytes(data)

    def test_unchanged_build_passes(self):
        self.verify()

    def test_standard_image_drift_fails(self):
        self.mutate('cpm.sys')
        with self.assertRaisesRegex(ValueError, 'pinned kernel baseline'):
            self.verify()

    def test_expanded_image_drift_fails(self):
        self.mutate('cpmexp.sys')
        with self.assertRaisesRegex(ValueError, 'pinned kernel baseline'):
            self.verify()

    def test_frozen_reference_edit_fails(self):
        path = self.root / 'ccporg.a86'
        path.write_bytes(path.read_bytes() + b'\r\n; changed reference\r\n')
        with self.assertRaisesRegex(ValueError, 'frozen reference source'):
            self.verify()

    def test_reference_line_endings_are_portable(self):
        for name in ['ccporg.a86', 'bdosorg.a86', 'pcbioorg.a86']:
            path = self.root / name
            path.write_bytes(path.read_bytes().replace(b'\r\n', b'\n'))
        self.verify()

    def test_standard_module_drift_fails(self):
        path = self.root / 'ccp.h86'
        path.write_bytes(changed_hex(path.read_bytes()))
        with self.assertRaisesRegex(ValueError, 'ccp.h86: differs'):
            self.verify()

    def test_expanded_module_drift_fails(self):
        path = self.root / 'bdosexp.h86'
        path.write_bytes(changed_hex(path.read_bytes()))
        with self.assertRaisesRegex(ValueError, 'EXP baseline'):
            self.verify()


if __name__ == '__main__':
    unittest.main()
