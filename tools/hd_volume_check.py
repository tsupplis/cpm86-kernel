#!/usr/bin/env python3
"""Disposable PCE hard-disk interoperability test; never opens a real disk.

Prepare a label matching HDMAINT, put the system file above 8 MiB, occupy
most blocks, then create/read a file through BDOS until disk-full. Check the
result and partition guard regions on the host. --system selects the guest.
"""
from pathlib import Path
import argparse,math,re,shutil,struct,subprocess,tempfile
P=argparse.ArgumentParser();P.add_argument('--system',choices=['cpm','ccpm','native','cdos'],default='ccpm');P.add_argument('--kib',type=int,default=30720);P.add_argument('--spt',type=int,default=17);P.add_argument('--root',type=Path);P.add_argument('--maint',type=Path);A=P.parse_args()
ROOT=(A.root or Path(__file__).resolve().parents[1]).resolve()
F=Path(tempfile.mkdtemp(prefix='hd-volume-'));print('Diagnostics:',F,flush=True)
def run(*args,**kw):return subprocess.run(args,cwd=F,check=True,capture_output=True,**kw)
ccpm=A.system in ['ccpm','native'];cdos=A.system=='cdos';heads=8 if A.spt==17 else 16;spc=heads*A.spt
start=100;length=math.ceil(A.kib*2/spc)+2;total=start+length+10
kib=(length-2)*spc//2;bs=8192 if kib>16384 else 4096;bsh=6 if bs==8192 else 5
blocks=kib*1024//bs;assert blocks<=4096
# Rebuilt maintained HDMAINT provides the unchanged label identity/setup and
# its updated loader. CDOS interoperability uses the same prepared volume.
maint=ROOT/'commands/hdmaint'
if cdos:maint=ROOT.parent/'ccpm86-kernel/commands/hdmaint'
if A.maint:maint=A.maint
b=(maint/'hdmaint.cmd').read_bytes();n=int.from_bytes(b[1:3],'little')*16;data=b[128+n:]
label=bytearray(data[0x16fe:0x18fe]);W=lambda at,v:struct.pack_into('<H',label,at,v)
W(33,start);W(35,length);label[37:41]=bytes([heads,A.spt,0,4]);W(41,A.spt*4)
label[43:46]=bytes([bsh,(1<<bsh)-1,1]);W(46,blocks-1);W(48,1023)
reserved=65536//bs;mask=((1<<reserved)-1)<<(16-reserved);label[50:52]=mask.to_bytes(2,'big')
W(52,0x8000);W(54,(start+1)*heads);W(64,16);W(66,min(220,spc//4));W(68,0);W(70,(length-1)*spc//4-1)
W(0,0);W(0,(-sum(struct.unpack('<256H',label)))&65535)
image=bytearray([0x5a])*(total*spc*512)
entry=bytearray(16);entry[0]=0x80
for at,c,h,s in [(1,start,0,1),(5,start+length-1,heads-1,A.spt)]:entry[at:at+3]=bytes([h,s|((c>>8)<<6),c&255])
entry[4]=0xdb;struct.pack_into('<II',entry,8,start*spc,length*spc)
mbr=bytearray(data[0xefe:0x10fe]);mbr[446:510]=bytes(64);mbr[446:462]=entry;mbr[510:]=b'\x55\xaa';image[:512]=mbr
boot=data[0x10fe:0x30fe];off=start*spc*512
image[off:off+len(boot)]=boot;image[off+3*512:off+4*512]=label
# Away from cylinder zero, boot copies occupy sectors one/two; label is four.
base=(start+1)*spc*512;image[base:base+65536]=b'\xe5'*65536
kernel=ROOT/('kernel/sysgen/ccpm-native.sys' if A.system=='native' else 'kernel/sysgen/ccpm.sys') if ccpm or cdos else ROOT/'cpm.sys'
kbytes=kernel.read_bytes();kn=math.ceil(len(kbytes)/bs);first_kernel=blocks-kn-64
entries=[]
def add_file(name,first,count,content=None):
 stem,ext=name.split('.');group=0
 while count:
  take=min(32768//bs,count);chunk=(content or b'')[group*32768:(group+1)*32768]
  size=len(chunk) if content is not None else take*bs;records=math.ceil(size/128)
  extent=group*2+(records-1)//128
  e=bytearray(32);e[1:12]=stem.ljust(8).encode()+ext.ljust(3).encode();e[12]=extent&31;e[14]=extent>>5;e[15]=(records-1)%128+1
  for j in range(take):struct.pack_into('<H',e,16+j*2,first+j)
  entries.append(e)
  if content is not None:image[base+first*bs:base+first*bs+len(chunk)]=chunk
  first+=take;count-=take;group+=1
cur=reserved;i=0
while cur<first_kernel:
 count=min(8*1024*1024//bs,first_kernel-cur);add_file(f'FILL{i}.DAT',cur,count);cur+=count;i+=1
add_file('CCPM.SYS' if ccpm or cdos else 'CPM.SYS',first_kernel,kn,kbytes)
assert len(entries)<1024
for i,e in enumerate(entries):image[base+i*32:base+(i+1)*32]=e
(F/'hard.img').write_bytes(image)
before_prefix=bytes(image[:off]);before_suffix=bytes(image[(start+length)*spc*512:]);del image
# Build a real 8080-model CMD, keeping code and its private DMA/stack together.
drive=3 if cdos else 2
asm=f'''bits 16
cpu 8086
org 0
 times 100h db 0
 push cs
 pop ds
 push cs
 pop ss
 mov sp,stacktop
 mov cx,14
 mov dx,{drive}
 int 0e0h
 mov cx,26
 mov dx,buffer
 int 0e0h
 mov byte [phase],'1'
 mov cx,22
 mov dx,fcb
 int 0e0h
 cmp al,255
 je fail
 xor bp,bp
write_loop:
 mov byte [phase],'2'
 mov di,buffer
 mov cx,64
 mov ax,bp
 push ds
 pop es
 rep stosw
 mov cx,21
 mov dx,fcb
 int 0e0h
 or al,al
 jnz full
 inc bp
 cmp bp,5000
 jb write_loop
 jmp fail
full:
 mov byte [phase],'3'
 add al,48
 mov [result],al
 sub al,48
 cmp al,2
 jne fail
 cmp bp,100
 jb fail
 mov byte [phase],'4'
 mov cx,16
 mov dx,fcb
 int 0e0h
 cmp al,255
 je fail
 mov [written],bp
 push ds
 pop es
 mov di,fcb+12
 mov cx,24
 xor ax,ax
 rep stosb
 mov byte [phase],'5'
 mov cx,15
 mov dx,fcb
 int 0e0h
 cmp al,255
 je fail
 xor bp,bp
read_loop:
 mov byte [phase],'6'
 mov cx,20
 mov dx,fcb
 int 0e0h
 or al,al
 jnz fail
 mov byte [phase],'7'
 push ds
 pop es
 mov di,buffer
 mov cx,64
 mov ax,bp
 repe scasw
 jne fail
 inc bp
 cmp bp,[written]
 jb read_loop
 mov dx,passed
 jmp done
fail:
 mov dx,failed
done:
 mov cx,9
 int 0e0h
 mov cx,0
 int 0e0h
passed db 'HDTEST PASS',13,10,'$'
failed db 'HDTEST FAIL phase '
phase db '0'
 db ' result '
result db '0',13,10,'$'
written dw 0
fcb db 0,'HDTEST  DAT'
 times 24 db 0
buffer times 128 db 0
 times 512 db 0
stacktop:
'''
(F/'hdtest.asm').write_text(asm);run('nasm','-f','bin','hdtest.asm','-o','hdtest.bin');payload=(F/'hdtest.bin').read_bytes();paras=math.ceil(len(payload)/16);header=bytearray(128);header[0]=1;struct.pack_into('<HHHH',header,1,paras,0,paras,0);(F/'hdtest.cmd').write_bytes(header+payload+bytes(paras*16-len(payload)))
config=ROOT/('media/cdos86.cfg' if cdos else 'media/ccpm86.cfg' if ccpm else 'cpm86-320.cfg')
bootbase=ROOT/('media/cdos86base.img' if cdos else 'media/ccpm86base.img' if ccpm else 'base-320.img')
shutil.copyfile(ROOT/('media/diskdefs' if ccpm or cdos else 'diskdefs'),F/'diskdefs')
run('python3',str(ROOT/'tools/cpm86twist.py'),'untwist',str(bootbase),'floppy.logical')
fmt='ccpm86-320' if ccpm or cdos else 'cpm86-320'
run('cpmcp','-f',fmt,'floppy.logical',str(kernel),'0:CCPM.SYS' if ccpm or cdos else '0:CPM.SYS')
run('cpmcp','-f',fmt,'floppy.logical','hdtest.cmd','0:HDTEST.CMD')
run('python3',str(ROOT/'tools/cpm86twist.py'),'twist','floppy.logical','floppy.img')
cfg=config.read_text().replace('driver = "sdl"','driver = "null"').replace('sdl:lowpass=5000','null')
cfg=re.sub(r'(ram\s*\{.*?size\s*=\s*)\d+K',r'\g<1>640K',cfg,flags=re.S)
cfg=re.sub(r'floppy_disk_drives\s*=\s*\d+', 'floppy_disk_drives = 2',cfg)
cfg=re.sub(r'disk\s*\{.*?\}', '',cfg,flags=re.S)
cfg=re.sub(r'(?m)^path\s*=\s*"([^"\n]+)"',lambda m:'path = "'+str((config.parent/m[1]).resolve())+'"',cfg)
cfg+='\ndisk { drive=0 type="auto" file="floppy.img" }\ndisk { drive=1 type="auto" file="floppy.img" }\n'
cfg+=f'\ndisk {{ drive=128 type="image" file="hard.img" c={total} h={heads} s={A.spt} }}\n'
(F/'test.cfg').write_text(cfg)
commands=['c f000000']
for ch in 'hdtest':commands+=['key '+ch,'c 200000']
commands+=['key Return','c 40000000','save "screen.bin" bin b800:0000 fa0','q']
with (F/'pce.log').open('wb') as log:
 subprocess.run(['pce-ibmpc','-c','test.cfg','-t','null','-g','vga'],cwd=F,input=('\n'.join(commands)+'\n').encode(),stdout=log,stderr=log,check=True,timeout=240)
b=(F/'screen.bin').read_bytes();screen='\n'.join(bytes(b[i:i+160:2]).decode('cp437') for i in range(0,len(b),160));(F/'screen.txt').write_text(screen)
assert 'HDTEST PASS' in screen,screen
actual=(F/'hard.img').read_bytes();assert actual[:off]==before_prefix;assert actual[(start+length)*spc*512:]==before_suffix
records=[]
for i in range(1024):
 e=actual[base+i*32:base+(i+1)*32]
 if e[0]!=0 or e[1:12]!=b'HDTEST  DAT':continue
 extent=e[12]+32*e[14];length_records=(extent&1)*128+e[15]
 part=b''.join(actual[base+blk*bs:base+(blk+1)*bs] for blk in struct.unpack('<8H',e[16:]) if blk)
 records.append((extent//2,part[:length_records*128]))
file=b''.join(part for _,part in sorted(records));assert len(file)>100*128
for i in range(len(file)//128):assert file[i*128:(i+1)*128]==struct.pack('<H',i)*64,i
print(f'PASS: {A.system}, {kib} KiB, {A.spt} sectors/track: disk full, guest/host readback and partition guards; {len(file)} bytes written',flush=True)
