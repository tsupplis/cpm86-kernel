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
        print(f'PASS: {variant}: {records} record/cache/CHS mappings across five formats')
    print('PASS: 10 format checks, 0 failures')


if __name__ == '__main__':
    main()
