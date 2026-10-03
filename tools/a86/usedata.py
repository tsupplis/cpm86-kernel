"""usedata: refer to data by label instead of by number, where it is safe.

Three forms are rewritten, each only when a data label sits at exactly that
address:   .0734h -> d0734     08abh[bx] -> d08ab[bx]     mov si,0a5ah ->
mov si,offset d0a5a.   A pointer loaded into dx is rewritten only at the label
of a string, since dx often holds a plain number.

Restrictive: an implicit width (decided by a register) must equal the label's
type, anything behind a segment override is left alone, and every candidate is
checked by the assembler.  All candidates are tried together; if that fails, a
halving search finds the lines that do not build and leaves just those numeric.
"""

import re

from .build import require_covered, trial, verified_write
from .source import data_lines, get_bounds
from .text import read_text, strip_comment

MARK = '; ---- data ----'
ABS = re.compile(r'(?<![:\w])\.([0-9][0-9a-f]*)h\b')
IDX = re.compile(r'(?<![:.\w])([0-9][0-9a-f]*)h\[')
OVERRIDE = re.compile(r'[a-z]s:\.?([0-9][0-9a-f]*)h\b')
PTR = re.compile(r'^\tmov\t(bx|si|di|bp|dx),([0-9][0-9a-f]*)h$')
INSN = re.compile(r'^\t([a-z]+)\t(.*)$')
REG8 = re.compile(r'\b[abcd][lh]\b')
REG16 = re.compile(r'\b(?:[abcd]x|si|di|bp|sp|[cdse]s)\b')
NOT_CODE = {'db', 'dw', 'dd', 'rs', 'rb', 'rw', 'org', 'cseg', 'dseg', 'end',
            'group'}


def data_labels(lines, anchor):
    """{addr: (name, 'b'|'w', is_text)} for labelled db/dw lines in the data."""
    out = {}
    for i, a, _ in data_lines(lines, anchor):
        m = re.match(r'^(\w+)\s*(db|dw)\s+(.*)$', lines[i])
        if m:
            out[a] = (m.group(1), 'b' if m.group(2) == 'db' else 'w',
                      "'" in m.group(3))
    return out


def implicit_width(code, token):
    """'x' if the line says its size, else 'b'/'w' from the other operand."""
    if re.search(r'\b(?:byte|word|dword) ptr\b', code):
        return 'x'
    rest = code.replace(token, '', 1)
    if REG8.search(rest):
        return 'b'
    if REG16.search(rest):
        return 'w'
    return '?'


def rewrite(line, labels, lo, end):
    """(new line, forms applied, [skip reasons]) for one code line."""
    code = strip_comment(line).rstrip()
    comment = line[len(code):]
    m = INSN.match(code)
    if not m or m.group(1) in NOT_CODE or "'" in code:
        return line, [], []
    mn, forms, skips = m.group(1), [], []

    p = PTR.match(code)
    if p:
        reg, addr = p.group(1), int(p.group(2), 16)
        if not lo <= addr < end:
            return line, [], []
        lab = labels.get(addr)
        if lab is None:
            return line, [], ['no label']
        if reg == 'dx' and not lab[2]:
            return line, [], ['dx pointer, not a string']
        return '\tmov\t%s,offset %s%s' % (reg, lab[0], comment), ['ptr'], []

    for m2 in OVERRIDE.finditer(code):
        if lo <= int(m2.group(1), 16) < end:
            skips.append('segment override')

    def sub(kind):
        def f(mt):
            addr = int(mt.group(1), 16)
            if not lo <= addr < end:
                return mt.group(0)
            lab = labels.get(addr)
            if lab is None:
                skips.append('no label')
                return mt.group(0)
            name = lab[0]
            if mn in ('les', 'lds'):
                name = 'dword ptr ' + name
            else:
                w = implicit_width(code, mt.group(0))
                if w not in ('x', lab[1]):
                    skips.append('width mismatch')
                    return mt.group(0)
            forms.append(kind)
            return name + ('[' if kind == 'idx' else '')
        return f

    new = ABS.sub(sub('abs'), code)
    new = IDX.sub(sub('idx'), new)
    return (new + comment if forms else line), forms, skips


def solve(a86, lines, cands):
    """The subset of cands that builds byte-identical, by halving."""
    if not cands:
        return []
    out = list(lines)
    for i, text, _ in cands:
        out[i] = text
    if trial(a86, out):
        return list(cands)
    if len(cands) == 1:
        return []
    mid = len(cands) // 2
    return solve(a86, lines, cands[:mid]) + solve(a86, lines, cands[mid:])


def cmd_usedata(a86, verify=True):
    lines = read_text(a86).split('\n')
    lo, end = get_bounds(lines)
    if lo >= end or MARK not in lines:
        raise SystemExit('no data area: set the boundary first')
    labels = data_labels(lines, lo)
    if not labels:
        print('nothing to substitute (no data labels yet: run typedata)')
        return

    start = next((i + 1 for i, ln in enumerate(lines)
                  if re.match(r'^\s*org\s+100h\b', ln, re.I)), 0)
    cands, left = [], {}
    for i in range(start, lines.index(MARK)):
        new, forms, skips = rewrite(lines[i], labels, lo, end)
        if forms:
            cands.append((i, new, forms))
        for s in skips:
            left[s] = left.get(s, 0) + 1

    if not cands:
        print('nothing to substitute')
    else:
        if verify:
            require_covered(a86)
            good = solve(a86, lines, cands)
        else:
            good = cands
        failed = len(cands) - len(good)
        if failed:
            left['did not build'] = failed
        if not good:
            print('nothing could be substituted safely')
        else:
            out = list(lines)
            for i, text, _ in good:
                out[i] = text
            kinds = {}
            for _, _, forms in good:
                for f in forms:
                    kinds[f] = kinds.get(f, 0) + 1
            verified_write(
                a86, out, verify, what='usedata',
                ok='OK  %d lines now use labels (%s), byte-identical'
                   % (len(good), ', '.join('%d %s' % (n, k)
                                           for k, n in sorted(kinds.items()))))
    if left:
        print('left numeric: ' + ', '.join('%d %s' % (n, k)
                                           for k, n in sorted(left.items())))
