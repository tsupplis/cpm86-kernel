"""Execute MBR policy/slot handling on an 8086; stub only the disk write."""
from itertools import permutations
from pathlib import Path
import struct
from check_capacity import Machine, symbols, eq

ROOT = Path(__file__).resolve().parent


def stores(at, data):
    assert len(data) % 2 == 0
    return ''.join(f'mov word [{at+i}],{int.from_bytes(data[i:i+2], "little")}\n'
                   for i in range(0, len(data), 2))


def main():
    raw = (ROOT/'hdmaint.cmd').read_bytes()
    n = int.from_bytes(raw[1:3], 'little')*16
    m = int.from_bytes(raw[10:12], 'little')*16
    code, data = raw[128:128+n], raw[128+n:128+n+m]
    dma = (m+15)&~15
    expected_at, calls = dma+512, dma+1024
    h = Machine(code, data+bytes(calls+2-m), symbols(ROOT/'hdmaint.sym'))
    S = h.s
    assert data[S('preserve_mbr')] == 0, 'Replacement must be the startup default'
    bootstrap = bytes((i*37+11)&255 for i in range(446))
    default = data[S('default_mbr'):S('default_mbr')+446]
    entries = []
    for kind, lba in [(4,17), (5,8209), (0xdb,16456), (0,0)]:
        entry = bytearray(16)
        if kind:
            entry[0] = 0x80 if kind == 4 else 0
            entry[1:8] = bytes([1,1,0,kind,3,17,100])
            struct.pack_into('<II', entry, 8, lba, 400)
        entries.append(bytes(entry))

    # All 24 slot permutations, on both disks and with both policies. Change
    # an active flag, delete CP/M, or fill an empty slot before writing.
    for order_index, order in enumerate(permutations(range(4))):
        for disk in (0,1):
            for preserve in (0,255):
                descriptor = S('first_disk')+disk*0x4a7
                original = bootstrap+b''.join(entries[i] for i in order)+b'\x55\xaa'
                operation = order_index % 3
                updated = list(entries)
                if operation == 0:
                    updated[0] = bytes([0])+updated[0][1:]
                    updated[1] = bytes([0x80])+updated[1][1:]
                elif operation == 1:
                    updated[2] = bytes(16)
                else:
                    updated[3] = bytes([0,0,1,200,7,3,17,201])+struct.pack('<II',30000,136)
                sorted_mbr = (bootstrap if preserve else default)+b''.join(updated)+b'\x55\xaa'
                expected = ((bootstrap+b''.join(updated[i] for i in order)+b'\x55\xaa')
                            if preserve else sorted_mbr)
                other_map = S('mbr_slots')+(1-disk)*4
                setup = stores(descriptor+0xa7, original)+stores(expected_at, expected)
                setup += f'''mov byte [{descriptor}],{disk}
 mov byte [{S('preserve_mbr')}],{preserve}
 mov word [{other_map}],0203h
 mov word [{other_map+2}],0001h
 mov ax,ds
 add ax,{dma//16}
 mov [{S('dma_segment')}],ax
'''
                # Slot map is computed by the real sorter, not supplied by test.
                bridge = f'''mov bx,{descriptor}
 call {S('sort_partitions')}
 call {S('select_second_disk' if disk else 'select_first_disk')}
'''
                if operation == 1:
                    bridge += f'call {S("delete_cpm_entry")}\n retf'
                elif operation == 0:
                    bridge += f'call {S("cycle_boot_partition")}\n call {S("write_mbr")}\n retf'
                else:
                    bridge += stores(S('partition_table'), b''.join(updated))
                    bridge += f'call {S("write_mbr")}\n retf'
                stub = f'''cmp bx,0
 jne bad
 cmp dx,{disk}
 jne bad
 mov ax,es
 cmp ax,[{S('dma_segment')}]
 jne bad
 inc byte [{calls}]
 xor ax,ax
 ret
bad:
 mov ax,4c01h
 int 21h
'''
                checks = f'''cmp al,0
 jne failed
 mov ax,ds
 mov es,ax
 mov si,{expected_at}
 mov di,{dma}
 mov cx,512
 cld
 repe cmpsb
 jne failed
'''+eq(calls,1,True)+eq(other_map,0x0203)+eq(other_map+2,0x0001)
                # Cache retains sorted working entries, including changed flags.
                for i in range(0,512,2):
                    checks += eq(descriptor+0xa7+i, int.from_bytes(sorted_mbr[i:i+2],'little'))
                mapping = bytes(order.index(i) for i in range(4)) if preserve else bytes(range(4))
                checks += eq(S('mbr_slots')+disk*4,int.from_bytes(mapping[:2],'little'))
                checks += eq(S('mbr_slots')+disk*4+2,int.from_bytes(mapping[2:],'little'))
                h.run('write_mbr',setup,checks,{'write_mbr_sectors':stub,
                      'boot_partition_menu_at_0b35':'ret'},bridge)

    # Both policies propagate write/read-back failures without updating cache.
    for preserve in (0,255):
        setup = f'''mov byte [{S('preserve_mbr')}],{preserve}
 mov word [{S('disk1_mbr')}],1234h
 mov word [{S('mbr_slots')}],0203h
 mov word [{S('mbr_slots')+2}],0001h
 mov ax,ds
 add ax,{dma//16}
 mov [{S('dma_segment')}],ax
'''
        checks = 'jnc failed\n cmp ax,55aah\n jne failed\n'
        checks += eq(S('disk1_mbr'),0x1234)+eq(S('mbr_slots'),0x0203)+eq(S('mbr_slots')+2,0x0001)
        h.run('write_mbr',setup,checks,{'write_mbr_sectors':'mov ax,55aah\n stc\n ret'})

    # Re-select after replacement, then preserve: keep the installed bootstrap,
    # active flags and new slot order, not the originally scanned disk state.
    descriptor = S('first_disk')
    order = (2,3,0,1)
    original = bootstrap+b''.join(entries[i] for i in order)+b'\x55\xaa'
    expected = default+b''.join(entries)+b'\x55\xaa'
    setup = stores(descriptor+0xa7,original)+stores(expected_at,expected)
    setup += f'mov ax,ds\n add ax,{dma//16}\n mov [{S("dma_segment")}],ax'
    bridge = f'''mov bx,{descriptor}
 call {S('sort_partitions')}
 call {S('select_first_disk')}
 call {S('write_mbr')}
 call {S('select_first_disk')}
 mov byte [{S('preserve_mbr')}],255
 call {S('write_mbr')}
 retf'''
    checks = f'''mov ax,ds
 mov es,ax
 mov si,{expected_at}
 mov di,{dma}
 mov cx,512
 cld
 repe cmpsb
 jne failed
'''
    h.run('write_mbr',setup,checks,{'write_mbr_sectors':'xor ax,ax\n ret'},bridge)
    print(f'PASS: {h.count} MBR policy cases; original slots, updates, caching and error propagation')


if __name__ == '__main__':
    main()
