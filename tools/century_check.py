#!/usr/bin/env python3
"""Execute resident century rendering without changing the software clock."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'commands/hdmaint'))
from check_capacity import Machine, symbols


def check():
    for kernel, bios in (('cpm', 'pcbios'), ('cpmexp', 'pcbioexp')):
        raw = (ROOT / (kernel + '.sys')).read_bytes()[128:]
        machine = Machine(raw, raw, symbols(ROOT / (bios + '.sym')))
        s = machine.s
        assert s('DSPCENT') == s('BIOS_DATA_RSV')
        assert s('DSPEND') <= s('BIOS_DATA_RSV') + 75
        hook = s('PRNBOS1')
        assert raw[hook] == 0xe8
        assert (hook + 3 + int.from_bytes(raw[hook+1:hook+3], 'little')) & 65535 == s('DSPCENT')
        cases = []
        # All short years, both characters, equal/unequal cache comparisons.
        # BCENT deliberately disagrees: rendering must neither use nor alter it.
        for year in range(100):
            ascii_year = int.from_bytes(f'{year:02}'.encode(), 'little')
            for digit, character in enumerate('20' if year < 80 else '19'):
                for equal in (False, True):
                    cases.append(f'''
 mov word [{s('AYEAR')}],{ascii_year}
 mov word [{s('BYEAR')}],{ascii_year}
 mov word [{s('BCENT')}],3234h
 mov byte [{s('BOSLINE')}],{ord(character) if equal else 0}
 mov si,{s('BCENT') + digit}
 mov di,{s('BOSLINE')}
 mov bx,1234h
 mov ah,56h
 call {s('DSPCENT')}
 {'jne' if equal else 'je'} bad
 cmp ax,{0x5600 + ord(character)}
 jne bad
 cmp bx,1234h
 jne bad
 cmp si,{s('BCENT') + digit + 1}
 jne bad
 cmp di,{s('BOSLINE')}
 jne bad
 cmp word [{s('BCENT')}],3234h
 jne bad
 cmp word [{s('AYEAR')}],{ascii_year}
 jne bad
 cmp word [{s('BYEAR')}],{ascii_year}
 jne bad
''')
        # Bound generated code size; each batch still exercises built machine code.
        for start in range(0, len(cases), 40):
            bridge = ''.join(cases[start:start+40]) + '\nretf\nbad: mov ax,4c01h\nint 21h\n'
            machine.run('DSPCENT', bridge=bridge)
        # Ordinary status text must keep its original character and flags.
        machine.run('DSPCENT',
                    f'mov si,{s("BYEAR")}\nmov di,{s("BYEAR")}\nmov word [si],3132h',
                    f'jne failed\ncmp al,32h\njne failed\ncmp si,{s("BYEAR")+1}\njne failed')
        print(f'PASS: {kernel}: 400 century cases, ordinary text, hook and resident bounds')


if __name__ == '__main__':
    check()
