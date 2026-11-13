#!/usr/bin/env python3
"""8086 execution checks for hard-disk reservation and record arithmetic."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'commands/hdmaint'))
from check_capacity import Machine,symbols,eq

if (ROOT/'kernel/con').exists():
    for variant in ['xios','xiosnat']:
        folder=ROOT/'kernel/con'
        raw=(folder/(variant+'.con')).read_bytes()
        n=int.from_bytes(raw[1:3],'little')*16
        image=raw[128:128+n]
        m=Machine(image,image,symbols(folder/(variant+'.sym')))
        template=m.s('HDDPBINIT')
        assert int.from_bytes(image[template+5:template+7],'little')==4095
        assert int.from_bytes(image[template+7:template+9],'little')==2047
        for dsm,bsh,drm,cks,ok in [(2592,5,1023,0x8000,1),(2559,6,1023,0x8000,1),(3839,6,2047,0x8000,1),(4031,6,1023,0x8000,1),(4032,6,1023,0x8000,0),(4096,5,1023,0x8000,0),(4031,6,2048,0x8000,0),(4031,7,1023,0x8000,0),(4031,6,1023,0,0)]:
            base=m.s('hdlabel0')
            m.run('hdcapacity',f'''mov si,{base}
 mov word [si+46],{dsm}
 mov byte [si+43],{bsh}
 mov word [si+48],{drm}
 mov word [si+52],{cks}
''',f'cmp ax,{0 if ok else 65535}\n jne failed')
        print(f'PASS: {variant}: {m.count} label limits; 1024-byte allocation reservation per drive')
else:
    for variant,bdos,bios in [('cpm','bdos','pcbios'),('cpmexp','bdosexp','pcbioexp')]:
        raw=(ROOT/(variant+'.sys')).read_bytes()[128:]
        names=symbols(ROOT/(bdos+'.sym'));names.update(symbols(ROOT/(bios+'.sym')))
        image=raw+bytes(max(0,0x5000-len(raw)))
        m=Machine(image,image,names);S=m.s
        for block,shift,record in [(1,5,0),(2047,5,31),(2048,5,0),(4095,5,31),(2560,6,63),(3840,6,12),(4031,6,63)]:
            logical=block*(1<<shift)+record
            setup=f'''mov word [{S('TGSECT')}],{block}
 mov byte [{S('BSH')}],{shift}
 mov byte [{S('BLM')}],{(1<<shift)-1}
 mov byte [{S('CURCNT')}],{record}
'''
            m.run('BLTSCT',setup,eq(S('TGSECT'),logical&65535)+eq(S('TGSHI'),logical>>16))
            for spt,offset in [(68,4),(252,3216)]:
                setup=f'''mov word [{S('TGSECT')}],{logical&65535}
 mov word [{S('TGSHI')}],{logical>>16}
 mov word [{S('SPT')}],{spt}
 mov word [{S('TRKOFF')}],{offset}
 mov word [{S('PNTRAK')}],4f00h
'''
                patches={S('VSTTRK'):'mov [4f02h],cx\n ret',S('VSTSEC'):'mov [4f04h],cx\n ret',S('VSCTRN'):'mov bx,cx\n ret'}
                m.run('TRSSET',setup,eq(0x4f02,logical//spt+offset)+eq(0x4f04,logical%spt),patches)
        for dsm,bsh,drm,ok in [(2592,5,1023,1),(2559,6,1023,1),(3839,6,2047,1),(4031,6,1023,1),(4032,6,1023,0),(4096,5,1023,0),(4031,6,2048,0),(4031,7,1023,0)]:
            base=S('HDDBUF')
            m.run('HD_CAPACITY',f'''mov word [{base+46}],{dsm}
 mov byte [{base+43}],{bsh}
 mov word [{base+48}],{drm}
 mov word [{base+52}],8000h
 mov word [{base+68}],0
''',('jc' if ok else 'jnc')+' failed')
        print(f'PASS: {variant}: {m.count} capacity/record/BIOS-address boundary cases')
