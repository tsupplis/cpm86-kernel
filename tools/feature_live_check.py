#!/usr/bin/env python3
"""Boot 720K/1.44M 144FEAT images with a disposable hd_volume_check fixture.

Build the four standard/EXP feature images first. --fixture is read-only:
each emulator receives private copies of its disk images. Requires PCE,
cpmtools, and HDTEST.CMD produced by hd_volume_check.py in the fixture.
"""
from pathlib import Path
import argparse
import concurrent.futures
import re
import shutil
import struct
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--fixture', type=Path, required=True)
parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
args = parser.parse_args()
root = args.root.resolve()
fixture = args.fixture.resolve()


def test(case):
    variant, size = case
    folder = Path(tempfile.mkdtemp(prefix='cpm-feature-'))
    name = 'cpm86-' + ('exp-' if variant == 'exp' else '') + str(size)
    shutil.copyfile(root / (name + '-at.img'), folder / 'floppy.img')
    shutil.copyfile(root / 'diskdefs', folder / 'diskdefs')
    fmt = 'cpm86-' + ('144' if size == 1440 else '720') + 'feat'
    for source, target in [(fixture / 'hdtest.cmd', 'HDTEST.CMD'),
                           (root / 'commands/chkcpmfs/chkcpmfs.cmd', 'CHKCPMFS.CMD')]:
        subprocess.run(['cpmrm', '-f', fmt, 'floppy.img', '0:' + target],
                       cwd=folder, capture_output=True)
        subprocess.run(['cpmcp', '-f', fmt, 'floppy.img', str(source), '0:' + target],
                       cwd=folder, check=True, capture_output=True)
    image = bytearray((fixture / 'hard.img').read_bytes())
    lba, sectors = struct.unpack_from('<II', image, 454)
    label = image[lba * 512 + 1536:lba * 512 + 2048]
    start = struct.unpack_from('<H', label, 33)[0]
    heads, spt = label[37:39]
    base = (start + 1) * heads * spt * 512
    block_size = 128 << label[43]
    drm = struct.unpack_from('<H', label, 48)[0]
    # Reuse the occupied fixture, freeing only the previous HDTEST file.
    for i in range(drm + 1):
        at = base + i * 32
        if image[at] == 0 and image[at + 1:at + 12] == b'HDTEST  DAT':
            image[at] = 0xE5
    prefix = bytes(image[:lba * 512])
    suffix = bytes(image[(lba + sectors) * 512:])
    (folder / 'hard.img').write_bytes(image)
    cylinders = len(image) // (heads * spt * 512)
    del image
    config = (root / (name + '.cfg')).read_text()
    config = config.replace('driver = "sdl"', 'driver = "null"').replace('sdl:lowpass=5000', 'null')
    config = re.sub(r'(?m)^path\s*=\s*"([^"\n]+)"',
                    lambda m: 'path = "' + str((root / m[1]).resolve()) + '"', config)
    config = re.sub(r'floppy_disk_drives\s*=\s*\d+', 'floppy_disk_drives = 2', config)
    config = re.sub(r'disk\s*\{.*?\}', '', config, flags=re.S)
    config += '\ndisk { drive=0 type="auto" file="floppy.img" }\n'
    config += (f'disk {{ drive=128 type="image" file="hard.img" '
               f'c={cylinders} h={heads} s={spt} }}\n')
    (folder / 'test.cfg').write_text(config)
    commands = ['c f000000', 'save "boot.bin" bin b800:0000 fa0']
    keys = {' ': 'Space', ':': '+Shift Semicolon -Shift'}
    for snap, command in [('dir', 'dir c:'), ('io', 'hdtest'), ('check', 'chkcpmfs c:')]:
        for ch in command:
            commands += ['key ' + keys.get(ch, ch), 'c 200000']
        commands += ['key Return', 'c 40000000', f'save "{snap}.bin" bin b800:0000 fa0']
    commands += ['q']
    with (folder / 'pce.log').open('wb') as log:
        subprocess.run(['pce-ibmpc', '-c', 'test.cfg', '-t', 'null', '-g', 'vga'],
                       cwd=folder, input=('\n'.join(commands) + '\n').encode(),
                       stdout=log, stderr=log, check=True, timeout=360)

    def screen(name):
        data = (folder / (name + '.bin')).read_bytes()
        text = '\n'.join(bytes(data[i:i + 160:2]).decode('cp437')
                         for i in range(0, len(data), 160))
        (folder / (name + '.txt')).write_text(text)
        return text

    assert 'A>' in screen('boot'), (folder, screen('boot'))
    assert 'FILL0' in screen('dir'), (folder, screen('dir'))
    assert 'HDTEST PASS' in screen('io'), (folder, screen('io'))
    assert 'Consistency errors: 0' in screen('check'), (folder, screen('check'))
    actual = (folder / 'hard.img').read_bytes()
    assert actual[:lba * 512] == prefix, folder
    assert actual[(lba + sectors) * 512:] == suffix, folder
    records = []
    for i in range(drm + 1):
        entry = actual[base + i * 32:base + (i + 1) * 32]
        if entry[0] != 0 or entry[1:12] != b'HDTEST  DAT':
            continue
        extent = entry[12] + 32 * entry[14]
        count = (extent & 1) * 128 + entry[15]
        part = b''.join(actual[base + b * block_size:base + (b + 1) * block_size]
                        for b in struct.unpack('<8H', entry[16:]) if b)
        records.append((extent // 2, part[:count * 128]))
    data = b''.join(part for _, part in sorted(records))
    assert len(data) >= 512 * 1024, (folder, len(data))
    for i in range(len(data) // 128):
        assert data[i * 128:(i + 1) * 128] == struct.pack('<H', i) * 64, (folder, i)
    return (f'PASS: {variant} {size}K feature boot, DIR, disk-full writes, '
            f'guest/host readback, checker and partition guards; {folder}')


if __name__ == '__main__':
    cases = [(variant, size) for variant in ['stock', 'exp'] for size in [720, 1440]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(test, cases):
            print(result, flush=True)
