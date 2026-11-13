"""Execute maintained capacity/MBR/loader routines on an 8086 emulator.

Disk BIOS boundaries are stubbed; no real disk is opened or written.
"""
from pathlib import Path
import re, struct, subprocess, tempfile

ROOT = Path(__file__).resolve().parent

def symbols(path):
    return {n: int(v, 16) for v, n in re.findall(r'\b([0-9A-F]{4})\s+([A-Z][A-Z0-9]*)', path.read_text())}

def key(name):
    return name.replace('_', '').upper()

class Machine:
    def __init__(self, code, data, names):
        self.code, self.data, self.names = bytes(code), bytes(data), names
        self.count = 0
    def s(self, name): return self.names[key(name)]
    def run(self, entry, setup='', checks='', patches=None, bridge=None):
        with tempfile.TemporaryDirectory(prefix='hd-capacity-') as td:
            p=Path(td)
            def asm(source):
                (p/'stub.asm').write_text('bits 16\ncpu 8086\n'+source)
                subprocess.run(['nasm','-f','bin','stub.asm','-o','stub.bin'],cwd=p,check=True,capture_output=True)
                return (p/'stub.bin').read_bytes()
            code=bytearray(self.code)
            for target, stub in (patches or {}).items():
                at=self.s(target) if isinstance(target,str) else target
                dest=len(code);code+=asm(stub)
                code[at:at+3]=b'\xe9'+((dest-at-3)&65535).to_bytes(2,'little')
            target=len(code)
            if bridge is None:
                code+=b'\xe8'+((self.s(entry)-target-3)&65535).to_bytes(2,'little')+b'\xcb'
            else:
                code+=asm('org '+str(target)+'\n'+bridge)
            (p/'code.bin').write_bytes(code)
            (p/'data.bin').write_bytes(self.data)
            (p/'test.asm').write_text(f'''bits 16
cpu 8086
org 100h
 mov ax,cs
 add ax,(code-$$+100h)/16
 mov [target+2],ax
 mov ax,cs
 add ax,(data-$$+100h)/16
 mov ds,ax
 mov es,ax
{setup}
 call far [cs:target]
{checks}
 mov ax,4c00h
 int 21h
failed:
 mov ax,4c01h
 int 21h
target dw {target},0
align 16
code: incbin "code.bin"
align 16
data: incbin "data.bin"
''')
            subprocess.run(['nasm','-f','bin','test.asm','-o','test.com'],cwd=p,check=True,capture_output=True)
            result=subprocess.run(['emu2','test.com'],cwd=p,capture_output=True,timeout=10)
            assert result.returncode==0,(entry,setup,checks,result.returncode,result.stdout,result.stderr)
        self.count+=1

def eq(where,value,byte=False):
    return f' cmp {"byte" if byte else "word"} [{where}],{value}\n jne failed\n'

def main():
    raw=(ROOT/'hdmaint.cmd').read_bytes()
    n=struct.unpack_from('<H',raw,1)[0]*16
    m=struct.unpack_from('<H',raw,10)[0]*16
    h=Machine(raw[128:128+n],raw[128+n:128+n+m],symbols(ROOT/'hdmaint.sym'))
    S=h.s
    for heads,spt in [(4,17),(8,17),(16,63)]:
        spc=heads*spt
        bound=min(64512//spc+2,65535//spc+1)
        h.run('default_partition_at_0646',f'mov word [{S("sectors_per_cylinder")}],{spc}',eq(S('maximum_cpm22_cylinders'),bound))
        for start,length in [(0,42),(1,63),(300,66),(900,42)]:
            entry=S('selected_disk')+0x265
            setup=f'''mov word [{S('cpm_partition_offset')}],265h
 mov word [{S('partition_start')}],{start}
 mov word [{S('partition_end')}],{start+length-1}
 mov word [{S('partition_cylinders_count')}],{length}
 mov word [{S('sectors_per_cylinder')}],{spc}
 mov byte [{S('physical_spt')}],{spt}
 mov byte [{S('last_head')}],{heads-1}
 mov word [{entry+10}],0ffffh
 mov word [{entry+14}],0ffffh
'''
            lba=start*spc+(start==0);size=length*spc-(start==0)
            h.run('encode_partition',setup,eq(entry+8,lba&65535)+eq(entry+10,lba>>16)+eq(entry+12,size&65535)+eq(entry+14,size>>16))
    for cylinders in [18,34,42,63,66]:
        kib=(cylinders-2)*504
        shift=6 if kib>16384 else 5
        blocks=kib//(1<<(shift-3))
        setup=f"""mov byte [{S('last_head')}],15
 mov byte [{S('sectors_per_track')}],63
 mov word [{S('sectors_per_cylinder')}],1008
 mov word [{S('partition_cylinders_count')}],{cylinders}
 mov word [{S('partition_start')}],300
 mov word [{S('current_extent_pointer')}],{S('free_extents')}
"""
        h.run('calculate_dpb',setup,eq(S('dpb_bsh'),shift,True)+eq(S('dpb_exm'),1,True)+eq(S('dpb_dsm'),blocks-1))
    for shift in [4,5,6]:
        for bad in [0,1,2,3,4,5,17]:
            h.run('finalize_bad_blocks',f"""mov byte [{S('physical_spt')}],63
 mov byte [{S('head_count')}],16
 mov byte [{S('dpb_bsh')}],{shift}
 mov word [{S('dpb_dsm')}],4000
 mov word [{S('bad_block_count')}],{bad}
 mov word [{S('original_spare_base')}],16000
""",eq(S('dpb_dsm'),4000-((bad+(1<<(shift-4))-1)>>(shift-4))))
    # Foreign partitions occupy their full LBA extent, including extended
    # containers and partial cylinders; stale CHS fields are ignored.
    base=S('selected_disk');entry=base+0x265
    for kind,start,size in [(5,0,1008*400),(15,1008*300+63,1008*100),(7,1008*800,1008*200),(6,0x100000,0xffffffff),(7,20,0)]:
        bad=size==0 or start+size>1008*1024
        first=0 if bad else start//1008
        last=1023 if bad else (start+size-1)//1008
        setup=f'''mov bx,{base}
 mov si,265h
 mov dx,1234h
 mov word [bx+4],1008
 mov word [bx+14],1024
 mov byte [{entry+4}],{kind}
 mov word [{entry+8}],{start&65535}
 mov word [{entry+10}],{start>>16}
 mov word [{entry+12}],{size&65535}
 mov word [{entry+14}],{size>>16}
'''
        h.run('entry_cylinder_range',setup,f'cmp cx,{first}\n jne failed\n cmp ax,{last}\n jne failed\n cmp dx,1234h\n jne failed')
    # Run the actual free-space scanner, including an invalid entry after
    # a previously discovered hole. Invalid metadata must erase that hole.
    for invalid in [False, True]:
        setup=f"""mov bx,{base}
 mov word [bx+4],1008
 mov word [bx+14],1024
"""
        for index,start_c,end_c in [(0,100,199),(1,300,399)]:
            at=base+0x265+16*index
            size=(end_c-start_c+1)*1008 if not (invalid and index==1) else 0
            lba=start_c*1008
            setup+=f"""mov byte [{at+4}],5
 mov word [{at+8}],{lba&65535}
 mov word [{at+10}],{lba>>16}
 mov word [{at+12}],{size&65535}
 mov word [{at+14}],{size>>16}
"""
        checks=eq(base+0x12,0 if invalid else 255,True)
        if invalid:checks+=eq(base+0x28,65535)
        else:
            for off,value in [(0x28,0),(0x2a,99),(0x2c,200),(0x2e,299),(0x30,400),(0x32,1023)]:checks+=eq(base+off,value)
        h.run('build_free_extents',setup,checks,
              {'initialize_bad_cylinders':'pop bx\n retf'},
              f'push bx\n jmp {S("build_free_extents")}')
    # The maintained loader must keep all legacy vector/data addresses.
    old=symbols(ROOT/'loader.sym');new=symbols(ROOT/'ldlarge.sym')
    for name in ['BDEXTPNT','BDSTDIRT','BDTRSSET','BIOSCOLDVECTOR','DIRECTORYBUFFER','BDTGSECT']:
        assert old[name]==new[name],name
    raw=(ROOT/'ldlarge.bin').read_bytes()
    loader=Machine(raw+bytes(0x2800-len(raw)),raw+bytes(0x2800-len(raw)),new)
    S=loader.s
    for block,shift,record in [(1,5,0),(2047,5,31),(2048,5,0),(4096,5,17),(8063,5,31),(4031,6,63)]:
        logical=block*(1<<shift)+record
        loader.run('bd_bltsct',f'mov word [{S("bd_tgsect")}],{block}\n mov byte [{S("bd_bsh")}],{shift}\n mov byte [{S("bd_blm")}],{(1<<shift)-1}\n mov byte [{S("bd_curcnt")}],{record}',eq(S('bd_tgsect'),logical&65535)+eq(0x11b8,logical>>16))
    assert new['ALLOCATIONVECTOR']==0x2200
    print(f'PASS: {h.count} formatter/MBR cases; {loader.count} loader record-boundary cases; stable loader ABI')

if __name__=='__main__':main()
