#!/usr/bin/env python3
"""Execute the built EXP Function 10 editor with scripted console boundaries.

The production editor and BDOS echo logic run unchanged. Only device input,
output and status are replaced; no real disk or console is used.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'commands/hdmaint'))
from check_capacity import Machine, symbols


def check():
    raw = (ROOT / 'cpmexp.sys').read_bytes()[128:]
    names = symbols(ROOT / 'bdosexp.sym')
    names.update(symbols(ROOT / 'pcbioexp.sym'))
    # Reserved recall bytes are not necessarily emitted in the CMD file.
    # Keep test trampolines beyond all resident storage.
    raw = raw.ljust(names["ENDEDIT"], b"\0")
    m = Machine(raw, raw, names)
    s = m.s
    buf, seq, cursor = 0x7000, 0x7200, 0x7400
    patches = {
        'CONINC': f'mov si,[{cursor}]\nmov al,[si]\ninc si\nmov [{cursor}],si\nret',
        'CONSTS': 'xor ax,ax\nret',
        'BCONOT': 'ret',
        'BLIST': 'ret',
    }
    cases = [
        ('append', b'hello\r', b'hello', 20),
        ('insert', b'ac\x01b\r', b'abc', 20),
        ('suffix acceptance', b'abcd\x01\x01\r', b'abcd', 20),
        ('backspace', b'abc\x08\r', b'ab', 20),
        ('delete', b'abc\x01\x07\r', b'ab', 20),
        ('home/end', b'bc\x80a\x81d\r', b'abcd', 20),
        ('ctrl B', b'bc\x02a\x02\x02d\r', b'abcd', 20),
        ('kill suffix', b'abcd\x01\x01\x0b\r', b'ab', 20),
        ('kill prefix', b'abcd\x01\x01\x18\r', b'cd', 20),
        ('cancel', b'abc\x15z\r', b'z', 20),
        ('retype', b'ab\x12c\r', b'abc', 20),
        ('continue', b'ab\x05c\r', b'abc', 20),
        ('tabs', b'a\tb\x01x\r', b'a\txb', 20),
        ('printer toggle', b'a\x10b\x10\r', b'ab', 20),
        ('empty', b'\r', b'', 20),
        ('zero capacity', b'', b'', 0),
        ('full append', b'abc', b'abc', 3),
        ('full middle', b'ac\x01bZ\r', b'abc', 3),
        ('left boundary', b'\x01\x08a\r', b'a', 20),
        ('right boundary', b'a\x06\x07\r', b'a', 20),
        ('255 bytes', b'x'*255, b'x'*255, 255),
    ]
    for name, keys, expected, maximum in cases:
        setup = f"""mov word [{s('SYS_CONI')}],1
mov word [{s('SYS_CONO')}],2
mov byte [{s('WRAPFLAG')}],255
mov word [{s('STATE')}],{s('VIDNORM')}
mov word [{s('INPARA')}],{buf}
mov [{s('INDSEG')}],ds
mov byte [{buf}],{maximum}
mov byte [{buf+maximum+2}],0a5h
mov word [{cursor}],{seq}
"""
        for offset, value in enumerate(keys):
            setup += f'mov byte [{seq+offset}],{value}\n'
        checks = f'cmp byte [{buf+1}],{len(expected)}\njne failed\n'
        checks += f'cmp byte [{buf+maximum+2}],0a5h\njne failed\n'
        checks += f'push es\nmov ax,[cs:target+2]\nmov es,ax\ncmp byte [es:{s("le_active")}],0\njne failed\npop es\n'
        for offset, value in enumerate(expected):
            checks += f'cmp byte [{buf+2+offset}],{value}\njne failed\n'
        m.run('MRDCBF', setup, checks, patches=patches)
        print('PASS:', name)
    # Real save followed by recall, including truncation and blank/cancel policy.
    for name, first, second, limit, expected in (
        ('recall', b'hello\r', b'\x17\r', 20, b'hello'),
        ('recall truncation', b'hello\r', b'\x17Z\r', 3, b'hel'),
        ('recall cancel', b'hello\r', b'x\x15\x17\r', 20, b'hello'),
        ('recall cap', b'x'*200, b'\x17\r', 255, b'x'*127),
    ):
        keys = first + second
        setup = f"""mov word [{s('SYS_CONI')}],1
mov word [{s('SYS_CONO')}],2
mov byte [{s('WRAPFLAG')}],255
mov word [{s('STATE')}],{s('VIDNORM')}
mov word [{s('INPARA')}],{buf}
mov [{s('INDSEG')}],ds
mov byte [{buf}],{200 if name == 'recall cap' else 20}
mov word [{cursor}],{seq}
"""
        for offset, value in enumerate(keys):
            setup += f'mov byte [{seq+offset}],{value}\n'
        bridge = f'call {s("MRDCBF")}\nmov byte [{buf}],{limit}\ncall {s("MRDCBF")}\nretf'
        checks = f'cmp byte [{buf+1}],{len(expected)}\njne failed\n'
        for offset, value in enumerate(expected):
            checks += f'cmp byte [{buf+2+offset}],{value}\njne failed\n'
        m.run('MRDCBF', setup, checks, patches=patches, bridge=bridge)
        print('PASS:', name)
    # Unsupported output routing must delegate without activating the editor.
    for output in (4, 6):
        m.run('MRDCBF', f'mov word [{s("SYS_CONI")}],1\nmov word [{s("SYS_CONO")}],{output}',
              'cmp ax,1234h\njne failed', patches={'RDCNBF': 'mov ax,1234h\nret'})
    # Abort cleanup must still invoke the original disk-reset routine.
    m.run('LE_ABORT_GATE', patches={'MRSDSY': 'mov ax,1234h\nret'},
          bridge=f"""mov byte [cs:{s('le_active')}],1
call {s('LE_ABORT_GATE')}
cmp byte [cs:{s('le_active')}],0
jne bad
cmp ax,1234h
jne bad
retf
bad: mov ax,4c01h
int 21h
""")
    print(f'PASS: {m.count} built-editor cases')


if __name__ == '__main__':
    check()
