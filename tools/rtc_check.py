#!/usr/bin/env python3
"""Execute the built cold-start RTC date path with simulated BIOS replies."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "commands/hdmaint"))
from check_capacity import Machine, symbols


def check():
    # BCD century/year/month/day, carry, expected ASCII date (None = fallback).
    cases = [
        (0x20, 0x26, 0x11, 0x13, False, "11/13/26", "20"),
        (0x19, 0x99, 0x12, 0x31, False, "12/31/99", "19"),
        (0x20, 0x24, 0x02, 0x29, False, "02/29/24", "20"),
        (0x20, 0x00, 0x02, 0x29, False, "02/29/00", "20"),
        (0x20, 0x26, 0x11, 0x13, True, None, "20"),
        (0xff, 0xff, 0xff, 0xff, False, None, "20"), # XT no-op
        (0xff, 0xff, 0xff, 0xff, True, None, "20"),
        (0x20, 0x26, 0x02, 0x29, False, None, "20"),
        (0x19, 0x00, 0x02, 0x29, False, None, "20"),
        (0x21, 0x00, 0x02, 0x29, False, None, "20"),
        (0x20, 0x26, 0x04, 0x31, False, None, "20"),
    ]
    for field, values in enumerate(([0, 0x18, 0x2a, 0xa0], [0x1a, 0xa0],
                                    [0, 0x13, 0x1a, 0xa0], [0, 0x32, 0x1a, 0xa0])):
        for value in values:
            reply = [0x20, 0x26, 0x11, 0x13]
            reply[field] = value
            cases.append((*reply, False, None, "20"))
    for kernel, bios in (("cpm", "pcbios"), ("cpmexp", "pcbioexp")):
        raw = (ROOT / (kernel + ".sys")).read_bytes()[128:]
        names = symbols(ROOT / (bios + ".sym"))
        m = Machine(raw, raw, names)
        S = m.s
        assert S("INIT_RTC") == 0x4400
        assert S("RTC_END") < 0x4780 # Stay inside pre-existing cold-start padding
        assert raw[S("RTC_INT"):S("RTC_INT")+3] == bytes.fromhex("cd1a90")
        # Exactly one same-size cold-start call; the original reset remains resident.
        hook = 0x3CDF
        assert raw[hook] == 0xe8
        assert (hook + 3 + int.from_bytes(raw[hook+1:hook+3], "little")) & 65535 == S("INIT_RTC")
        for century, year, month, day, carry, expected, expected_century in cases:
            fallback = "08/01/83,00:00:00"
            expected = (expected or fallback[:8]) + fallback[8:]
            setup = ""
            checks = ""
            for address, initial, result in ((S("AMONTH"), fallback, expected),
                                             (S("BCENT"), "20", expected_century)):
                for i, byte in enumerate(initial.encode()):
                    setup += f" mov byte [{address+i}],{byte}\n"
                for i, byte in enumerate(result.encode()):
                    checks += f" cmp byte [{address+i}],{byte}\n jne bad\n"
            # Verify the BIOS call contract and clobber registers as a hostile BIOS might.
            stub = f""" cmp ah,4
 jne biosbad
 cmp cx,0ffffh
 jne biosbad
 cmp dx,0ffffh
 jne biosbad
 jc biosbad
 mov cx,{century*256+year}
 mov dx,{month*256+day}
 mov bx,9876h
 mov si,bx
 mov di,bx
 mov es,bx
 mov ds,bx
 {"stc" if carry else "clc"}
 mov ax,{S("RTC_INT")+3}
 push ax
 ret
biosbad:
 mov ax,4c01h
 int 21h
"""
            bridge = f"""push ds
 push es
 push cs
 pop ds
 push cs
 pop es
{setup}
 mov ax,1234h
 mov bx,2345h
 mov cx,3456h
 mov dx,4567h
 mov si,5678h
 mov di,6789h
 stc
 std
 call {S("INIT_RTC")}
 jnc bad
 pushf
 pop bp
 test bp,400h
 jz bad
 cld
 cmp ax,1234h
 jne bad
 cmp bx,2345h
 jne bad
 cmp cx,3456h
 jne bad
 cmp dx,4567h
 jne bad
 cmp si,5678h
 jne bad
 cmp di,6789h
 jne bad
 mov ax,ds
 mov bx,cs
 cmp ax,bx
 jne bad
 mov ax,es
 cmp ax,bx
 jne bad
{checks}
 pop es
 pop ds
 retf
bad:
 mov ax,4c01h
 int 21h
"""
            m.run("INIT_RTC", patches={S("RTC_INT"): stub, "RESETIO": "ret"}, bridge=bridge)
        print(f"PASS: {kernel}: {m.count} RTC dates/fallbacks; registers, flags and time preserved")


if __name__ == "__main__":
    check()
