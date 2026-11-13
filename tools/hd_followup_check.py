#!/usr/bin/env python3
"""Cold boot and exact metadata repair on an hd_volume_check disposable fixture.

Requires --fixture explicitly; modifies only that temporary test directory.
"""
from pathlib import Path
import argparse,re,struct,subprocess,shutil
P=argparse.ArgumentParser();P.add_argument('--fixture',type=Path,required=True);P.add_argument('--maint',type=Path,required=True);P.add_argument('--system',choices=['cpm','ccpm','native','cdos'],required=True);P.add_argument('--root',type=Path,required=True);A=P.parse_args()
F=A.fixture.resolve();assert F.name.startswith('hd-volume-') and str(F).startswith(('/tmp/','/private/','/var/folders/'))
ROOT=A.root.resolve();M=A.maint.resolve();cfg=(F/'test.cfg').read_text();image=(F/'hard.img').read_bytes()
start_lba=struct.unpack_from('<I',image,454)[0];off=start_lba*512;label=image[off+1536:off+2048]
start,length=struct.unpack_from('<HH',label,33);heads,spt=label[37:39];base=(start+1)*heads*spt*512
raw=(M/'hdmaint.cmd').read_bytes();n=int.from_bytes(raw[1:3],'little')*16;data=raw[128+n:];boot=bytearray(data[0x10fe:0x30fe]);boot[1536:2048]=label
with (F/'hard.img').open('r+b') as f:f.seek(off);f.write(boot)
def run(*args):return subprocess.run(args,cwd=F,check=True,capture_output=True)
def screen(name):
 b=(F/(name+'.bin')).read_bytes();t='\n'.join(bytes(b[i:i+160:2]).decode('cp437') for i in range(0,len(b),160));(F/(name+'.txt')).write_text(t);return t
def execute(config,commands,log):
 (F/'followup.cfg').write_text(config)
 with (F/(log+'.log')).open('wb') as f:subprocess.run(['pce-ibmpc','-c','followup.cfg','-t','null','-g','vga'],cwd=F,input=('\n'.join(commands)+'\n').encode(),stdout=f,stderr=f,check=True,timeout=240)
# New-volume boot bundle; no floppy media are available during this phase.
cold=re.sub(r'boot\s*=\s*0','boot = 128',cfg,count=1)
cold=re.sub(r'disk\s*\{\s*drive=[01]\s+.*?\}', '',cold,flags=re.S)
execute(cold,['c 20000000','save "cold.bin" bin b800:0000 fa0','q'],'cold')
t=screen('cold');assert re.search(r'\b[C-F]>',t),t
print('PASS: cold boot from high-block system file:',A.system,spt,flush=True)
# Install the same rebuilt checker for every guest. It detects the OS at run time.
fmt='cpm86-320' if A.system=='cpm' else 'ccpm86-320'
run('python3',str(ROOT/'tools/cpm86twist.py'),'untwist','floppy.img','check.logical')
# Permit rerunning the test with a newer checker on the same fixture.
subprocess.run(['cpmrm','-f',fmt,'check.logical','0:CHKCPMFS.CMD'],cwd=F,capture_output=True)
run('cpmcp','-f',fmt,'check.logical',str(M.parent/'chkcpmfs/chkcpmfs.cmd'),'0:CHKCPMFS.CMD')
run('python3',str(ROOT/'tools/cpm86twist.py'),'twist','check.logical','floppy.img')
expected=(F/'hard.img').read_bytes();dirty=bytearray(expected);dirty[base+12]|=0xe0;dirty[base+14]|=0xc0;(F/'hard.img').write_bytes(dirty)
commands=['c f000000'];drive='d' if A.system=='cdos' else 'c'
keys={':':'+Shift Semicolon -Shift',' ':'Space','[':'LeftBracket',']':'RightBracket'}
def command(text):
 for ch in text:commands.extend(['key '+keys.get(ch,ch),'c 200000'])
 commands.extend(['key Return','c 10000000'])
command('chkcpmfs '+drive+': [f]')
commands.extend(['save "plan.bin" bin b800:0000 fa0','key y','c 10000000','save "repair.bin" bin b800:0000 fa0'])
command('chkcpmfs '+drive+':')
commands.extend(['save "clean.bin" bin b800:0000 fa0','q'])
execute(cfg,commands,'repair')
t=screen('repair');assert 'Metadata repairs written and verified.' in t,t
t=screen('clean');assert 'Consistency errors: 0' in t,t
assert (F/'hard.img').read_bytes()==expected,'Repair changed bytes outside the two reserved-bit fields'
print('PASS: live checker repair, clean rescan and exact whole-disk comparison:',A.system,spt,flush=True)
