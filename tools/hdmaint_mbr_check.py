#!/usr/bin/env python3
"""Guest F4/delete and DOS/CP/M cold-boot regression on disposable images.

Requires a local raw IBM DOS 3.3 system disk (--dos-source). Only reads it;
all formatting, installation, menu operations and boots use temporary copies.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import select
import shutil
import struct
import subprocess
import tempfile
import time

P = argparse.ArgumentParser(description=__doc__)
P.add_argument('--emulator', choices=['pce', 'qemu'], required=True)
P.add_argument('--personality', choices=['pc', 'experimental'], default='pc')
P.add_argument('--dos-source', type=Path, required=True)
P.add_argument('--refresh-only', action='store_true', help='Test replacement and creation/verification pause-resume screens')
P.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
A = P.parse_args()
R = A.root.resolve()
SOURCE = A.dos_source.resolve()
WORK = R/'local/hdmaint-tests'
WORK.mkdir(parents=True, exist_ok=True)
F = Path(tempfile.mkdtemp(prefix='hdmaint-mbr-', dir=WORK))
print('Diagnostics:', F, flush=True)
CYL, HEADS, SPT = 615, 4, 17
SPC = HEADS*SPT
results = []


def run(*args, cwd=None):
    result = subprocess.run(args, cwd=cwd or F, capture_output=True)
    if result.returncode:
        raise RuntimeError(f'{args}: {result.stderr.decode(errors="replace")}')
    return result


def sha(data):
    return hashlib.sha256(data).hexdigest()


def passed(name):
    results.append(name)
    (F/'results.json').write_text(json.dumps(results, indent=2)+'\n')
    print('PASS:', name, flush=True)


def entries(mbr):
    return [mbr[i:i+16] for i in range(446, 510, 16)]


def assert_mbr(before, after, preserve, target=None, delete=False):
    old = entries(before)
    # The editor sorts occupied entries by LBA before making any changes.
    order = sorted(range(4), key=lambda i: (not old[i][4], struct.unpack_from('<I',old[i],8)[0]))
    updated = []
    for i in order:
        e = bytearray(old[i])
        if target is not None and e[4]:
            e[0] = 0x80 if e[4] == target else 0
        if delete and e[4] == 0xdb:
            e[:] = bytes(16)
        updated.append(bytes(e))
    output = [bytes(16)]*4
    for index, e in enumerate(updated):
        output[order[index] if preserve else index] = e
    expected = (before[:446] if preserve else default_boot)+b''.join(output)+b'\x55\xaa'
    assert after == expected, 'Unexpected MBR byte change'


class Guest:
    """Use the emulator monitor for keys/screens; never attach user disks."""
    def __init__(self, name, floppy=True):
        self.folder = F/name
        self.folder.mkdir()
        self.sequence = 0
        self.last = ''
        self.video = b''
        self.log = (self.folder/'emulator.log').open('wb')
        if A.emulator == 'qemu':
            args = ['qemu-system-i386','-machine','pc','-accel','tcg','-m','16',
                    '-display','none','-serial','none','-monitor','none','-qmp','stdio',
                    '-net','none','-boot','a' if floppy else 'c','-no-fd-bootchk','-no-reboot',
                    '-drive','file=hard.img,format=raw,if=none,id=hd0',
                    '-device',f'ide-hd,drive=hd0,cyls={CYL},heads={HEADS},secs={SPT},bios-chs-trans=none']
            if floppy:
                args += ['-drive','file=boot.img,format=raw,if=floppy,index=0']
            self.p = subprocess.Popen(args,cwd=F,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                      stderr=self.log,bufsize=0)
            self.receive()
            self.command('qmp_capabilities')
        else:
            cfg = (F/'pce.cfg').read_text()
            if not floppy:
                cfg = re.sub(r'boot\s*=\s*0\b','boot = 128',cfg,count=1)
                cfg = re.sub(r'disk\s*\{\s*drive=0\s+.*?\}', '',cfg,flags=re.S)
            config = self.folder/'test.cfg'
            config.write_text(cfg)
            args = ['pce-ibmpc','-c',str(config),'-t','null','-g','vga']
            self.p = subprocess.Popen(args,cwd=F,stdin=subprocess.PIPE,stdout=self.log,stderr=self.log)
        (self.folder/'command.json').write_text(json.dumps(args,indent=2)+'\n')

    def receive(self):
        assert select.select([self.p.stdout],[],[],10)[0], 'QMP timeout'
        return json.loads(self.p.stdout.readline())

    def command(self, name, arguments=None):
        self.p.stdin.write((json.dumps({'execute':name,'arguments':arguments or {}})+'\n').encode())
        while True:
            reply = self.receive()
            assert 'error' not in reply, reply
            if 'return' in reply:
                return reply['return']

    def hmp(self, text):
        return self.command('human-monitor-command',{'command-line':text})

    def send(self, text):
        self.p.stdin.write((text+'\n').encode())
        self.p.stdin.flush()

    def key(self, key):
        if A.emulator == 'qemu':
            key = {'Return':'ret',' ': 'spc','.':'dot',':':'shift-semicolon','=':'equal'}.get(key,key.lower())
            assert not self.hmp('sendkey '+key+' 50')
            time.sleep(.12)
        else:
            key = {' ':'Space','.':'Period',':':'+Shift Semicolon -Shift','=':'Equal'}.get(key,key)
            self.send('key '+key+'\nc '+('2000' if getattr(self, 'fast_poll', False) else '200000'))

    def type(self, text):
        for ch in text:
            self.key(ch)
        self.key('Return')

    def screen(self):
        self.sequence += 1
        path = self.folder/f'screen-{self.sequence:04}.bin'
        if A.emulator == 'qemu':
            self.hmp(f'pmemsave 0xb8000 4000 "{path}"')
        else:
            cycles = 20000 if getattr(self, 'fast_poll', False) else 2000000
            self.send(f'c {cycles}\nsave "{path}" bin b800:0000 fa0')
            until = time.monotonic()+30
            while not path.exists() or path.stat().st_size != 4000:
                assert self.p.poll() is None, 'PCE exited'
                assert time.monotonic() < until, 'PCE monitor timeout'
                time.sleep(.05)
        self.video = path.read_bytes()
        self.last = '\n'.join(bytes(self.video[i:i+160:2]).decode('cp437') for i in range(0,4000,160))
        path.with_suffix('.txt').write_text(self.last)
        return self.last

    def wait(self, expected, name, timeout=90):
        predicate = expected if callable(expected) else lambda text: expected in text
        until = time.monotonic()+timeout
        while time.monotonic() < until:
            if predicate(self.screen()):
                # Let the menu finish its input flush before sending the next key.
                if A.emulator == 'qemu': time.sleep(.2)
                (self.folder/(name+'.txt')).write_text(self.last)
                return
            time.sleep(.15)
        raise AssertionError(f'{name}: {self.last}')

    def policy(self, preserve):
        def matches(text):
            if 'MBR boot code: replace/preserve' not in text:
                return False
            chars = self.video[:4000:2]
            at = chars.index(b'replace/preserve')
            normal = self.video[2*(at-2)+1]
            r, p = self.video[2*at+1], self.video[2*(at+8)+1]
            return r != p and (r == normal) == preserve and (p == normal) != preserve
        self.wait(matches, 'policy-preserve' if preserve else 'policy-replace')

    def start_hdmaint(self, preserve):
        self.wait('A>', 'floppy-boot')
        self.type('hdmaint')
        self.wait('Exit from this program', 'main')
        self.key('F1')
        self.policy(False)
        if preserve:
            self.key('F8')
            self.policy(True)

    def close(self):
        if self.p.poll() is None:
            if A.emulator == 'qemu':
                self.command('quit')
            else:
                self.send('q')
        try:
            self.p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.p.terminate()
            try:
                self.p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.p.kill()
                self.p.wait(timeout=5)
        self.log.close()


def cold_boot(name, dos):
    g = Guest(name, floppy=False)
    try:
        if dos:
            g.wait('DOS_HDD_BOOT_OK', 'dos-autoexec')
            g.wait(lambda t: bool(re.search(r'C:\\[^\n]*>',t)), 'dos-prompt')
            g.type('ver')
            g.wait('3.30', 'dos-version')
            g.type('type doskeep.txt')
            g.wait('DOS_PARTITION_DATA_OK', 'dos-file')
        else:
            g.wait(lambda t: bool(re.search(r'\b[B-F]>',t)), 'cpm-hdd-prompt')
            g.type('type bootchk.txt')
            g.wait('CPM_HDD_BOOT_OK', 'cpm-file')
    finally:
        g.close()
    passed(name+' (no floppy attached)')


def menu_write(name, preserve, target=None, delete=False, cancel=False):
    before = hard.read_bytes()
    g = Guest(name)
    try:
        g.start_hdmaint(preserve)
        if delete:
            g.key('F2')
            g.wait('Do not delete existing CP/M volume', 'delete-confirmation')
            g.key('F9' if cancel else 'F7')
            if cancel:
                g.wait('Exit from this program', 'cancelled')
            else:
                g.wait('Please insert a system diskette', 'deleted')
        else:
            g.key('F4')
            g.wait('before it can boot.', 'boot-menu')
            if target is not None:
                def active(text):
                    for line in text.splitlines()[:9]:
                        if '(bootable)' in line:
                            return 4 if 'non-CP/M' in line else 0xdb
                    return None
                for _ in range(5):
                    if active(g.last) == target:
                        break
                    previous = active(g.last)
                    g.key('F2')
                    g.wait(lambda t: active(t) != previous, 'cycle-active')
                assert active(g.last) == target, g.last
            g.key('F10')
            g.wait('Exit from this program', 'written-main')
        if not delete or cancel:
            g.key('F9')
            g.wait('A>', 'exit')
    finally:
        g.close()
    after = hard.read_bytes()
    assert after[512:] == before[512:], 'Menu action wrote outside the MBR'
    if cancel:
        assert after == before, 'Cancelled deletion changed the disk'
    else:
        assert_mbr(before[:512],after[:512],preserve,target,delete)
    passed(name+'; exact MBR and whole-disk comparison')



def refresh_suite():
    before = hard.read_bytes()
    g = Guest('refresh-replace-create')
    try:
        g.start_hdmaint(True)
        summary = g.last.splitlines()[4:8]
        g.key('F6')
        g.wait('Do not delete existing CP/M volume', 'replacement-warning')
        assert g.last.splitlines()[8][1:79] == ' '*78, 'Old F2 border remains'
        assert g.last.splitlines()[4:8] == summary, 'Partition summary was erased'
        g.key('F9')
        g.wait('Exit from this program', 'replacement-cancelled')
        assert hard.read_bytes() == before, 'Cancelling replacement wrote the disk'
        g.key('F1');g.policy(False)
        g.key('F8');g.policy(True)
        g.key('F6');g.wait('Do not delete existing CP/M volume', 'replacement-warning-again')
        g.key('F7');g.wait('Enter starting cylinder', 'replacement-start')
        g.key('F10');g.wait('Enter partition size', 'replacement-size')
        g.key('F10');g.wait('Accept CP/M options shown', 'replacement-options')
        g.key('F10');g.wait('Testing cylinder', 'replacement-progress',240)
        g.key('F9');g.wait('Continue creating CP/M volume', 'creation-paused')
        g.key('F7')
        g.wait(lambda t: 'Continue creating CP/M volume' not in t and
               ('Testing cylinder' in t or 'Creation of CP/M volume complete' in t), 'creation-resumed')
        assert all(line[1:79] == ' '*78 for line in g.last.splitlines()[15:20]), 'Creation-resume remnant'
        g.wait('Creation of CP/M volume complete', 'replacement-complete',240)
        g.wait('To continue', 'replacement-controls')
        g.key('F9');g.wait('Please insert a system diskette', 'replacement-reboot')
    finally:
        g.close()
    after = hard.read_bytes()
    entry = next(e for e in entries(before[:512]) if e[4] == 0xdb)
    lba, count = struct.unpack_from('<II',entry,8)
    assert after[:lba*512] == before[:lba*512], 'Replacement changed MBR or DOS region'
    assert after[(lba+count)*512:] == before[(lba+count)*512:], 'Replacement escaped its partition'
    passed('refresh: existing-partition F6, cancel, replace, creation pause/resume; clean screens and protected DOS')
    before = after
    g = Guest('refresh-verify')
    try:
        g.wait('A>', 'floppy-boot')
        g.type('hdmaint');g.wait('Exit from this program', 'main')
        g.fast_poll = True
        g.key('F3');g.wait('Scanning cylinder', 'verify-progress')
        g.key('F10');g.wait('Continue verifying CP/M volume', 'verify-paused')
        g.key('F8')
        g.wait(lambda t: 'Continue verifying CP/M volume' not in t and
               (('Scanning cylinder' in t and all(line[1:79] == ' '*78 for line in t.splitlines()[16:20]))
                or 'Verify complete' in t), 'verify-resumed')
        # Completion has its own F8 box; only require blank rows while scanning.
        if 'Scanning cylinder' in g.last:
            assert all(line[1:79] == ' '*78 for line in g.last.splitlines()[16:20]), 'Verify-resume remnant'
        else:
            assert g.last.splitlines()[16][1:79] == ' '*78, 'Verify warning remains'
        g.fast_poll = False
        g.wait('Verify complete', 'verify-complete',240)
        g.wait('Return to main menu', 'verify-controls')
        g.key('F10');g.wait('Exit from this program', 'verify-main')
        g.key('F9');g.wait('A>', 'exit')
    finally:
        g.close()
    assert hard.read_bytes() == before, 'Read-only verify modified the disk'
    passed('refresh: verification pause/resume; clean screen and entire disk unchanged')

# Use the same agreed geometry, boot floppy and disk configuration as creation tests.
prep = run('python3', str(R/'tools/hdmaint_live_check.py'),'--emulator',A.emulator,
           '--personality',A.personality,'--layout','dos-cpm','--prepare-only')
prepared = Path(re.search(rb'Fixture: ([^\n]+)',prep.stdout)[1].decode())
for name in ('boot.img','hdmaint.cmd','cpm.sys','manifest.json'):
    shutil.copyfile(prepared/name,F/name)
# Always prepare a PCE config, including for QEMU fixtures (cold-boot portability).
if not (prepared/'pce.cfg').exists():
    prep = run('python3', str(R/'tools/hdmaint_live_check.py'),'--emulator','pce',
               '--personality',A.personality,'--layout','dos-cpm','--prepare-only')
    pce_prepared = Path(re.search(rb'Fixture: ([^\n]+)',prep.stdout)[1].decode())
else:
    pce_prepared = prepared
shutil.copyfile(pce_prepared/'pce.cfg',F/'pce.cfg')
raw = (F/'hdmaint.cmd').read_bytes()
code_size = int.from_bytes(raw[1:3],'little')*16
payload = raw[128+code_size:]
default_boot = payload[0xefe:0xefe+446]
source_hash = sha(SOURCE.read_bytes())
with SOURCE.open('rb') as f:
    source_mbr = f.read(512)
    candidates = [e for e in entries(source_mbr) if e[4] == 4]
    assert len(candidates) == 1, 'Expected one FAT16 DOS partition in source'
    source_lba = struct.unpack_from('<I',candidates[0],8)[0]
    f.seek(source_lba*512)
    dos_boot = f.read(512)
assert dos_boot[3:11] == b'IBM  3.3', 'This installer expects an IBM DOS 3.3 boot sector'
# DOS 3.3 starts executable code at offset 54; retain it, update only its BPB.
dos = F/'dos.img'
dos.write_bytes(bytes(8*1024*1024))
run('mformat','-i',str(dos),'-T','16384','-h','4','-s','17','-H','17','-c','1','::')
boot = bytearray(dos_boot)
boot[11:30] = dos.read_bytes()[11:30]
with dos.open('r+b') as f:
    f.write(boot)
for name in ('IBMBIO.COM','IBMDOS.COM','COMMAND.COM'):
    run('mcopy','-i',f'{SOURCE}@@{source_lba*512}','::'+name,str(F/name))
    run('mcopy','-i',str(dos),str(F/name),'::'+name)
run('mattrib','-i',str(dos),'+s','+h','+r','::IBMBIO.COM','::IBMDOS.COM')
for name, contents in [('AUTOEXEC.BAT',b'@echo off\r\necho DOS_HDD_BOOT_OK\r\nprompt $p$g\r\n'),
                       ('DOSKEEP.TXT',b'DOS_PARTITION_DATA_OK\r\n')]:
    (F/name).write_bytes(contents)
    run('mcopy','-i',str(dos),str(F/name),'::'+name)
# System files must occupy the first two directory entries for this DOS loader.
bpb = dos.read_bytes()[:512]
root_lba = struct.unpack_from('<H',bpb,14)[0]+bpb[16]*struct.unpack_from('<H',bpb,22)[0]
root = dos.read_bytes()[root_lba*512:root_lba*512+64]
assert root[:11] == b'IBMBIO  COM' and root[32:43] == b'IBMDOS  COM'
hard = F/'hard.img'
shutil.copyfile(prepared/'hard.img', hard)
mbr = bytearray(source_mbr)
mbr[446:510] = bytes(64)
# Put DOS in slot 4 to catch accidental sorting under preserve.
fixture_mbr = (prepared/'baseline-mbr.bin').read_bytes()
mbr[494:510] = fixture_mbr[446:462]
with hard.open('r+b') as f:
    f.write(mbr)
    f.seek(SPT*512)
    f.write(dos.read_bytes())
(F/'dos-source.json').write_text(json.dumps(dict(path=str(SOURCE),sha256=source_hash,
    mbr_sha256=sha(source_mbr),vbr_sha256=sha(dos_boot)),indent=2)+'\n')
shutil.rmtree(prepared)
if pce_prepared != prepared:
    shutil.rmtree(pce_prepared)
cold_boot('00-original-dos', True)

# Real HDMAINT creates CP/M; retain the known-bootable DOS bootstrap and slot.
before = hard.read_bytes()
g = Guest('01-create-preserve')
try:
    g.start_hdmaint(True)
    g.key('F6');g.wait('Enter starting cylinder','start')
    g.key('F10');g.wait('Enter partition size','size')
    g.key('F10');g.wait('Accept CP/M options shown','options')
    g.key('F10');g.wait('Creation of CP/M volume complete','complete',240)
    g.wait('To continue','complete-controls')
    g.key('F9');g.wait('Please insert a system diskette','reboot')
finally:
    g.close()
after = hard.read_bytes()
assert after[:446] == before[:446] and after[494:510] == before[494:510]
cpm = next(e for e in entries(after[:512]) if e[4] == 0xdb)
lba, sectors = struct.unpack_from('<II',cpm,8)
assert lba == 242*SPC
assert sectors == ((614 if A.emulator == 'qemu' else 615)-242)*SPC
assert after[512:lba*512] == before[512:lba*512]
assert after[(lba+sectors)*512:] == before[(lba+sectors)*512:]
passed('01-create-preserve; original DOS bootstrap, slot and protected regions intact')
# Install the actual built kernel and a marker using the DPB created by HDMAINT.
label = after[lba*512+1536:lba*512+2048]
assert sum(struct.unpack('<256H',label))&65535 == 0
block_size = 128 << label[43]
blocks = struct.unpack_from('<H',label,46)[0]+1
maxdir = struct.unpack_from('<H',label,48)[0]+1
base = (242+1)*SPC*512
filesystem = F/'cpm.img'
filesystem.write_bytes(after[base:base+blocks*block_size])
(F/'diskdefs').write_text(f'''diskdef hdtest
 seclen 512
 tracks {blocks*block_size//512}
 sectrk 1
 blocksize {block_size}
 maxdir {maxdir}
 skew 1
 boottrk 0
 os 2.2
end
''')
(F/'BOOTCHK.TXT').write_bytes(b'CPM_HDD_BOOT_OK\r\n\x1a')
# TYPE is built into the CP/M-86 CCP.
run('cpmcp','-T','raw','-f','hdtest',str(filesystem),'cpm.sys','BOOTCHK.TXT','0:')
run('cpmcp','-T','raw','-f','hdtest',str(filesystem),'0:CPM.SYS','kernel-readback.sys')
assert (F/'kernel-readback.sys').read_bytes() == (F/'cpm.sys').read_bytes()
with hard.open('r+b') as f:
    f.seek(base);f.write(filesystem.read_bytes())
shutil.copyfile(hard,F/'created-both.img')

if A.refresh_only:
    refresh_suite()
else:
    for preserve in (True, False):
        mode = 'preserve' if preserve else 'replace'
        shutil.copyfile(F/'created-both.img',hard)
        menu_write(mode+'-02-renew-no-cycle',preserve)
        cold_boot(mode+'-03-dos-after-renewal',True)
        menu_write(mode+'-04-select-cpm',preserve,target=0xdb)
        cold_boot(mode+'-05-cpm',False)
        menu_write(mode+'-06-select-dos',preserve,target=4)
        cold_boot(mode+'-07-dos-after-switch',True)
        menu_write(mode+'-08-cancel-delete',preserve,delete=True,cancel=True)
        menu_write(mode+'-09-delete',preserve,delete=True)
        cold_boot(mode+'-10-dos-after-delete',True)
        shutil.copyfile(hard,F/(mode+'-final.img'))
assert sha(SOURCE.read_bytes()) == source_hash, 'DOS source image changed'
if A.refresh_only:
    passed(f'{A.emulator} {A.personality}: refresh regression')
else:
    passed(f'{A.emulator} {A.personality}: both MBR policies, F4 renewal/switching, deletion, DOS and CP/M hard-disk boots')

# Keep text evidence and hashes, remove all disposable images/system binaries.
for path in F.iterdir():
    if path.is_file() and path.suffix.lower() in ('.img','.sys','.com','.cmd'):
        path.unlink()
print('Cleaned disposable images and system binaries; text diagnostics:', F, flush=True)
