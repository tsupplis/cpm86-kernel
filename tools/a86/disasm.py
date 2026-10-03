"""ndisasm driver and the RASM-86 source renderer."""

import re
import subprocess

from .text import lbl, num


BRANCH = {'jmp', 'jmps', 'call', 'loop', 'loope', 'loopne', 'loopz', 'loopnz',
          'ja', 'jae', 'jb', 'jbe', 'jc', 'jcxz', 'je', 'jg', 'jge', 'jl',
          'jle', 'jna', 'jnae', 'jnb', 'jnbe', 'jnc', 'jne', 'jng', 'jnge',
          'jnl', 'jnle', 'jno', 'jnp', 'jns', 'jnz', 'jo', 'jp', 'jpe', 'jpo',
          'js', 'jz'}

# Registers that hold addresses - an immediate loaded into one of these is
# probably a variable address worth naming.
PTRREG = {'bx', 'si', 'di', 'bp'}

# ndisasm spellings RASM-86 does not accept, as (mnemonic, operands).
# RASM-86 insists XLAT name a register even though the opcode has no operand.
MNEMONIC = {'xlatb': ('xlat', 'bx')}

# Address of the `data:` label, overridable with a `data_org equ ...` line.


def disasm(binf, start, end, base=0):
    """Disassemble [start,end).  `base` is the address of file offset 0."""
    raw = subprocess.run(
        ['ndisasm', '-b', '16', '-o', hex(start), '-e', hex(start - base), binf],
        capture_output=True, text=True).stdout
    out = []
    for ln in raw.splitlines():
        m = re.match(r'^([0-9A-F]{8})\s+([0-9A-F]+)\s+(.*)$', ln)
        if not m:
            continue
        addr = int(m.group(1), 16)
        if addr >= end:
            break
        out.append((addr, m.group(2), m.group(3)))
    return out


class Converter:
    def __init__(self, labels, equates, lo, hi):
        self.labels, self.eq, self.lo, self.hi = labels, equates, lo, hi

    def target(self, v):
        return lbl(v) if v in self.labels else num(v)

    def name_or_num(self, v):
        return self.eq.get(v) or num(v)

    def mem(self, inner):
        inner = inner.strip()
        seg = ''
        m = re.match(r'^(\w+):(.*)$', inner)
        if m and m.group(1) in ('es', 'cs', 'ss', 'ds'):
            seg, inner = m.group(1) + ':', m.group(2)
        m = re.match(r'^([a-z]{2})\+([a-z]{2})\+0x([0-9a-f]+)$', inner)
        if m:
            return '%s%s[%s][%s]' % (seg, self.name_or_num(int(m.group(3), 16)),
                                     m.group(1), m.group(2))
        m = re.match(r'^([a-z]{2})\+0x([0-9a-f]+)$', inner)
        if m:
            return '%s%s[%s]' % (seg, self.name_or_num(int(m.group(2), 16)),
                                 m.group(1))
        m = re.match(r'^0x([0-9a-f]+)$', inner)
        if m:
            return '%s.%s' % (seg, self.name_or_num(int(m.group(1), 16)))
        m = re.match(r'^([a-z]{2})\+([a-z]{2})$', inner)
        if m:
            if seg:                 # RASM-86 takes es:[bx+si], not es:[bx][si]
                return '%s[%s+%s]' % (seg, m.group(1), m.group(2))
            return '[%s][%s]' % (m.group(1), m.group(2))
        return '%s[%s]' % (seg, inner)

    def line(self, hexb, text):
        parts = text.split(None, 1)
        mn, ops = parts[0], (parts[1] if len(parts) > 1 else '')
        # EB is a short jump; DRI spells it jmps and plain jmp always emits E9.
        if mn == 'jmp' and hexb[:2].lower() == 'eb':
            mn = 'jmps'
        if mn in MNEMONIC:
            mn, ops = MNEMONIC[mn]
        ops = re.sub(r'\b(word|byte)\s+near\s+\[', r'\1 ptr [', ops)
        if mn in ('les', 'lds'):    # a far pointer: dword, and RASM-86 wants it
            ops = re.sub(r'\bword\s+\[', 'dword ptr [', ops)  # typed explicitly
        ops = re.sub(r'\b(word|byte)\s+\[', r'\1 ptr [', ops)
        if mn == 'int':
            ops = ops.replace('byte ', '')
        ops = re.sub(r'\[([^\]]+)\]', lambda m: self.mem(m.group(1)), ops)
        if mn in BRANCH:
            ops = re.sub(r'0x([0-9a-f]+)',
                         lambda m: self.target(int(m.group(1), 16)), ops)
        else:
            # Name an immediate only when it is loaded into a pointer register.
            m = re.match(r'^(%s),0x([0-9a-f]+)$' % '|'.join(PTRREG), ops)
            if m:
                ops = '%s,%s' % (m.group(1),
                                 self.name_or_num(int(m.group(2), 16)))
            else:
                ops = re.sub(r'0x([0-9a-f]+)',
                             lambda m: num(int(m.group(1), 16)), ops)
        return '\t%s\t%s' % (mn, ops) if ops else '\t%s' % mn

    def render(self, insns, skip_first_label=False):
        out = []
        for i, (addr, hexb, text) in enumerate(insns):
            if addr in self.labels and not (i == 0 and skip_first_label):
                out.append('')
                out.append('%s:' % lbl(addr))
            out.append(self.line(hexb, text))
        return out
