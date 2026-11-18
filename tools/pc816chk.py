#!/usr/bin/env python3
"""EXP bridge regression on disposable PCE disks; no host clock/disk writes."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
NATIVE_CPUS = ('8088', '8086')


def check(cpu, media, editor=False):
    folder = Path(tempfile.mkdtemp(prefix='pc816-'))
    print(f'{cpu}/{media}: {folder}', flush=True)

    def run(*args):
        return subprocess.run(args, cwd=folder, check=True, capture_output=True)

    (folder / 'diskdefs').write_bytes((ROOT / 'diskdefs').read_bytes())
    fmt = {'320': 'cpm86-320', '720': 'cpm86-720feat', '1440': 'cpm86-144feat'}[media]
    if media == '320':
        run('python3', str(ROOT / 'tools/cpm86twist.py'), 'untwist', str(ROOT / 'base-320.img'), 'work.img')
    else:
        # Same blank-media recipe as Makefile, isolated from repository clean.
        boot = bytearray((ROOT / 'extra/144boot2.bin').read_bytes())
        boot[511] = {'720': 72, '1440': 144}[media]
        (folder / 'bootsect.bin').write_bytes(boot)
        (folder / 'work.img').write_bytes(bytes([0xe5]) * int(media) * 1024)
        run('mkfs.cpm', '-f', fmt, '-b', 'bootsect.bin', 'work.img')
        run('python3', str(ROOT / 'tools/cpm86cfgsec.py'), 'work.img', 'atinit')
        for name in ('144bldr2', '144pat2'):
            run('cpmcp', '-f', fmt, 'work.img', str(ROOT / 'extra' / (name + '.cmd')), f'0:{name.upper()}.CMD')
    run('cpmcp', '-f', fmt, 'work.img', str(ROOT / 'cpmexp.sys'), '0:CPM.SYS')
    # 8080: print through BDOS, then RET through the bridge's return address.
    hello = bytes.fromhex('11 09 01 0e 09 cd 05 00 c9') + b'CPM816 HELLO PASS\r\n$'
    (folder / 'hello.com').write_bytes(hello)
    # Small 8080 test programs, with explicit opcode/fixup construction.
    # This avoids making the production build depend on an 8080 assembler.
    def probe(kind):
        code = bytearray()
        labels = {}
        fixups = []

        def emit(*values):
            code.extend(values)

        def address(opcode, label):
            emit(opcode, 0, 0)
            fixups.append((len(code) - 2, label))

        def bdos(number, label):
            address(0x11, label)              # LXI D,label
            emit(0x0e, number, 0xcd, 5, 0)    # MVI C,n / CALL 5

        if kind == 'args':
            expected = [(0x5c, bytes([1]) + b'ONE     TXT'),
                        (0x6c, bytes([2]) + b'TWO     COM')]
            tail = b'A:ONE.TXT B:TWO.COM'
            expected.append((0x80, bytes([len(tail)]) + tail))
            for base, data in expected:
                for offset, byte in enumerate(data):
                    at = base + offset
                    emit(0x3a, at & 255, at >> 8, 0xfe, byte)  # LDA / CPI
                    address(0xc2, 'fail')                     # JNZ
        else:
            bdos(22, 'fcb')                   # Make
            emit(0xfe, 255)
            address(0xca, 'fail')
            bdos(26, 'data')                  # Set DMA
            bdos(21, 'fcb')                   # Write one record
            emit(0xb7)
            address(0xc2, 'fail')
            bdos(16, 'fcb')                   # Close
            emit(0xfe, 255)
            address(0xca, 'fail')
        bdos(9, 'pass')
        emit(0xc9)
        labels['fail'] = len(code) + 0x100
        bdos(9, 'error')
        emit(0xc9)
        for label, data in [('pass', (kind.upper() + ' PASS\r\n$').encode()),
                            ('error', b'BRIDGE TEST FAILED\r\n$'),
                            ('fcb', bytes([0]) + b'BRIDGE  DAT' + bytes(24)),
                            ('data', b'8080 FILE WRITE VERIFIED'.ljust(128, b'.'))]:
            labels[label] = len(code) + 0x100
            code.extend(data)
        for at, label in fixups:
            code[at:at+2] = labels[label].to_bytes(2, 'little')
        return code

    for name in ('args', 'write'):
        (folder / (name + '.com')).write_bytes(probe(name))
        run('cpmcp', '-f', fmt, 'work.img', name + '.com', '0:' + name.upper() + '.COM')
    # Native 8086 command verifies that normal launching still works afterwards.
    (folder / 'native.asm').write_text('''bits 16
cpu 8086
org 0
 times 100h db 0
 push cs
 pop ds
 mov dx,message
 mov cl,9
 int 224
 xor dx,dx
 xor cx,cx
 int 224
message db 'NATIVE PASS',13,10,'$'
''')
    run('nasm', '-f', 'bin', 'native.asm', '-o', 'native.bin')
    payload = (folder / 'native.bin').read_bytes()
    paras = (len(payload) + 15) // 16
    header = bytearray(128)
    header[0] = 1
    header[1:3] = paras.to_bytes(2, 'little')
    header[5:7] = (paras + 32).to_bytes(2, 'little')
    (folder / 'native.cmd').write_bytes(header + payload.ljust(paras * 16, b'\0'))
    clear_source = (folder / 'native.asm').read_text().replace("message db 'NATIVE PASS',13,10,'$'", "message times 24 db 13,10\n db 'CLEARED',13,10,'$'")
    (folder / 'clear.asm').write_text(clear_source)
    run('nasm', '-f', 'bin', 'clear.asm', '-o', 'clear.bin')
    clear = (folder / 'clear.bin').read_bytes()
    count = (len(clear) + 15) // 16
    clear_header = bytearray(header)
    clear_header[1:3] = count.to_bytes(2, 'little')
    clear_header[5:7] = (count + 32).to_bytes(2, 'little')
    (folder / 'clear.cmd').write_bytes(clear_header + clear.ljust(count * 16, b'\0'))
    # Read a line through BDOS 10; Ctrl-C must abort back to the CCP.
    abort = bytes.fromhex('11 0f 01 0e 09 cd 05 00 11 30 01 0e 0a cd 05 00 c9')
    abort = bytearray(abort)
    abort[1:3] = (0x111).to_bytes(2, 'little')
    abort.extend(b'ABORT READY$')
    abort.extend(bytes(0x30-len(abort)))
    abort.extend(bytes([20,0])+bytes(22))
    (folder / 'abort.com').write_bytes(abort)
    for name in ('hello.com', 'native.cmd', 'clear.cmd', 'abort.com'):
        run('cpmcp', '-f', fmt, 'work.img', name, '0:' + name.upper())
    # End marker is a native command, reached only after the submitted sequence.
    done = (folder / 'native.cmd').read_bytes().replace(b'NATIVE PASS', b'SUBMIT PASS')
    (folder / 'done.cmd').write_bytes(done)
    run('cpmcp', '-f', fmt, 'work.img', 'done.cmd', '0:DONE.CMD')
    run('cpmcp', '-f', fmt, 'work.img', str(ROOT / 'commands/submit/submit.cmd'), '0:SUBMIT.CMD')
    (folder / 'check.txt').write_bytes(b'NATIVE TYPE PASS\r\n\x1a')
    run('cpmcp', '-f', fmt, 'work.img', 'check.txt', '0:CHECK.TXT')
    script = ('DIR\r\nTYPE CHECK.TXT\r\nNATIVE\r\nDONE\r\n'
              if cpu in NATIVE_CPUS else
              'WRITE\r\nHELLO\r\nSAVE 1 FIRST.COM\r\nSAVE 2 SECOND.COM\r\nSAVE 2 FIRST.COM\r\nSAVE 251 BAD.COM\r\nARGS $1 $2\r\nDONE\r\n')
    (folder / 'bridge.sub').write_bytes(script.encode() + b'\x1a')
    run('cpmcp', '-f', fmt, 'work.img', 'bridge.sub', '0:BRIDGE.SUB')
    # Same basename proves CMD takes precedence over COM.
    run('cpmcp', '-f', fmt, 'work.img', 'hello.com', '0:NATIVE.COM')
    (folder / 'empty.com').write_bytes(b'')
    run('cpmcp', '-f', fmt, 'work.img', 'empty.com', '0:EMPTY.COM')
    (folder / 'large.com').write_bytes(bytes(0xfc00))
    run('cpmcp', '-f', fmt, 'work.img', 'large.com', '0:LARGE.COM')
    if media == '320':
        run('python3', str(ROOT / 'tools/cpm86twist.py'), 'twist', 'work.img', 'boot.img')
    else:
        (folder / 'boot.img').write_bytes((folder / 'work.img').read_bytes())
    cfg = (ROOT / 'cpm86-exp.cfg').read_text()
    cfg = re.sub(r'(?m)^path\s*=.*', 'path = "' + str(ROOT / 'rom') + '"', cfg)
    cfg = re.sub(r'disk\s*\{.*?\}', '', cfg, flags=re.S)
    cfg = cfg.replace('model = "8088"', f'model = "{cpu}"')
    cfg = cfg.replace('driver = "sdl"', 'driver = "null"').replace('sdl:lowpass=5000', 'null')
    cfg += '\ndisk { drive=0 type="auto" file="boot.img" }\n'
    (folder / 'test.cfg').write_text(cfg)
    with (folder / 'pce.log').open('wb') as log:
        process = subprocess.Popen(['pce-ibmpc', '-c', 'test.cfg', '-t', 'null', '-g', 'vga'],
                                   cwd=folder, stdin=subprocess.PIPE, stdout=log, stderr=log)
        sequence = 0

        def send(text):
            process.stdin.write((text + '\n').encode())
            process.stdin.flush()

        def screen():
            nonlocal sequence
            sequence += 1
            path = folder / f'screen{sequence}.bin'
            send(f'c 200000\nsave "{path}" bin b800:0 fa0')
            deadline = time.monotonic() + 15
            while not path.exists() or path.stat().st_size != 4000:
                assert process.poll() is None, 'PCE exited before screen capture'
                assert time.monotonic() < deadline, 'PCE capture timeout'
                time.sleep(.02)
            data = path.read_bytes()
            text = '\n'.join(data[i:i+160:2].decode('cp437') for i in range(0,4000,160))
            path.with_suffix('.txt').write_text(text)
            return text

        def wait(expected):
            deadline = time.monotonic() + 30
            last = ''
            while time.monotonic() < deadline:
                last = screen()
                if expected in last and (expected == 'ABORT READY' or any(line.strip() == 'A>' for line in last.splitlines()) or expected == 'HELLO?'):
                    return last
                if 'BRIDGE TEST FAILED' in last:
                    send('save "failure.bin" bin 0:0 20000')
                    screen()
                    raise AssertionError((expected, '8080 assertion failed', last))
            raise AssertionError((expected, last))

        def command(text):
            for char in text:
                keys = '+Shift Semicolon -Shift' if char == ':' else ('Space' if char == ' ' else char)
                send('key ' + keys + '\nc 10000')
            send('key Return')

        try:
            boot = wait('A>')
            assert ('CP/M-816' in boot) == (cpu not in NATIVE_CPUS), boot
            assert ('8080 Emulation : V20/V30' in boot) == (cpu not in NATIVE_CPUS), boot
            if editor:
                from editlive import check as check_editor
                check_editor(send, screen)
                editor = False
            command('native')
            wait('NATIVE PASS')
            if cpu in NATIVE_CPUS:
                command('hello')
                rejected = wait('HELLO?')
                assert 'CPM816 HELLO PASS' not in rejected
            else:
                command('hello')
                wait('CPM816 HELLO PASS')
                command('clear')
                wait('CLEARED')
                command('abort')
                wait('ABORT READY')
                send('key +Ctrl c -Ctrl')
                wait('A>')
                command('native')
                wait('NATIVE PASS')
                # Clear display before each assertion, so old output cannot pass.
                for text, expected in [('hello', 'CPM816 HELLO PASS'),
                                       ('args a:one.txt b:two.com', 'ARGS PASS'),
                                                                              ('empty', 'empty COM file'),
                                       ('large', 'COM file too large'),
                                       ('native', 'NATIVE PASS')]:
                    command('clear')
                    wait('CLEARED')
                    command(text)
                    wait(expected)
            command('clear')
            wait('CLEARED')
            command('submit bridge' + ('' if cpu in NATIVE_CPUS else ' a:one.txt b:two.com'))
            submitted = wait('SUBMIT PASS')
            required = ('NATIVE TYPE PASS', 'NATIVE PASS') if cpu in NATIVE_CPUS else ('CPM816 HELLO PASS', 'ARGS PASS', 'WRITE PASS', 'SAVE complete', 'SAVE: file exists', 'SAVE: invalid arguments or disk error')
            assert all(marker in submitted for marker in required), submitted
            assert 'BRIDGE TEST FAILED' not in submitted, submitted
            if cpu not in NATIVE_CPUS:
                command('save 1 gone.com')
                wait('SAVE: no retained 8080 program')
                command('abort')
                wait('ABORT READY')
                send('key +Ctrl c -Ctrl')
                wait('A>')
                command('save 1 abort.com')
                wait('SAVE: no retained 8080 program')
            print(f'PASS: {cpu}/{media}: SUBMIT sequence and parameters', flush=True)
            print(f'PASS: {cpu}/{media}: boot/banner, native CMD precedence, '
                  + ('unsupported COM rejection' if cpu in NATIVE_CPUS else 'Ctrl-C/native/COM recovery, 8080 return/repeat, arguments/FCBs, file write, empty/large rejection, native recovery'), flush=True)
        finally:
            if process.poll() is None:
                send('q')
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    if cpu not in NATIVE_CPUS:
        if media == '320':
            run('python3', str(ROOT / 'tools/cpm86twist.py'), 'untwist', 'boot.img', 'result.img')
        else:
            (folder / 'result.img').write_bytes((folder / 'boot.img').read_bytes())
        run('cpmcp', '-f', fmt, 'result.img', '0:BRIDGE.DAT', 'readback.dat')
        assert (folder / 'readback.dat').read_bytes() == b'8080 FILE WRITE VERIFIED'.ljust(128, b'.')
        for filename, size in (('FIRST.COM', 256), ('SECOND.COM', 512)):
            run('cpmcp', '-f', fmt, 'result.img', '0:' + filename, filename)
            assert (folder / filename).read_bytes() == hello.ljust(size, b'\0'), filename
        listing = run('cpmls', '-f', fmt, 'result.img').stdout.upper()
        assert b'BAD.COM' not in listing
        print(f'PASS: {cpu}/{media}: host verified BDOS write and SAVE bytes, repeat, bounds and overwrite refusal', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cpu', choices=['8088', '8086', 'v20', 'v30'], default='v20')
    parser.add_argument('--media', choices=['320', '720', '1440'], default='320')
    parser.add_argument('--editor', action='store_true')
    args = parser.parse_args()
    check(args.cpu, args.media, args.editor)
