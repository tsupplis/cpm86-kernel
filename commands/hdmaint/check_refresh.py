"""Execute display transitions and check the resulting 80-column screen."""
from pathlib import Path
from check_capacity import Machine, symbols

ROOT = Path(__file__).resolve().parent


def render(output):
    screen = [bytearray(b' '*80) for _ in range(25)]
    row = col = 0
    i = 0
    while i < len(output):
        ch = output[i]
        i += 1
        if ch == 27:
            cmd = output[i]
            i += 1
            if cmd == ord('Y'):
                row, col = output[i]-32, output[i+1]-32
                i += 2
            elif cmd == ord('A'): row = max(0,row-1)
            elif cmd == ord('B'): row = min(24,row+1)
            elif cmd == ord('C'): col = min(79,col+1)
            elif cmd == ord('D'): col = max(0,col-1)
            elif cmd == ord('K'): screen[row][col:] = b' '*(80-col)
            elif cmd not in b'rustmnzf': raise AssertionError(('escape',cmd))
        elif ch == 13: col = 0
        elif ch == 10: row = min(24,row+1)
        elif ch == 8:
            if col: col -= 1
            elif row: row, col = row-1,79
        else:
            screen[row][col] = ch
            col += 1
            if col == 80: col, row = 0,min(24,row+1)
    return screen


def main():
    raw = (ROOT/'hdmaint.cmd').read_bytes()
    n = int.from_bytes(raw[1:3],'little')*16
    m = int.from_bytes(raw[10:12],'little')*16
    code, data = raw[128:128+n], raw[128+n:128+n+m]
    count, buffer = len(data), len(data)+2
    h = Machine(code, data+bytes(8194), symbols(ROOT/'hdmaint.sym'))
    S = h.s
    sink = f"""push bx
 mov bx,[{count}]
 cmp bx,8192
 jae overflow
 mov [{buffer}+bx],al
 inc word [{count}]
 pop bx
 ret
overflow:
 mov ax,4c01h
 int 21h
"""
    def capture(streams, routine=None):
        bridge = ''.join(f'mov si,{S(name)}\n call {S("print_template")}\n' for name in streams)
        if routine: bridge += f'call {S(routine)}\n'
        bridge += 'retf'
        setup = f"""mov byte [{S('selected_has_cpm')}],255
 mov byte [{S('can_create')}],255
 mov byte [{S('selected_letter')}],67
 mov byte [{S('output_enabled')}],255
 mov bp,sp
 cld
"""
        checks = f"""cmp sp,bp
 jne failed
 mov bx,1
 mov cx,[{count}]
 mov dx,{buffer}
 mov ah,40h
 int 21h
"""
        return h.run('print_template',setup,checks,{'console_out':sink},bridge)

    # Four summary rows precede the first function-key box. Keep all of them.
    summary = b''.join(bytes([27,89,32+r,34])+b'KEEP PARTITION' for r in range(4,8))
    warning = render(summary+capture(['partition_screen','mbr_policy_screen'],'warn_delete'))
    assert warning[8][1:79] == b' '*78, 'Old F2 top border survives replacement warning'
    assert all(warning[r][2:16] == b'KEEP PARTITION' for r in range(4,8))
    assert b'Do you really want to proceed?' in warning[15]

    for base, progress, abort, resume in [
        ('create_screen','test_progress','create_abort_screen','resume_create'),
        ('verify_screen',None,'verify_abort_screen','resume_verify'),
    ]:
        streams = [base]+([progress] if progress else [])
        before = render(capture(streams))
        after = render(capture(streams+[abort],resume))
        assert after == before, f'{resume}: confirmation text or key-box remnant remains'
    print('PASS: replacement warning and creation/verification resume screens; no stale boxes')


if __name__ == '__main__':
    main()
