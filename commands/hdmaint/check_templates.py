"""Audit and execute the maintained HDMAINT display streams, without disk I/O."""
from pathlib import Path
import argparse
import re
import struct
from check_capacity import Machine, symbols, key

ROOT = Path(__file__).resolve().parent


def check(execute_only=False):
    source = (ROOT / 'hdmaint.a86').read_text()
    names = symbols(ROOT / 'hdmaint.sym')
    raw = (ROOT / 'hdmaint.cmd').read_bytes()
    code_size = int.from_bytes(raw[1:3], 'little') * 16
    data_size = int.from_bytes(raw[10:12], 'little') * 16
    code = raw[128:128 + code_size]
    data = raw[128 + code_size:128 + code_size + data_size]
    address = lambda name: names[key(name)]
    roots = sorted(set(re.findall(r'mov\s+si,offset\s+(\w+)\s*\n\s*call\s+print_template', source)))
    callbacks = {address(n): (n, size) for n, size in {
        'print_template': 0, 'template_number3': 2, 'template_number4': 2, 'template_number5': 2, 'template_character': 2,
        'template_decimal': 2, 'template_position': 2, 'template_key_caption': 3,
        'template_if_equal': 3, 'template_if_not_equal': 3,
        'template_clear_rows': 1, 'blink_on': 0, 'blink_off': 0,
        'reverse_on': 0, 'reverse_off': 0, 'clear_line': 0,
        'frame_down': 0, 'frame_up': 0, 'cursor_on': 0, 'cursor_off': 0,
    }.items()}
    # Listing proves each parsed callback word was emitted symbolically.
    symbolic = {int(m[1], 16): key(m[2]) for m in re.finditer(
        r'^\s*([0-9A-F]{4})\s+[0-9A-F]{4}\s+dw\s+offset\s+(\w+)',
        (ROOT / 'hdmaint.lst').read_text(), re.M | re.I)}
    seen = set()

    def stream(at, depth=0):
        assert depth < 20, 'Recursive display stream'
        while True:
            assert at < len(data), 'Unterminated display stream'
            token = data[at]
            at += 1
            if not token:
                return at
            if token != 255:
                continue
            callback = struct.unpack_from('<H', data, at)[0]
            assert callback in callbacks, f'Invalid display callback {callback:04X}h at DATA {at:04X}h'
            name, size = callbacks[callback]
            assert symbolic.get(at) == key(name), f'Non-symbolic callback at DATA {at:04X}h'
            seen.add(at)
            at += 2
            if name in ('template_number3', 'template_number4', 'template_number5', 'template_character', 'template_decimal',
                        'template_if_equal', 'template_if_not_equal'):
                pointer = struct.unpack_from('<H', data, at)[0]
                assert pointer < len(data), f'Invalid DATA pointer at {at:04X}h'
            at += size
            if name in ('print_template', 'template_if_equal', 'template_if_not_equal'):
                at = stream(at, depth + 1)

    if not execute_only:
        for root in roots:
            stream(address(root))
        print(f'PASS: {len(roots)} display roots; {len(seen)} symbolic callback sites')

    # Execute the real interpreter and callbacks. Only the final console sink
    # is replaced; its buffer is outside the program's original DATA group.
    count_at = len(data)
    output_at = count_at + 2
    machine = Machine(code, data + bytes(8194), names)
    sink = f'''cmp byte [{address('output_enabled')}],0
 je done
 push bx
 mov bx,[{count_at}]
 cmp bx,8192
 jae overflow
 mov [{output_at}+bx],al
 inc word [{count_at}]
 pop bx
done:
 ret
overflow:
 mov ax,4c01h
 int 21h
'''
    cases = [('create_progress', b'Creating CP/M volume'),
             ('create_complete', b'Creation of CP/M volume complete'),
             ('options_screen', b'verify after writes'),
             ('verify_screen', b'Scanning cylinder '),
             ('verify_complete', b'Verify complete       '),
             ('mbr_policy_screen', b'MBR boot code: ')]
    for root, text in cases:
        for verify in (0, 255):
            if root == 'mbr_policy_screen':
                text = b'MBR boot code: '+(
                    b'replace\x1bu/\x1brpreserve\x1bu' if verify else
                    b'\x1brreplace\x1bu/preserve\x1bu')
            setup = f'''mov si,{address(root)}
 mov byte [{address('output_enabled')}],255
 mov byte [{address('verify_writes')}],{verify}
 mov byte [{address('preserve_mbr')}],{verify}
 mov byte [{address('creating_volume')}],255
 mov byte [{address('directory_expanded')}],0
 mov word [{address('directory_entries')}],512
 mov word [{address('maximum_directory_entries')}],1024
 mov bp,sp
 cld
'''
            checks = f'''cmp sp,bp
 jne failed
 mov si,{output_at}
 mov cx,[{count_at}]
 sub cx,{len(text)-1}
 jbe failed
search:
'''
            for i, byte in enumerate(text):
                checks += f' cmp byte [si+{i}],{byte}\n jne next_byte\n'
            checks += ''' jmp found
next_byte:
 inc si
 dec cx
 jz failed
 jmp search
found:
'''
            machine.run('print_template', setup, checks, {'console_out': sink})
    print(f'PASS: {machine.count} affected-screen executions; text and stack return checked')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute-only', action='store_true', help='Reproduce failures without the static audit')
    check(p.parse_args().execute_only)
