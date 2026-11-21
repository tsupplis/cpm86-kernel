#!/usr/bin/env python3
"""Execute native floppy record/cache/CHS mapping for both PC BIOS variants."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'commands/hdmaint'))
from check_capacity import Machine, symbols
from kernel_check import image_map


def main():
    for variant in ['pcbios', 'pcbioexp']:
        emitted = image_map(ROOT / (variant + '.h86'))
        image = bytearray(0x7100)
        for (_, address), byte in emitted.items():
            image[address] = byte
        machine = Machine(image, image, symbols(ROOT / (variant + '.sym')))
        at = machine.s
        records = 0
        for index, cylinders, tracks, sectors in [(0, 40, 40, 8), (1, 40, 80, 8),
                                                  (2, 80, 160, 9), (3, 80, 160, 18), (5, 80, 160, 15)]:
            setup = f'''mov word [{at('DPH0')}+10],{at('DPB'+str(index))}
 mov byte [{at('DISK')}],0
 mov byte [{at('DRVTYPE')}],0
'''
            bridge = f'''xor bp,bp
track:
 xor di,di
record:
 mov [{at('TRK')}],bp
 mov [{at('SECT')}],di
 call {at('CALC_PHYSEC')}
 mov ax,di
 and ax,31
 cmp [{at('PHY_SEC')}],ax
 jne failed
 mov ax,di
 mov cl,5
 shr ax,cl
 mov bx,bp
 shl bx,1
 add bx,bp
 add ax,bx
 cmp [{at('PHY_TRK')}],ax
 jne failed
 xor dx,dx
 call {at('SETUP_INTREG')}
 mov [7000h],ax
 mov [7002h],cx
 mov [7004h],dx
 cmp bx,{at('DSKBUF')}
 jne failed
 or si,si
 jne failed
 mov ax,es
 mov bx,cs
 cmp ax,bx
 jne failed
 mov ax,di
 mov cl,5
 shr ax,cl
 mov cl,3
 shl ax,cl
 inc ax
 cmp [7002h],al
 jne failed
 mov bx,{sectors+1}
 sub bx,ax
 cmp bx,8
 jbe count
 mov bx,8
count:
 cmp [7000h],bl
 jne failed
 mov ax,bp
 xor dx,dx
 cmp ax,{cylinders}
 jb cylinder
 mov ax,{2*cylinders-1}
 sub ax,bp
 mov dh,1
cylinder:
 cmp [7003h],al
 jne failed
 cmp [7004h],dx
 jne failed
 inc di
 cmp di,{sectors*4}
 jb record
 inc bp
 cmp bp,{tracks}
 jb track
 xor ax,ax
 retf
failed:
 mov ax,1
 retf
'''
            machine.run('CALC_PHYSEC', setup, 'or ax,ax\n jnz failed', bridge=bridge)
            records += tracks * sectors * 4
        # FD_FLUSH is called only for dirty data during floppy relogin.
        # Another drive's write result (including failure) must be preserved.
        for cached, hard, error, writes in [(0, 0, 0, 0), (1, 0, 0, 1),
                                             (1, 128, 0, 1), (1, 128, 1, 1)]:
            setup = f'''mov byte [{at('DISK')}],0
 mov byte [{at('DSK_LAST')}],{cached}
 mov byte [{at('DRVTYPE')+1}],{hard}
 mov word [7000h],0
'''
            checks = f'''pushf
 pop ax
 and ax,1
 cmp ax,{error}
 jne failed
 cmp word [7000h],{writes}
 jne failed
'''
            machine.run('FD_FLUSH', setup, checks,
                        patches={'WRSEC': 'inc word [7000h]\n'+('stc' if error else 'clc')+'\nret'})
        print(f'PASS: {variant}: 4 relogin cache cases (same drive, other floppy, hard disk, flush error)')
        if variant == 'pcbioexp':
            # Execute BDOS 13 through its real BIOS reset gateway. Stop at
            # relogin to observe cache state before any disk can be accessed.
            bdos = symbols(ROOT / 'bdosexp.sym')
            combined = bytearray(image)
            for (_, address), byte in image_map(ROOT / 'bdosexp.h86').items():
                combined[address] = byte
            reset = Machine(combined, combined, {**machine.names, **bdos})
            for cached, hard, dirty in [(0, 0, 255), (1, 0, 255),
                                         (0, 0, 0), (1, 0, 0),
                                         (2, 128, 255), (3, 128, 0),
                                         (4, 0, 255), (255, 0, 0)]:
                discard = cached < 4 and not hard
                setup = f'''mov byte [{at('DSK_LAST')}],{cached}
 mov byte [{at('DSK_DIRTY')}],{dirty}
 mov word [{at('DRVTYPE')}],0
 mov word [{at('DRVTYPE')}+2],8080h
 mov word [{bdos['LGDSKV']}],3
 mov word [{bdos['RODSKV']}],3
 mov byte [{bdos['CURDRV']}],0
 mov byte [{bdos['CURDSK']}],1
 mov word [7000h],0
 mov dx,1234h
 mov si,5678h
 mov di,9abch
 mov bp,0def0h
'''
                # Snapshot the state at SELDSK, not after the reset returns.
                select = f'''inc word [7000h]
 mov al,[{at('DSK_LAST')}]
 mov [7002h],al
 mov al,[{at('DSK_DIRTY')}]
 mov [7003h],al
 ret
'''
                checks = f'''cmp word [7000h],1
 jne failed
 cmp byte [7002h],{255 if discard else cached}
 jne failed
 cmp byte [7003h],{0 if discard else dirty}
 jne failed
 cmp word [{bdos['LGDSKV']}],0
 jne failed
 cmp word [{bdos['RODSKV']}],0
 jne failed
 cmp byte [{bdos['CURDSK']}],0
 jne failed
 cmp bx,0
 jne failed
 cmp dx,1234h
 jne failed
 cmp si,5678h
 jne failed
 cmp di,9abch
 jne failed
 cmp bp,0def0h
 jne failed
'''
                reset.run('MRSDSY', setup, checks,
                          patches={bdos['SELDSK']: select})
            print('PASS: EXP: 8 full-reset cases before relogin (floppy, hard disk, memory disk, invalid cache)')
        print(f'PASS: {variant}: {records} record/cache/CHS mappings across five formats')
    print('PASS: 10 format checks, 0 failures')


if __name__ == '__main__':
    main()
