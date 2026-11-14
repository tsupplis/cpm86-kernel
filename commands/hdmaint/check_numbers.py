"""Execute cylinder display/input and upper-bound cases; no disk I/O."""
from pathlib import Path
from check_capacity import Machine, symbols, eq


def main():
    root = Path(__file__).resolve().parent
    raw = (root / 'hdmaint.cmd').read_bytes()
    n = int.from_bytes(raw[1:3], 'little') * 16
    m = int.from_bytes(raw[10:12], 'little') * 16
    data = raw[128+n:128+n+m]
    h = Machine(raw[128:128+n], data + bytes(1024), symbols(root / 'hdmaint.sym'))
    S = h.s
    count, output, keys, consumed, bells = [len(data)+i for i in (0, 2, 514, 546, 548)]
    sink = f'''push bx
 mov bx,[{count}]
 cmp bx,512
 jae overflow
 mov [{output}+bx],al
 inc word [{count}]
 cmp al,7
 jne done
 inc word [{bells}]
done:
 pop bx
 ret
overflow:
 mov ax,4c01h
 int 21h
'''
    for value in (0, 10, 66, 999, 1000, 1014, 1023, 1024, 10000, 16128, 65535):
        for width in (3, 4, 5):
            expected = f'{value % (10**width):0{width}}'.encode()
            checks = eq(count, width) + eq(S('disk_cylinders'), value)
            checks += ''.join(eq(output+i, c, True) for i, c in enumerate(expected))
            h.run(f'print_number{width}',
                  f'mov ax,{value}\nmov word [{S("disk_cylinders")}],{value}',
                  checks, {'console_out': sink})
    cases = [('E', 65535, 0), ('\rE', 65535, 1), ('0\r', 0, 0),
             ('9\r', 9, 0), ('10\r', 10, 0), ('66\r', 66, 0),
             ('066\r', 66, 0), ('999\r', 999, 0), ('1000\r', 1000, 0),
             ('1014\r', 1014, 0), ('1023\r', 1023, 0), ('1024\r', 1024, 0),
             ('9999\r', 9999, 0), ('1000E', 1000, 0), ('66E', 66, 0),
             ('10000\r', 1000, 1), ('1x0\r', 10, 1)]
    for typed, value, beep_count in cases:
        setup = ''.join(f'mov byte [{keys+i}],{c}\n' for i, c in enumerate(typed.encode()))
        reader = f'''push bx
 mov bx,[{consumed}]
 cmp bx,{len(typed)}
 jae exhausted
 mov al,[{keys}+bx]
 inc word [{consumed}]
 pop bx
 ret
exhausted:
 mov ax,4c01h
 int 21h
'''
        h.run('read_number', setup,
              f'cmp ax,{value}\njne failed\n' + eq(consumed, len(typed)) + eq(bells, beep_count),
              {'flush_keys': 'ret', 'read_key': reader, 'console_out': sink})
    # The real caller must still enforce the ten-cylinder minimum and disk end.
    for value, expected in ((999, 999), (1000, 1000), (1014, 1014),
                            (1015, 980), (1023, 980), (1024, 980), (9999, 980)):
        setup = f'''mov ax,{value}
 mov word [{S('partition_start')}],980
 mov word [{S('free_extents')}],980
 mov word [{S('free_extents')+2}],1023
'''
        setup += ''.join(f'mov word [{S("free_extents")+i}],65535\n' for i in range(4, 20, 2))
        h.run('edit_start_cylinder_at_0513', setup, eq(S('partition_start'), expected),
              {'edit_start_cylinder': 'retf', 'beep': 'ret'},
              f'push ax\njmp {S("edit_start_cylinder_at_0513")}')
    # Exercise the serialized upper CHS bits and the full LBA fields together.
    entry = S('selected_disk') + 0x265
    setup = f'''mov word [{S('cpm_partition_offset')}],265h
 mov word [{S('partition_start')}],1000
 mov word [{S('partition_end')}],1023
 mov word [{S('partition_cylinders_count')}],24
 mov word [{S('sectors_per_cylinder')}],1008
 mov byte [{S('physical_spt')}],63
 mov byte [{S('last_head')}],15
'''
    checks = eq(entry+8, 1008000 & 65535) + eq(entry+10, 1008000 >> 16)
    checks += eq(entry+12, 24192) + eq(entry+14, 0)
    for offset, value in ((1, 0), (2, 193), (3, 232), (5, 15), (6, 255), (7, 255)):
        checks += eq(entry+offset, value, True)
    h.run('encode_partition', setup, checks)
    print(f'PASS: {h.count} numeric display/input, cylinder-bound and CHS/LBA cases')


if __name__ == '__main__':
    main()
