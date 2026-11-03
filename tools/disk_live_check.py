#!/usr/bin/env python3
"""Actual CP/M/CCP/M copy/compare with nine physical sectors under PCE.

The disposable source keeps its native eight-sector CP/M filesystem and adds
one uniquely patterned ninth sector per physical head. Thus it can still load
the tools normally while proving all nine sectors are copied and compared.
"""
from pathlib import Path
import re,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parent.parent
CCPM=(ROOT/'media/ccpm86.cfg').exists()
F=Path(tempfile.mkdtemp(prefix='ccpm-disk-live-' if CCPM else 'cpm-disk-live-'))
print('Diagnostics:',F,flush=True)
def run(*args,**kw):return subprocess.run(args,cwd=F,capture_output=True,check=True,**kw)
definitions=ROOT/('media/diskdefs' if CCPM else 'diskdefs')
shutil.copyfile(definitions,F/'diskdefs')
if CCPM:
    # Build a minimal boot disk from the local template, not from the crowded
    # full system distribution. Only the rebuilt local kernel and tools enter it.
    run('python3',str(ROOT/'tools/cpm86twist.py'),'untwist',str(ROOT/'media/ccpm86base.img'),'logical.img')
    fmt='ccpm86-320'
    run('cpmcp','-f',fmt,'logical.img',str(ROOT/'kernel/sysgen/ccpm.sys'),'0:CCPM.SYS')
else:
    run('python3',str(ROOT/'tools/cpm86twist.py'),'untwist',str(ROOT/'base-320.img'),'logical.img')
    fmt='cpm86-320'
    run('cpmcp','-f',fmt,'logical.img',str(ROOT/'cpm.sys'),'0:CPM.SYS')
for tool in ['dcopy','dcomp']:
    run('cpmcp','-f',fmt,'logical.img',str(ROOT/f'commands/disk/{tool}.cmd'),'0:')
run('python3',str(ROOT/'tools/cpm86twist.py'),'twist','logical.img','native.img')
b=(F/'native.img').read_bytes();assert len(b)==327680
expanded=b''.join(b[i*4096:(i+1)*4096]+bytes([0xa0+i%48])*512 for i in range(80))
(F/'source.img').write_bytes(expanded)
(F/'target.img').write_bytes(bytes([0xe5])*368640)
config=ROOT/('media/ccpm86.cfg' if CCPM else 'cpm86-320.cfg')
cfg=config.read_text().replace('driver = "sdl"','driver = "null"').replace('sdl:lowpass=5000','null')
# Replace only configured floppy files; ROM paths stay local to this project.
cfg=re.sub(r'file\s*=\s*"(?:ccpm86|cpm86-320-at)\.img"','file = "source.img"',cfg)
cfg=re.sub(r'file\s*=\s*"(?:ccpmtools|cpm86-320-dev)\.img"','file = "target.img"',cfg)
base=config.parent
cfg=re.sub(r'(?m)^path\s*=\s*"([^"\n]+)"',lambda m:'path = "'+str((base/m[1]).resolve())+'"',cfg)
(F/'test.cfg').write_text(cfg)
c=['c f000000'];keys={':':'+Shift Semicolon -Shift',' ':'Space','[':'LeftBracket',']':'RightBracket'}
def command(s):
    for ch in s:c.extend(['key '+keys.get(ch,ch),'c 200000'])
    c.extend(['key Return','c 6000000'])
command('dcopy a: b: [9]')
c.extend(['key Space','c 40000000','save "copy.bin" bin b800:0000 fa0','key n','c 4000000'])
command('dcomp a: b: [9]')
c.extend(['key Space','c 40000000','save "compare.bin" bin b800:0000 fa0','key n','c 4000000','q'])
with (F/'pce.log').open('wb') as log:
    subprocess.run(['pce-ibmpc','-c','test.cfg','-t','null','-g','vga'],cwd=F,input=('\n'.join(c)+'\n').encode(),stdout=log,stderr=log,timeout=240,check=True)
def screen(name):
    b=(F/(name+'.bin')).read_bytes();s='\n'.join(bytes(b[i:i+160:2]).decode('cp437').rstrip() for i in range(0,3840,160));(F/(name+'.txt')).write_text(s);return s
s=screen('copy');assert 'Copy complete' in s,s
s=screen('compare');assert 'Diskettes compare ok' in s,s
assert (F/'source.img').read_bytes()==(F/'target.img').read_bytes(),'Physical nine-sector data differ'
print('PASS: actual '+('updated CCP/M XIOS' if CCPM else 'CP/M BIOS')+' nine-sector copy/compare; every physical byte matches and CMD MIN-reserved DMA storage works')
shutil.rmtree(F)
