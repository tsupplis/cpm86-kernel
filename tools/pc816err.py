#!/usr/bin/env python3
"""Execute the built EXP loader with injected BDOS results; never run COM code."""
from pathlib import Path
import sys
import subprocess
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'commands/hdmaint'))
from check_capacity import Machine, symbols


def check():
    build = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    raw = (build/'cpmexp.sys').read_bytes()[128:]
    names = symbols(build/'pcbioexp.sym')
    names.update(symbols(build/'ccpexp.sym'))
    m = Machine(raw, b'', names)
    S = m.s
    # Test-owned scratch, beyond the complete kernel image, inside its segment.
    state = 0xe000
    entered, owned, reads, closes, dma, dmaseg, message = [state+2*i for i in range(7)]
    cases = [
        ('empty', 0, 0, -1, False, False, False, 1),
        ('one record', 1, 1, -1, False, False, True, 1),
        ('500 records', 500, 500, -1, False, False, True, 1),
        ('exact maximum', 501, 501, -1, False, False, True, 1),
        ('one record over', 502, 502, -1, False, False, False, 1),
        ('24-bit oversized count', 65536, 1, -1, False, False, False, 1),
        ('mid-read failure', 8, 8, 3, False, False, False, 1),
        ('premature EOF', 8, 3, -1, False, False, False, 1),
        ('close failure', 1, 1, -1, True, False, False, 1),
        ('allocation failure', 1, 1, -1, False, True, False, 1),
        ('repeated failed replacement', 8, 8, 3, False, False, False, 8),
    ]
    failures = []
    for label, size, available, badread, badclose, nomem, success, repeats in cases:
        patches = {
            'CCPLOP': 'ret',
            'SLCRDR': 'ret',
            'ARGS816': 'ret',
            # Stop before BRKEM, after all loading and closing checks.
            'VECT816': f'mov word [{entered}],1\npop ax\nret',
        }
        bridge = f'''push ds
 push es
 push cs
 pop ds
 xor ax,ax
 mov es,ax
 mov word [es:380h],bdos
 mov [es:382h],cs
 mov ax,cs
 add ax,1000h
 mov word [{S('mem816')}],ax
 ; Begin with a retained old bank: replacement must invalidate it.
 mov byte [{S('bank816')}],1
 mov byte [{S('keep816')}],1
 mov word [{owned}],1
 mov bp,{repeats}
again:
 mov word [{entered}],0
 mov word [{reads}],0
 mov word [{closes}],0
 mov word [{message}],0
 call {S('LOAD816')}
 cmp word [{entered}],{int(success)}
 jne bad
 cmp word [{closes}],0
 je bad
 cmp byte [{S('vec816')}],0
 jne bad
'''
        if not success:
            bridge += f'''cmp word [{owned}],0
 jne bad
 cmp byte [{S('bank816')}],0
 jne bad
 cmp byte [{S('keep816')}],0
 jne bad
 cmp word [{dma}],80h
 jne bad
 mov ax,cs
 cmp [{dmaseg}],ax
 jne bad
 cmp word [{message}],0
 je bad
'''
        bridge += f'''dec bp
 jnz again
 pop es
 pop ds
 retf
bad:
 mov ax,4c01h
 int 21h
bdos:
 cmp cl,55
 je allocate
 cmp cl,57
 je release
 cmp cl,35
 je filesize
 cmp cl,51
 je dma_segment
 cmp cl,26
 je dma_offset
 cmp cl,20
 je read
 cmp cl,16
 je close
 cmp cl,9
 je print
 jmp bad
allocate:
 cmp word [{owned}],0
 jne bad
 mov al,{int(nomem)}
 or al,al
 jnz done
 mov word [{owned}],1
 mov ax,cs
 add ax,1000h
 mov [{S('mem816')}],ax
 xor ax,ax
 jmp done
release:
 cmp word [{owned}],1
 jne bad
 mov word [{owned}],0
 xor ax,ax
 jmp done
filesize:
 mov word [{S('WKFCB')+33}],{size & 65535}
 mov byte [{S('WKFCB')+35}],{size >> 16}
 xor ax,ax
 jmp done
dma_segment:
 mov [{dmaseg}],dx
 jmp done
dma_offset:
 mov [{dma}],dx
 jmp done
read:
 cmp word [{owned}],1
 jne bad
 cmp word [{reads}],{badread & 65535}
 je readfail
 cmp word [{reads}],{available}
 jae eof
 ; No successful read may reach reserved bridge storage.
 cmp word [{dma}],0fb00h
 ja bad
 inc word [{reads}]
 xor ax,ax
 jmp done
readfail:
 mov al,2
 jmp done
eof:
 mov al,1
 jmp done
close:
 inc word [{closes}]
 mov al,{255 if badclose else 0}
 jmp done
print:
 mov [{message}],dx
done:
 iret
'''
        try:
            m.run('LOAD816', patches=patches, bridge=bridge)
            print('PASS:', label, flush=True)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(exc.stderr.decode()) from exc
        except AssertionError:
            failures.append(label)
            print('FAIL:', label, flush=True)
    # Execute SAVE's write/close paths with errors; retain the bank for retry.
    for label, badwrite, badclose, expected in [
        ('SAVE write failure', True, False, 'writeerr816'),
        ('SAVE close failure', False, True, 'closeerr816'),
        ('SAVE success', False, False, 'saved816'),
    ]:
        bridge = f'''push ds
 push es
 push cs
 pop ds
 xor ax,ax
 mov es,ax
 mov word [es:380h],bdos
 mov [es:382h],cs
 mov byte [{S('bank816')}],1
 mov byte [{S('keep816')}],1
 mov word [{S('saverecs816')}],1
 mov word [{S('saveoff816')}],100h
 mov word [{reads}],0
 mov word [{closes}],0
 mov word [{owned}],0
 call {S('SAVEWRITE816')}
 cmp word [{reads}],1
 jne bad
 cmp word [{closes}],1
 jne bad
 cmp word [{owned}],{int(badwrite or badclose)}
 jne bad
 cmp word [{message}],{S(expected)}
 jne bad
 cmp byte [{S('bank816')}],1
 jne bad
 cmp word [{dma}],80h
 jne bad
 mov ax,cs
 cmp [{dmaseg}],ax
 jne bad
 pop es
 pop ds
 retf
bad:
 mov ax,4c01h
 int 21h
bdos:
 cmp cl,26
 je dma_offset
 cmp cl,51
 je dma_segment
 cmp cl,21
 je write_record
 cmp cl,16
 je close_file
 cmp cl,19
 je delete_file
 cmp cl,9
 je print_message
 jmp bad
dma_offset:
 mov [{dma}],dx
 iret
dma_segment:
 mov [{dmaseg}],dx
 iret
write_record:
 inc word [{reads}]
 mov al,{int(badwrite)}
 iret
close_file:
 inc word [{closes}]
 mov al,{255 if badclose else 0}
 iret
delete_file:
 inc word [{owned}]
 xor ax,ax
 iret
print_message:
 mov [{message}],dx
 iret
'''
        m.run('SAVEWRITE816', patches={'CCPLOP': 'ret', 'SLCRDR': 'ret'}, bridge=bridge)
        print('PASS:', label, flush=True)
    print('3/3 injected SAVE cases passed')
    print(f'{len(cases)-len(failures)}/{len(cases)} injected loader cases passed')
    if failures:
        raise SystemExit(1)

if __name__ == '__main__':
    check()
