#!/usr/bin/env python3
"""Issue #17 investigation: actual PCE disk swaps, no production changes.

Fixtures and reports stay under local/recovery-tests. Failed cases retain
images for inspection; successful cases remove them. Each run records its
kernel hash and independently inspects the resulting CP/M filesystem.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from cpm86twist import convert

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'commands/hdmaint'))
from check_capacity import symbols


def run(folder, *args, check=True):
    return subprocess.run(args, cwd=folder, capture_output=True, check=check)


def cmdfile(folder, source, name, *defines):
    run(folder, 'nasm', '-f', 'bin', *defines, str(source), '-o', name+'.bin')
    payload = (folder/(name+'.bin')).read_bytes()
    paras = (len(payload)+15)//16
    header = bytearray(128)
    header[0] = 1
    header[1:3] = paras.to_bytes(2, 'little')
    header[5:7] = (paras+32).to_bytes(2, 'little')
    (folder/(name+'.cmd')).write_bytes(header+payload.ljust(paras*16, b'\0'))


def media(folder, name, kib, files):
    fmt = f'cpm86-{kib}'
    image = folder/(name+'.raw')
    image.write_bytes(bytes([0xe5])*(kib*1024))
    run(folder, 'mkfs.cpm', '-f', fmt, image.name)
    data = bytearray(image.read_bytes())
    boot = (ROOT/'commands/dskmaint/bootsect.bin').read_bytes()
    loader = (ROOT/'commands/dskmaint/loader.bin').read_bytes()
    data[:len(boot)] = boot
    data[510:512] = bytes([1, 1 if kib == 320 else kib//10])
    data[0x900:0x900+len(loader)] = loader
    image.write_bytes(data)
    for host, guest in files:
        run(folder, 'cpmcp', '-T', 'raw', '-f', fmt, image.name, str(host), '0:'+guest)
    physical = folder/(name+'.img')
    logical = image.read_bytes()
    physical.write_bytes(convert(logical, False) if kib == 320 else logical)
    image.unlink()
    return physical


class Guest:
    def __init__(self, folder, cpu):
        self.folder, self.sequence = folder, 0
        cfg = (ROOT/'cpm86-exp-320.cfg').read_text()
        cfg = re.sub(r'(?m)^path\s*=.*', f'path = "{ROOT / "rom"}"', cfg)
        cfg = re.sub(r'disk\s*\{.*?\}', '', cfg, flags=re.S)
        cfg = cfg.replace('model = "8088"', f'model = "{cpu}"')
        cfg = cfg.replace('driver = "sdl"', 'driver = "null"').replace('sdl:lowpass=5000', 'null')
        cfg += '\ndisk { drive=0 type="auto" file="boot.img" }\n'
        cfg += '\ndisk { drive=1 type="auto" file="old.img" }\n'
        (folder/'test.cfg').write_text(cfg)
        self.log = (folder/'pce.log').open('wb')
        self.process = subprocess.Popen(['pce-ibmpc', '-c', 'test.cfg', '-t', 'null', '-g', 'vga'], cwd=folder, stdin=subprocess.PIPE, stdout=self.log, stderr=self.log)

    def send(self, text):
        self.process.stdin.write((text+'\n').encode())
        self.process.stdin.flush()

    def capture(self, address, size):
        self.sequence += 1
        path = self.folder/f'capture{self.sequence}.bin'
        self.send(f'c 200000\nsave "{path.name}" bin {address} {size:x}')
        deadline = time.monotonic()+15
        while not path.exists() or path.stat().st_size != size:
            assert self.process.poll() is None, 'PCE exited before capture'
            assert time.monotonic() < deadline, 'PCE capture timeout (host/harness)'
            time.sleep(.02)
        return path.read_bytes()

    def screen(self):
        data = self.capture('b800:0', 4000)
        text = '\n'.join(data[i:i+160:2].decode('cp437') for i in range(0,4000,160))
        (self.folder/f'screen{self.sequence}.txt').write_text(text)
        return text

    def wait(self, token, prompt=False):
        deadline = time.monotonic()+35
        last = ''
        while time.monotonic() < deadline:
            last = self.screen()
            if token in last and (not prompt or any(line.strip() == 'A>' for line in last.splitlines())):
                return last
            if 'PROBE FAILED' in last:
                raise AssertionError('guest probe failed: '+last)
        raise AssertionError(f'guest completion timeout: {token}\n{last}')

    def command(self, command):
        for c in command:
            key = '+Shift Semicolon -Shift' if c == ':' else 'Space' if c == ' ' else c
            self.send('key '+key+'\nc 10000')
        self.send('key Return')

    def close(self):
        if self.process.poll() is None:
            self.send('quit')
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.log.close()


CASES = {
    'dirty-reset': (1, 320), 'dirty-reset-a': (1, 320), 'dirty-ctrlc-a': (2, 320), 'dirty-drive-reset': (6, 320),
    'dirty-ctrlc': (2, 320), 'dirty-warmboot': (8, 320),
    'no-reset-protect': (7, 320), 'other-drive-flush': (9, 320), 'clean-same': (0, 320),
    'clean-different': (0, 720), 'no-reset': (3, 320),
    'removed-retry': (4, 320), 'protected-retry': (5, 320),
}


def disk_case(variant, case, kernel_path=None):
    parent = ROOT/'local/recovery-tests'
    parent.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix=variant+'-'+case+'-', dir=parent))
    mode, kib = CASES[case]
    print(f'RUN {variant}/{case}: {folder}', flush=True)
    (folder/'diskdefs').write_bytes((ROOT/'diskdefs').read_bytes())
    kernel = (kernel_path or ROOT/(variant+'.sys')).read_bytes()
    (folder/'kernel.sys').write_bytes(kernel)
    drive = 0 if case.endswith('-a') else 1
    cmdfile(folder, ROOT/'tools/recprobe.asm', 'probe', f'-DMODE={mode}', f'-DTARGET={drive+1}')
    media(folder, 'boot', 320, [(folder/'kernel.sys', 'CPM.SYS'), (folder/'probe.cmd', 'PROBE.CMD')])
    (folder/'old.dat').write_bytes(b'O'*128)
    (folder/'new.dat').write_bytes(b'N'*128)
    # The guard also detects writes outside the probe's intended file.
    (folder/'guard.dat').write_bytes(b'G'*8192)
    (folder/'newguard.dat').write_bytes(b'H'*8192)
    media(folder, 'old', 320, [(folder/'old.dat', 'IDENT.DAT'), (folder/'guard.dat', 'GUARD.DAT')])
    if drive == 0:
        media(folder, 'boot', 320, [(folder/'kernel.sys', 'CPM.SYS'), (folder/'probe.cmd', 'PROBE.CMD'), (folder/'old.dat', 'IDENT.DAT'), (folder/'guard.dat', 'GUARD.DAT')])
    replacement_files = [(folder/'new.dat', 'IDENT.DAT'), (folder/'newguard.dat', 'GUARD.DAT')]
    if mode == 7:
        replacement_files.append((folder/'new.dat', 'CHANGED.TXT'))
    replacement = media(folder, 'new', kib, replacement_files)
    before = replacement.read_bytes()
    result = {'variant': variant, 'case': case, 'kernel_sha256': hashlib.sha256(kernel).hexdigest()}
    g = Guest(folder, 'v20' if variant == 'cpmexp' else '8088')
    try:
        g.wait('A>', prompt=True)
        g.command('probe')
        g.wait('SWAP READY')
        names = symbols(ROOT/('pcbioexp.sym' if variant == 'cpmexp' else 'pcbios.sym'))
        vector = g.capture('0:380', 4)
        segment = int.from_bytes(vector[2:4], 'little')
        result['kernel_segment'] = segment
        state = g.capture(f'{segment:x}:0', 0x6000)
        result['dirty_before_swap'] = state[names['DSKDIRTY']]
        result['cached_drive'] = state[names['DSKLAST']]
        assert bool(result['dirty_before_swap']) == (mode in (1, 2, 6, 8, 9)), result
        if mode != 9:
            g.send(f'm disk.id {drive}\nm disk.eject {drive}')
        if mode not in (4, 9):
            g.send('m disk.insert new.img')
        if mode == 5:
            g.send('m disk.ro 1')
        if mode == 2:
            g.send('key +Ctrl c -Ctrl')
            result['screen'] = g.wait('A>', prompt=True)
        else:
            g.send('key Return')
            if mode in (4, 5):
                g.wait('Retry, Ignore, Accept?')
                if mode == 4:
                    g.send('m disk.insert new.img')
                else:
                    g.send('m disk.rw 1')
                g.send('key r')
            if mode == 7:
                g.wait('R/O')
                g.send('key Return')
                result['screen'] = g.wait('A>', prompt=True)
            elif mode == 8:
                result['screen'] = g.wait('A>', prompt=True)
            else:
                result['screen'] = g.wait('PROBE DONE', prompt=True)
                if mode in (0, 4, 5):
                    assert 'READ NEW' in result['screen'], 'reset/retry returned old media data'
        g.close()
        after = replacement.read_bytes()
        changed = [i for i in range(len(before)) if before[i] != after[i]]
        result['changed_bytes'] = len(changed)
        result['changed_sectors'] = sorted({i//512 for i in changed})
        raw = folder/'inspect.raw'
        raw.write_bytes(convert(after, True) if kib == 320 else after)
        fmt = f'cpm86-{kib}'
        result['listing'] = run(folder, 'cpmls', '-f', fmt, raw.name).stdout.decode()
        fsck = run(folder, 'fsck.cpm', '-n', '-f', fmt, raw.name, check=False)
        result['fsck_status'] = fsck.returncode
        result['fsck'] = (fsck.stdout+fsck.stderr).decode()
        for name, expected in [('IDENT.DAT', b'N'*128), ('GUARD.DAT', b'H'*8192)]:
            run(folder, 'cpmcp', '-T', 'raw', '-f', fmt, raw.name, '0:'+name, name)
            assert (folder/name).read_bytes() == expected, name+' changed'
        if mode in (0, 5):
            run(folder, 'cpmcp', '-T', 'raw', '-f', fmt, raw.name, '0:OUTPUT.DAT', 'OUTPUT.DAT')
            assert (folder/'OUTPUT.DAT').read_bytes() == b'Y'*128, 'written file differs'
        else:
            assert not changed, 'replacement modified without an authorized file write'
        assert fsck.returncode == 0, result['fsck']
        if mode == 9:
            # Relogging A: must preserve and flush pending B: file data.
            raw.write_bytes(convert((folder/'old.img').read_bytes(), True))
            for name, expected in [('OUTPUT.DAT', b'X'*128), ('GUARD.DAT', b'G'*8192), ('IDENT.DAT', b'O'*128)]:
                run(folder, 'cpmcp', '-T', 'raw', '-f', 'cpm86-320', raw.name, '0:'+name, 'old-'+name)
                assert (folder/('old-'+name)).read_bytes() == expected, 'other-drive '+name
            check = run(folder, 'fsck.cpm', '-n', '-f', 'cpm86-320', raw.name, check=False)
            result['other_drive_fsck_status'] = check.returncode
            assert check.returncode == 0, check.stdout.decode()

        result['status'] = 'PASS'
    except Exception as exc:
        result['status'] = 'FAIL'
        result['error'] = str(exc)
    finally:
        g.close()
        (folder/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    if result['status'] == 'PASS':
        for pattern in ('*.img', '*.raw'):
            for p in folder.glob(pattern):
                p.unlink()
    print(result['status'], variant, case, result.get('error', ''), flush=True)
    return result


def recovery(variant):
    """Repeated native termination; observe real BDOS state before next command."""
    parent = ROOT/'local/recovery-tests'
    parent.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix=variant+'-recovery-', dir=parent))
    (folder/'diskdefs').write_bytes((ROOT/'diskdefs').read_bytes())
    kernel = (ROOT/(variant+'.sys')).read_bytes()
    (folder/'kernel.sys').write_bytes(kernel)
    (folder/'done.asm').write_text("bits 16\ncpu 8086\norg 0\ntimes 100h db 0\npush cs\npop ds\nmov dx,msg\nmov cl,9\nint 224\nxor cx,cx\nxor dx,dx\nint 224\nmsg db 'SUBMIT RECOVERY DONE',13,10,'$'\n")
    cmdfile(folder, folder/'done.asm', 'done')
    files = [(folder/'done.cmd', 'DONE.CMD'), (folder/'kernel.sys', 'CPM.SYS'),
             (ROOT/'commands/submit/submit.cmd', 'SUBMIT.CMD')]
    for mode in range(4):
        cmdfile(folder, ROOT/'tools/recstate.asm', f'rec{mode}', f'-DMODE={mode}')
        files.append((folder/f'rec{mode}.cmd', f'REC{mode}.CMD'))
    # Follow-up file I/O must work after every termination, independently of
    # snapshots. TYPE reads this known file using the restored CCP DMA.
    (folder/'check.txt').write_bytes(b'RECOVERY FILE PASS\r\n\x1a')
    files.append((folder/'check.txt', 'CHECK.TXT'))
    (folder/'batch.sub').write_bytes(b'REC1\r\nTYPE CHECK.TXT\r\nREC0\r\nTYPE CHECK.TXT\r\nDONE\r\n\x1a')
    files.append((folder/'batch.sub', 'BATCH.SUB'))
    if variant == 'cpmexp':
        for abort in (False, True):
            code = bytearray()
            fixups = []
            def service(number, label):
                code.extend([0x11, 0, 0, 0x0e, number, 0xcd, 5, 0])
                fixups.append((len(code)-7, label))
            service(9, 'clear')
            service(9, 'ready')
            # Move DMA away from the default before returning or aborting.
            code.extend([0x11, 0x00, 0x04, 0x0e, 26, 0xcd, 5, 0])
            if abort:
                service(10, 'line')
            service(9, 'done')
            code.append(0xc9)
            labels = {}
            for label, data in [('clear', b'\r\n'*24+b'$'),
                                ('ready', b'COM REC READY\r\n$'),
                                ('done', b'COM REC DONE\r\n$'),
                                ('line', bytes([20,0])+bytes(22))]:
                labels[label] = 0x100+len(code)
                code.extend(data)
            for at, label in fixups:
                code[at:at+2] = labels[label].to_bytes(2, 'little')
            name = 'comabort' if abort else 'comret'
            (folder/(name+'.com')).write_bytes(code)
            files.append((folder/(name+'.com'), name.upper()+'.COM'))
    media(folder, 'boot', 320, files)
    media(folder, 'old', 320, [])
    names = symbols(ROOT/('bdosexp.sym' if variant == 'cpmexp' else 'bdos.sym'))
    ccp = symbols(ROOT/('ccpexp.sym' if variant == 'cpmexp' else 'ccp.sym'))
    bios = symbols(ROOT/('pcbioexp.sym' if variant == 'cpmexp' else 'pcbios.sym'))
    results = []
    g = Guest(folder, 'v20' if variant == 'cpmexp' else '8088')
    def snapshot():
        vector = g.capture('0:380', 4)
        segment = int.from_bytes(vector[2:], 'little')
        memory = g.capture(f'{segment:x}:0', 0x6000)
        def value(n, size=1):
            return int.from_bytes(memory[names[n]:names[n]+size], 'little')
        result = {n: value(n, 2 if n in ('DMASEG','DMAADD','INSTSG') else 1)
                  for n in ('CNUMCB','CNTREG','SIZREG','DMASEG','DMAADD','USRCOD','CURDSK','BFCONC','INSTSG')}
        result['regions'] = memory[names['TBLREG']:names['TBLREG']+value('SIZREG')*4].hex()
        result['vectors'] = g.capture('0:200', 12).hex()
        result['kernel_segment'] = segment
        if variant == 'cpmexp':
            result.update({n: memory[bios[n]] for n in ('BANK816','KEEP816','VEC816')})
        return result
    try:
        g.wait('A>', prompt=True)
        baseline = snapshot()
        for cycle in range(3):
            for mode in range(4):
                record = {'cycle': cycle+1, 'mode': mode}
                g.command(f'rec{mode}')
                if mode == 2:
                    g.wait('REC READY')
                    g.send('key +Ctrl c -Ctrl')
                elif mode == 3:
                    g.wait('Type any key to continue.')
                    g.send('key Return')
                else:
                    g.wait('REC DONE', prompt=True)
                g.wait('A>', prompt=True)
                state = snapshot()
                record['state'] = state
                for field in ('CNUMCB','CNTREG','SIZREG','regions','vectors','USRCOD','CURDSK','BFCONC','INSTSG'):
                    assert state[field] == baseline[field], (field, baseline[field], state[field])
                assert state['DMASEG'] == state['kernel_segment'], state
                assert state['DMAADD'] == ccp['RWBUFF'], state
                if variant == 'cpmexp':
                    assert all(state[n] == 0 for n in ('BANK816','KEEP816','VEC816')), state
                g.command('type check.txt')
                g.wait('RECOVERY FILE PASS', prompt=True)
                record['status'] = 'PASS'
                results.append(record)
                print(f'PASS {variant} recovery cycle={cycle+1} mode={mode}', flush=True)
        # The final TYPE must be from the submitted sequence, not old output:
        # REC0 clears the screen before the final TYPE.
        g.command('submit batch')
        submitted = g.wait('SUBMIT RECOVERY DONE', prompt=True)
        assert 'RECOVERY FILE PASS' in submitted, submitted
        results.append({'case': 'SUBMIT', 'status': 'PASS'})
        if variant == 'cpmexp':
            retained = None
            for cycle in range(3):
                for command in ('comret', 'comret', 'comabort'):
                    g.command(command)
                    g.wait('COM REC READY')
                    if command == 'comabort':
                        g.send('key +Ctrl c -Ctrl')
                    else:
                        g.wait('COM REC DONE', prompt=True)
                    g.wait('A>', prompt=True)
                    state = snapshot()
                    for field in ('vectors', 'USRCOD', 'CURDSK', 'BFCONC', 'INSTSG'):
                        assert state[field] == baseline[field], (field, baseline[field], state[field])
                    assert state['DMASEG'] == state['kernel_segment'], state
                    assert state['DMAADD'] == ccp['RWBUFF'], state
                    assert state['VEC816'] == 0, state
                    if command == 'comret':
                        assert state['BANK816'] == state['KEEP816'] == 1, state
                        if retained is None:
                            retained = state
                        for field in ('regions', 'CNUMCB', 'CNTREG', 'SIZREG'):
                            assert state[field] == retained[field], (field, retained[field], state[field])
                    else:
                        assert state['BANK816'] == state['KEEP816'] == 0, state
                        for field in ('regions', 'CNUMCB', 'CNTREG', 'SIZREG'):
                            assert state[field] == baseline[field], (field, baseline[field], state[field])
                    g.command('type check.txt')
                    g.wait('RECOVERY FILE PASS', prompt=True)
                    results.append({'case': command, 'cycle': cycle+1, 'status': 'PASS', 'state': state})
                    print(f'PASS {variant} {command} cycle={cycle+1}', flush=True)

    except Exception as exc:
        results.append({'status': 'FAIL', 'error': str(exc)})
        print('FAIL', variant, 'recovery', str(exc), flush=True)
    finally:
        g.close()
        report = {'kernel_sha256': hashlib.sha256(kernel).hexdigest(), 'results': results}
        (folder/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    passed = sum(x['status'] == 'PASS' for x in results)
    print(f'{variant} recovery: {passed}/{len(results)} passed; {folder}', flush=True)
    if passed == len(results):
        for image in folder.glob('*.img'):
            image.unlink()
    return passed == len(results)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant', choices=['cpm', 'cpmexp', 'cpmorg'], default='cpm')
    p.add_argument('--case', choices=list(CASES)+['all'], default='all')
    p.add_argument('--skip', action='append', default=[])
    p.add_argument('--recovery', action='store_true')
    p.add_argument('--kernel', type=Path, help='Snapshot kernel for before/after disk tests')
    args = p.parse_args()
    if args.recovery:
        sys.exit(not recovery(args.variant))
    results = [disk_case(args.variant, case, args.kernel) for case in (CASES if args.case == 'all' else [args.case]) if case not in args.skip]
    passed = sum(r['status'] == 'PASS' for r in results)
    print(f'{passed}/{len(results)} passed; {len(results)-passed} failed')
    sys.exit(passed != len(results))
