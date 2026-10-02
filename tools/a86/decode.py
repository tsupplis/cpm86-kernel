"""decode: turn every reached db region into instructions.

ndisasm and RASM-86 do not always agree: the assembler may reject a spelling or
pick a different encoding for the same instruction.  So decode everything, build,
find the FIRST thing that went wrong, demote just that instruction back to db
(with its mnemonic as a comment), and repeat.  One build per stubborn
instruction, not one per region.  The original source is restored unless the
result is byte-identical.
"""

import bisect
import os
import re
import shutil
import subprocess
import sys

from .build import rebuild, require_covered
from .disasm import Converter, disasm
from .flow import CODE_START, analyse
from .source import get_bounds, line_size, load_equates
from .splice import LABEL
from .text import num, read_text, write_text

MAX_ROUNDS = 400
END_OF_CODE = re.compile(r'^(; ---- data|\s*dseg\b|\s*end\s*$)')


def regions(lines):
    """[(body_start, body_end, addr, size)] for db-only regions after lXXXX:."""
    labs, stop, in_code = [], len(lines), False
    for i, ln in enumerate(lines):
        if re.match(r'^\s*org\s+100h\b', ln, re.I):
            in_code = True
        elif in_code and END_OF_CODE.match(ln):
            stop = i
            break
        elif in_code and LABEL.match(ln):
            labs.append((i, int(LABEL.match(ln).group(1), 16)))
    out = []
    for k, (i, a) in enumerate(labs):
        j = labs[k + 1][0] if k + 1 < len(labs) else stop
        body = lines[i + 1:j]
        sizes = [line_size(b) for b in body if b.strip()]
        if not sizes or any(s is None for s in sizes):
            continue                      # already decoded, or not plain db
        size = sum(sizes)
        if k + 1 < len(labs) and a + size != labs[k + 1][1]:
            sys.exit('address drift in the region at %04xh: its db lines emit '
                     '%d bytes but the next label is at %04xh'
                     % (a, size, labs[k + 1][1]))
        out.append((i + 1, j, a, size))
    return out


def as_db(hexb, text):
    raw = [num(int(hexb[i:i + 2], 16)) for i in range(0, len(hexb), 2)]
    return '\tdb\t%s\t; %s' % (','.join(raw), text)


def render(lines, regs, recs, bad, conv):
    out, pos = [], 0
    for b0, b1, a, _ in regs:
        if a not in recs:
            continue
        out += lines[pos:b0]
        for addr, hexb, text in recs[a]:
            out.append(as_db(hexb, text) if addr in bad
                       else conv.line(hexb, text))
        out.append('')
        pos = b1
    return out + lines[pos:]


def assemble_listing(d, name):
    """(error count, [(address or None, message, source text)]) from a listing."""
    subprocess.run(['unix2dos', '-q', name], cwd=d, capture_output=True)
    r = subprocess.run(['pcdev_rasm86', name, '$', 'px', 'sz'], cwd=d,
                       capture_output=True, text=True)
    rows = (r.stdout + r.stderr).replace('\r', '').split('\n')
    m = re.search(r'Number of errors:\s+(\d+)', '\n'.join(rows))
    errs = []
    for i, ln in enumerate(rows[:-1]):
        if 'ERROR NO' in ln:
            a = re.match(r'^ ?([0-9A-F]{4}) {2,}', rows[i + 1])
            errs.append((int(a.group(1), 16) if a else None, ln.strip(),
                         rows[i + 1].strip()))
    return (int(m.group(1)) if m else -1), errs


def cmd_decode(binf, a86, base):
    require_covered(a86)
    d, name = os.path.dirname(a86) or '.', os.path.basename(a86)
    lines = read_text(a86).split('\n')
    _, end = get_bounds(lines)
    seen, _ = analyse(binf, base, end)

    regs, recs = regions(lines), {}
    for _, _, a, size in regs:
        if a not in seen:
            continue
        insns = disasm(binf, a, a + size, base)
        if sum(len(h) // 2 for _, h, _ in insns) == size:
            recs[a] = insns
    if not recs:
        print('nothing to decode')
        return

    sizes = {addr: len(h) // 2 for ins in recs.values() for addr, h, _ in ins}
    starts = sorted(sizes)
    labels = {int(m.group(1), 16) for m in map(LABEL.match, lines) if m}
    conv = Converter(labels, load_equates(a86), CODE_START, end)

    def owner(addr):
        if addr is None:
            return None
        i = bisect.bisect_right(starts, addr) - 1
        return starts[i] if i >= 0 and addr < starts[i] + sizes[starts[i]] \
            else None

    backup, ok = a86 + '.bak', False
    shutil.copy2(a86, backup)
    bad, why = set(), {}
    try:
        for _ in range(MAX_ROUNDS):
            write_text(a86, '\n'.join(render(lines, regs, recs, bad, conv)))
            n, errs = assemble_listing(d, name)
            if n != 0:
                addr = next((a for a, _, _ in errs if a is not None), None)
                reason = errs[0][1] if errs else 'assembler failed'
            else:
                r = rebuild(d)
                if r.returncode == 0:
                    ok = True
                    break
                m = re.search(r'differ: char (\d+)', r.stdout + r.stderr)
                addr = int(m.group(1)) - 1 + base if m else None
                reason = 'encodes differently'
            hit = owner(addr)
            if hit is None or hit in bad:
                sys.exit('cannot attribute the failure (%s, address %s); '
                         'original source restored'
                         % (reason, '%04xh' % addr if addr is not None
                            else '?'))
            bad.add(hit)
            why[hit] = reason
        else:
            sys.exit('gave up after %d rounds; original source restored'
                     % MAX_ROUNDS)
    finally:
        if ok:
            os.remove(backup)
        else:
            shutil.move(backup, a86)

    total = len(sizes)
    print('OK  %d regions, %d instructions decoded, byte-identical'
          % (len(recs), total - len(bad)))
    if bad:
        print('%d kept as db (assembler disagrees with ndisasm):' % len(bad))
        for a in sorted(bad):
            text = next(t for ins in recs.values() for ad, _, t in ins
                        if ad == a)
            print('  %04x  %-24s %s' % (a, text, why[a]))
