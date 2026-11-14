#!/usr/bin/env python3
"""Drive HDMAINT creation through PCE/QEMU on disposable 615/4/17 disk images.

This is an interactive-formatter test: HDMAINT, not the host, creates CP/M.
DOS primaries contain a FAT filesystem and a checked file, not a bootable OS.
Extended containers are synthetic boundary guards.
Project-local fixtures retain diagnostics; successful runs remove disk images
unless --keep-images or --prepare-only was requested.
"""
from pathlib import Path
import argparse, hashlib, json, re, select, shutil, struct, subprocess, tempfile, time

P = argparse.ArgumentParser(description=__doc__)
P.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
P.add_argument('--cmd', type=Path)
P.add_argument('--emulator', choices=['pce','qemu'], required=True)
P.add_argument('--personality', choices=['pc','experimental'], default='pc')
P.add_argument('--expect-hang', choices=['options'])
P.add_argument('--layout', choices=['mixed', 'dos-cpm', 'cpm-only'], default='mixed')
P.add_argument('--preserve-mbr', action='store_true', help='Select preservation and test original bootstrap/partition slots')
P.add_argument('--cylinders', type=int, help='CP/M length; default fills the free extent')
P.add_argument('--keep-images', action='store_true', help='Retain successful automated-run images for manual replay')
P.add_argument('--prepare-only', action='store_true', help='Create fresh images/configuration for manual testing without running the emulator')
A = P.parse_args()
R = A.root.resolve()
CMD = (A.cmd or R/'commands/hdmaint/hdmaint.cmd').resolve()
WORK = R/'local/hdmaint-tests'
WORK.mkdir(parents=True, exist_ok=True)
F = Path(tempfile.mkdtemp(prefix='hdmaint-ui-', dir=WORK))
print('Fixture:', F, flush=True)

def run(*args):
    return subprocess.run(args, cwd=F, check=True, capture_output=True)

def digest_range(path, start, end):
    h = hashlib.sha256()
    with path.open('rb') as f:
        f.seek(start)
        while start < end:
            block = f.read(min(1048576, end-start))
            assert block
            h.update(block)
            start += len(block)
    return h.hexdigest()

# Preserve exact inputs in the fixture, independent of repository rebuilds.
shutil.copyfile(CMD,F/'hdmaint.cmd')
kernel = R/('cpmexp.sys' if A.personality=='experimental' else 'cpm.sys')
shutil.copyfile(kernel,F/'cpm.sys')
shutil.copyfile(R/'diskdefs', F/'diskdefs')
run('python3',str(R/'tools/cpm86twist.py'),'untwist',str(R/'base-320.img'),'boot.logical.img')
run('cpmcp','-f','cpm86-320','boot.logical.img','cpm.sys','hdmaint.cmd','0:')
run('python3',str(R/'tools/cpm86twist.py'),'twist','boot.logical.img','boot.img')
# All disk-backed scenarios use the agreed native-XT geometry.
CYLINDERS, HEADS, SPT = 615, 4, 17
# Expected BIOS reports are test assertions, not formatter behaviour.
bios_cylinders = CYLINDERS-1 if A.emulator == 'qemu' else CYLINDERS
spc=HEADS*SPT
size=CYLINDERS*spc*512
DOS_SECTORS = 8*1024*1024//512
first = 0 if A.layout == 'cpm-only' else (SPT+DOS_SECTORS+spc-1)//spc
maximum_length = bios_cylinders-first
length = A.cylinders if A.cylinders is not None else maximum_length
if not 10 <= length <= maximum_length:
    P.error(f'--cylinders must be between 10 and {maximum_length}')
# Mixed reserves the same 8 MiB using a 4 MiB primary plus a 4 MiB
# extended container; its partial-cylinder boundary exercises LBA rounding.
foreign = [] if A.layout == 'cpm-only' else (
    [(0,4,SPT,DOS_SECTORS)] if A.layout == 'dos-cpm' else
    [(0,4,SPT,DOS_SECTORS//2),(1,5,SPT+DOS_SECTORS//2,DOS_SECTORS//2)])
# Preserve fixtures deliberately place entries out of order with empty slots.
if A.preserve_mbr:
    foreign = [((3,1)[i],kind,start,length) for i,(_,kind,start,length) in enumerate(foreign)]
hard=F/'hard.img'
with hard.open('wb') as f: f.truncate(size)
mbr=bytearray(512)
# Identifiable bootstrap: replaced by default, retained with --preserve-mbr.
mbr[:446]=bytes([0x5a])*446
for index,kind,entry_start,entry_length in foreign:
    at=446+index*16
    mbr[at]=0x80 if kind==4 else 0
    mbr[at+4]=kind
    for pos,lba in [(at+1,entry_start),(at+5,entry_start+entry_length-1)]:
        c,rem=divmod(lba,spc);h,s=divmod(rem,SPT)
        mbr[pos:pos+3]=bytes([h,s+1|((c>>8)<<6),c&255])
    struct.pack_into('<II',mbr,at+8,entry_start,entry_length)
mbr[510:]=b'\x55\xaa'
with hard.open('r+b') as f:
    f.write(mbr)
    for lba in [SPT,65*spc,first*spc-1,(first+length)*spc,size//512-1]:
        if not 0 < lba < size//512: continue
        f.seek(lba*512);f.write(bytes([0xa5])*512)
# Format the foreign primary and populate a file before taking protection hashes.
dos_text = b'HDMAINT must preserve this DOS file and the entire DOS partition.\r\n'
if foreign:
    dos_sectors = foreign[0][3]
    with (F/'dos.img').open('wb') as f: f.truncate(dos_sectors*512)
    run('mformat','-i','dos.img','-T',str(dos_sectors),'-h',str(HEADS),
        '-s',str(SPT),'-H',str(SPT),'-c','1','-v','KEEPDOS','::')
    (F/'DOSKEEP.TXT').write_bytes(dos_text)
    run('mcopy','-i','dos.img','DOSKEEP.TXT','::DOSKEEP.TXT')
    with (F/'dos.img').open('rb') as src, hard.open('r+b') as dst:
        assert src.read(512)[54:62] == b'FAT16   ', 'Unexpected DOS filesystem type'
        src.seek(0);dst.seek(SPT*512);shutil.copyfileobj(src,dst)
start=first*spc*512; end=(first+length)*spc*512
before=(digest_range(hard,512,max(512,start)),digest_range(hard,end,size))
(F/'baseline-mbr.bin').write_bytes(mbr)
(F/'manifest.json').write_text(json.dumps(dict(emulator=A.emulator,personality=A.personality,
    geometry=[CYLINDERS,HEADS,SPT],layout=A.layout,preserve_mbr=A.preserve_mbr,bios_cylinders=bios_cylinders,cylinders=[first,first+length-1],hdmaint_sha256=hashlib.sha256(CMD.read_bytes()).hexdigest(),
    kernel_sha256=hashlib.sha256(kernel.read_bytes()).hexdigest(),protected_hashes=before),indent=2)+'\n')

class Qemu:
    def __init__(self):
        args=['qemu-system-i386','-machine','pc','-accel','tcg','-m','16',
              '-display','none','-serial','none','-monitor','none','-qmp','stdio',
              '-net','none','-boot','a','-no-fd-bootchk','-no-reboot',
              '-drive','file=boot.img,format=raw,if=floppy,index=0',
              '-drive','file=hard.img,format=raw,if=none,id=hd0',
              '-device',f'ide-hd,drive=hd0,cyls={CYLINDERS},heads={HEADS},secs={SPT},bios-chs-trans=none']
        (F/'qemu-command.json').write_text(json.dumps(args,indent=2)+'\n')
        if A.prepare_only: return
        self.log=(F/'qemu.log').open('wb')
        self.p=subprocess.Popen(args,cwd=F,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,bufsize=0)
        self.receive();self.command('qmp_capabilities')
    def receive(self):
        assert select.select([self.p.stdout],[],[],10)[0], 'QMP timeout'
        return json.loads(self.p.stdout.readline())
    def command(self,name,args=None):
        self.p.stdin.write((json.dumps({'execute':name,'arguments':args or {}})+'\n').encode())
        while True:
            r=self.receive()
            assert 'error' not in r,r
            if 'return' in r:return r['return']
    def hmp(self,s):return self.command('human-monitor-command',{'command-line':s})
    def screen(self,path):
        self.hmp(f'pmemsave 0xb8000 4000 "{path}"')
        return path.read_bytes()
    def key(self,key):
        self.hmp('sendkey '+{'Return':'ret','Space':'spc'}.get(key,key.lower())+' 50')
        time.sleep(.12)
    def close(self):
        if self.p.poll() is None:self.command('quit')
        self.p.wait(timeout=10);self.log.close()

class Pce:
    def __init__(self):
        cfg=(R/'cpm86-320.cfg').read_text().replace('driver = "sdl"','driver = "null"').replace('sdl:lowpass=5000','null')
        cfg=re.sub(r'(?m)^path\s*=\s*"([^"\n]+)"',lambda m:'path = "'+str((R/m[1]).resolve())+'"',cfg)
        # The hard-disk loader uses 3000:0000h; the base floppy profile is only 128K.
        cfg=re.sub(r'(ram\s*\{.*?size\s*=\s*)\d+K',r'\g<1>640K',cfg,flags=re.S)
        cfg=re.sub(r'floppy_disk_drives\s*=\s*\d+','floppy_disk_drives = 2',cfg)
        cfg=re.sub(r'disk\s*\{.*?\}','',cfg,flags=re.S)
        cfg+='\ndisk { drive=0 type="auto" file="boot.img" }\n'
        cfg+=f'disk {{ drive=128 type="image" file="hard.img" c={CYLINDERS} h={HEADS} s={SPT} }}\n'
        (F/'pce.cfg').write_text(cfg)
        if A.prepare_only: return
        self.log=(F/'pce.log').open('wb')
        self.p=subprocess.Popen(['pce-ibmpc','-c','pce.cfg','-t','null','-g','vga'],cwd=F,stdin=subprocess.PIPE,stdout=self.log,stderr=self.log)
    def send(self,s):self.p.stdin.write((s+'\n').encode());self.p.stdin.flush()
    def screen(self,path):
        self.send(f'c 2000000\nsave "{path}" bin b800:0000 fa0')
        until=time.monotonic()+30
        while not path.exists() or path.stat().st_size!=4000:
            assert self.p.poll() is None,'PCE exited'
            assert time.monotonic()<until,'PCE monitor timeout'
            time.sleep(.05)
        return path.read_bytes()
    def key(self,key):self.send('key '+key+'\nc 200000')
    def close(self):
        if self.p.poll() is None:self.send('q')
        self.p.wait(timeout=10);self.log.close()

vm = Qemu() if A.emulator=='qemu' else Pce()
if A.prepare_only:
    print(f'Prepared {A.layout}: {CYLINDERS}/{HEADS}/{SPT}; CP/M proposal {first}..{bios_cylinders-1}', flush=True)
    raise SystemExit(0)
seq=0
last=''
def screen():
    global seq,last
    seq+=1
    p=F/f'screen-{seq:04}.bin'
    data=vm.screen(p)
    last='\n'.join(bytes(data[i:i+160:2]).decode('cp437') for i in range(0,4000,160))
    p.with_suffix('.txt').write_text(last)
    return last

def wait(text,name,seconds=60):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        if text in screen():
            if A.emulator == 'qemu': time.sleep(.2)
            (F/(name+'.txt')).write_text(last)
            print('SCREEN:',name,flush=True)
            return
        time.sleep(.15)
    raise AssertionError(f'{name}: missing {text!r}\n{last}')

def wait_policy(preserve, name):
    wait('MBR boot code: replace/preserve', name)
    video = (F/f'screen-{seq:04}.bin').read_bytes()
    chars = video[0:4000:2]
    at = chars.index(b'replace/preserve')
    replacement = video[2*at+1]
    preservation = video[2*(at+8)+1]
    # ESC r/u is the same selected-option highlighting used by CP/M options.
    assert replacement != preservation, 'MBR selection is not highlighted'
    normal = video[2*(at-2)+1]
    assert (replacement == normal) == preserve, 'Wrong MBR option highlighted'
    assert (preservation == normal) != preserve, 'Wrong MBR option highlighted'
    row = chars[18*80:19*80]
    assert b'F8' in row and b'MBR boot code:' in row, 'F8 caption misaligned'

def key(name):vm.key(name)

success=False
try:
    wait('A>','boot')
    for ch in 'hdmaint':key(ch)
    key('Return')
    wait('Exit from this program','main')
    key('F1');wait('Change or create CP/M partition','partition')
    if not A.expect_hang:
        wait_policy(False,'default-policy')
        # Exercise both toggle directions; leave the requested policy selected.
        key('F8');wait_policy(True,'preserve-policy')
        key('F8');wait_policy(False,'replace-policy')
        # Leaving/re-entering the disk menu must also restore the default.
        key('F8');wait_policy(True,'preserve-before-exit')
        key('F10');wait('Exit from this program','main-again')
        key('F1');wait_policy(False,'default-policy-again')
        if A.preserve_mbr:
            key('F8');wait_policy(True,'selected-preserve-policy')
    key('F6');wait('Enter starting cylinder','start')
    if not A.expect_hang:
        assert f'of {bios_cylinders:04} cylinders assigned:' in last,last
        for ch in f'{first+1:04}': key(ch)
        # Four digits alone must not submit or change the proposal.
        wait(f'Continue with starting cylinder {first:04}','unconfirmed-start')
        key('Return');wait(f'Continue with starting cylinder {first+1:04}','confirmed-start')
        for ch in f'{bios_cylinders:04}': key(ch)
        key('Return');wait('Enter starting cylinder: ____','rejected-start')
        assert f'Continue with starting cylinder {first+1:04}' in last,last
        for ch in f'{first:04}': key(ch)
        key('Return');wait(f'Continue with starting cylinder {first:04}','restored-start')
    key('F10');wait('Enter partition size','size')
    assert f'{bios_cylinders:04} of {bios_cylinders:04} cylinders assigned:' in last,last
    if not A.expect_hang:
        for ch in str(maximum_length+1): key(ch)
        key('Return');wait('Enter partition size: ____','rejected-size')
        assert f'Continue with partition size of {maximum_length:04}' in last,last
        for ch in str(length-1): key(ch)
        key('Return');wait(f'Continue with partition size of {length-1:04}','confirmed-size')
        for ch in str(length): key(ch)
        key('F10');wait(f'Continue with partition size of {length:04}','confirmed-size-f10')
    key('F10')
    if A.expect_hang=='options':
        try:wait('Accept CP/M options shown','options',15)
        except AssertionError:
            assert 'reading the data back.' in last,last
            print('PASS: reproduced options-screen hang',flush=True);success=True
        else:raise AssertionError('Broken binary unexpectedly passed options')
    else:
        wait('Accept CP/M options shown','options')
        # Exercise an option redraw before accepting the final settings.
        key('F4');wait('Accept CP/M options shown','options-redraw')
        key('F10')
        wait('Creation of CP/M volume complete','complete',180)
        assert f'{first:04}-{first+length-1:04}' in last,last
        assert '00000 bad blocks found' in last,last
        # The completion title precedes the controls and menu input flush.
        # Take another guest observation before sending the continuation key.
        wait('To continue','complete-controls')
        key('F9');wait('Please insert a system diskette','reboot')
        success=True
finally:
    vm.close()

if not A.expect_hang:
    with hard.open('rb') as f:
        after=f.read(512);f.seek(start+1536);label=f.read(512)
    for index,_,_,_ in foreign:
        at=446+index*16
        assert after[at:at+16]==mbr[at:at+16], 'Foreign partition entry changed'
    assert after[510:]==b'\x55\xaa'
    entries=[after[i:i+16] for i in range(446,510,16)]
    cpm=[e for e in entries if e[4]==0xdb]
    assert len(cpm)==1 and struct.unpack_from('<II',cpm[0],8)==(first*spc+(first==0),length*spc-(first==0))
    kib = (length-2)*spc//2
    shift = 4 if kib <= 1024 else (5 if kib <= 16384 else 6)
    blocks = (length-2)*spc*512//(128 << shift)
    assert label[43]==shift and struct.unpack_from('<H',label,46)[0]==blocks-1, 'Unexpected DPB'
    assert cpm[0][3] | ((cpm[0][2] & 0xc0) << 2) == first
    assert cpm[0][7] | ((cpm[0][6] & 0xc0) << 2) == first+length-1
    assert len([e for e in entries if e[4]]) == len(foreign)+1, 'Unexpected partition count'
    if foreign:
        assert run('mtype','-i',f'hard.img@@{SPT*512}','::DOSKEEP.TXT').stdout == dos_text, 'DOS file changed'
    assert sum(struct.unpack('<256H',label))&65535==0,'Invalid label checksum'
    assert before==(digest_range(hard,512,max(512,start)),digest_range(hard,end,size)), 'Out-of-partition write'
    raw=CMD.read_bytes();n=int.from_bytes(raw[1:3],'little')*16;data=raw[128+n:]
    expected_bootstrap = mbr[:446] if A.preserve_mbr else data[0xefe:0xefe+446]
    assert after[:446]==expected_bootstrap, 'MBR bootstrap policy not respected'
    print(f'PASS: guest-created {length}-cylinder volume at {first}; DPB/checksum/MBR and protected regions verified',flush=True)
assert success
if not A.keep_images:
    for path in F.iterdir():
        if path.is_file() and path.suffix.lower() in ('.img','.sys','.cmd'):
            path.unlink()
print(f'PASS: {A.emulator} {A.personality} {A.layout}; diagnostics at {F}',flush=True)
