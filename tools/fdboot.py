#!/usr/bin/env python3
"""Boot both native BIOSes and verify persisted floppy writes in PCE.

All images and evidence stay under local/native-tests. The large-media
fixtures deliberately allocate CPM.SYS above block 255 and on side two.
"""
from pathlib import Path
import re
import subprocess
import time
from cpm86twist import convert

ROOT = Path(__file__).resolve().parents[1]
FORMATS = [(160, 'ibmpc-514ss', 40, 1, 8, 0),
           (320, 'cpm86-320', 40, 2, 8, 160*1024),
           (720, 'cpm86-720', 80, 2, 9, 520*1024),
           (1200, 'cpm86-1200', 80, 2, 15, 1040*1024),
           (1440, 'cpm86-1440', 80, 2, 18, 1040*1024)]


def check(variant, geometry):
    kib, fmt, cylinders, heads, sectors, filler = geometry
    folder = ROOT / 'local/native-tests' / f'{variant}-{kib}'
    folder.mkdir(parents=True, exist_ok=True)

    def run(*args):
        return subprocess.run(args, cwd=folder, check=True, capture_output=True)

    (folder/'diskdefs').write_bytes((ROOT/'diskdefs').read_bytes())
    disk = folder/'work.img'
    disk.write_bytes(bytes([0xe5])*(kib*1024))
    run('mkfs.cpm', '-f', fmt, str(disk))
    data = bytearray(disk.read_bytes())
    boot = (ROOT/'commands/dskmaint/bootsect.bin').read_bytes()
    loader = (ROOT/'commands/dskmaint/loader.bin').read_bytes()
    assert len(boot) < 510 and len(loader) <= 0x700
    data[:len(boot)] = boot
    data[511] = heads-1 if kib < 720 else kib//10
    if kib >= 720:
        data[510] = 1
    data[0x900:0x900+len(loader)] = loader
    disk.write_bytes(data)
    if filler:
        (folder/'filler.dat').write_bytes(bytes([0x5a])*filler)
        run('cpmcp', '-T', 'raw', '-f', fmt, str(disk), 'filler.dat', '0:FILLER.DAT')
    run('cpmcp', '-T', 'raw', '-f', fmt, str(disk), str(ROOT/(variant+'.sys')), '0:CPM.SYS')
    # A native command writes enough records to cross several cache windows.
    (folder/'probe.asm').write_text('''bits 16
cpu 8086
org 0
 times 100h db 0
 push cs
 pop ds
 push cs
 pop es
 cld
 mov dx,fcb
 mov cl,22
 int 224
 cmp al,255
 je failed
 mov dx,buffer
 mov cl,26
 int 224
next:
 push ds
 pop es
 cld
 mov di,buffer
 mov al,[number]
 mov cx,128
 rep stosb
 mov dx,fcb
 mov cl,21
 int 224
 or al,al
 jnz failed
 inc byte [number]
 cmp byte [number],64
 jb next
 mov dx,fcb
 mov cl,16
 int 224
 cmp al,255
 je failed
 mov dx,pass
 jmp done
failed:
 mov dx,error
done:
 mov cl,9
 int 224
 xor dx,dx
 xor cx,cx
 int 224
number db 0
fcb db 0,'OUTPUT  DAT'
 times 24 db 0
buffer times 128 db 0
pass db 'NATIVE WRITE PASS',13,10,'$'
error db 'NATIVE WRITE FAILED',13,10,'$'
''')
    run('nasm', '-f', 'bin', 'probe.asm', '-o', 'probe.bin')
    payload = (folder/'probe.bin').read_bytes()
    paras = (len(payload)+15)//16
    header = bytearray(128)
    header[0] = 1
    header[1:3] = paras.to_bytes(2, 'little')
    header[5:7] = (paras+32).to_bytes(2, 'little')
    (folder/'probe.cmd').write_bytes(header+payload.ljust(paras*16, b'\0'))
    run('cpmcp', '-T', 'raw', '-f', fmt, str(disk), 'probe.cmd', '0:PROBE.CMD')
    (folder/'boot.img').write_bytes(convert(disk.read_bytes(), False) if kib == 320 else disk.read_bytes())
    cfg = (ROOT/'cpm86-exp-320.cfg').read_text()
    cfg = re.sub(r'(?m)^path\s*=.*', f'path = "{ROOT / "rom"}"', cfg)
    cfg = re.sub(r'disk\s*\{.*?\}', '', cfg, flags=re.S)
    cfg = cfg.replace('driver = "sdl"', 'driver = "null"').replace('sdl:lowpass=5000', 'null')
    cfg += '\ndisk { drive=0 type="auto" file="boot.img" }\n'
    (folder/'test.cfg').write_text(cfg)
    with (folder/'pce.log').open('wb') as log:
        process = subprocess.Popen(['pce-ibmpc', '-c', 'test.cfg', '-t', 'null', '-g', 'vga'],
                                   cwd=folder, stdin=subprocess.PIPE, stdout=log, stderr=log)
        sequence = 0

        def send(text):
            process.stdin.write((text+'\n').encode())
            process.stdin.flush()

        def wait(expected):
            nonlocal sequence
            deadline = time.monotonic()+30
            text = ''
            while time.monotonic() < deadline:
                sequence += 1
                path = folder/f'screen{sequence}.bin'
                path.unlink(missing_ok=True)
                send(f'c 200000\nsave "{path}" bin b800:0 fa0')
                capture = time.monotonic()+10
                while not path.exists() or path.stat().st_size != 4000:
                    assert process.poll() is None, 'PCE exited'
                    assert time.monotonic() < capture, 'capture timeout'
                    time.sleep(.02)
                data = path.read_bytes()
                text = '\n'.join(data[i:i+160:2].decode('cp437') for i in range(0,4000,160))
                (folder/'screen.txt').write_text(text)
                if expected in text and any(line.strip() == 'A>' for line in text.splitlines()):
                    return
            raise AssertionError((variant, kib, expected, text))

        try:
            wait('A>')
            for char in 'probe':
                send('key '+char+'\nc 10000')
            send('key Return')
            wait('NATIVE WRITE PASS')
            send('quit')
            process.wait(timeout=10)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    saved = (folder/'boot.img').read_bytes()
    disk.write_bytes(convert(saved, True) if kib == 320 else saved)
    run('cpmcp', '-T', 'raw', '-f', fmt, str(disk), '0:OUTPUT.DAT', 'output.dat')
    assert (folder/'output.dat').read_bytes() == b''.join(bytes([i])*128 for i in range(64))
    run('cpmcp', '-T', 'raw', '-f', fmt, str(disk), '0:CPM.SYS', 'system.sys')
    assert (folder/'system.sys').read_bytes() == (ROOT/(variant+'.sys')).read_bytes()
    print(f'PASS: {variant}/{kib}K: boot, 64 persisted records, system intact', flush=True)


if __name__ == '__main__':
    for variant in ('cpm', 'cpmexp'):
        for geometry in FORMATS:
            check(variant, geometry)
    print('PASS: 10 native floppy cases, 0 failures')
