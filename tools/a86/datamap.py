"""datamap: classify the data area and say what the code references in it.

Read-only.  The data area of a CMD is not always plain data: a disk utility can
carry whole boot sectors and loaders for another origin.  So the map reports
what is there (text, zero runs, evidenced word tables, binary) together with
who points at it, and flags binary blobs that contain BIOS interrupt opcodes.
"""

import re

from .holes import discover, image_bytes
from .source import data_lines, get_bounds
from .text import read_text

ZERO_MIN = 8
TEXT_MIN = 4
MEM = re.compile(r'\[((?:[a-z]{2}\+){0,2})0x([0-9a-f]+)\]')
REG8 = re.compile(r'\b[abcd][lh]\b')
REG16 = re.compile(r'\b(?:[abcd]x|si|di|bp|sp|[cdse]s)\b')
IMM = re.compile(r'^mov\s+(bx|si|di|bp|dx),0x([0-9a-f]+)$')
BIOS = {0x10: 'video', 0x12: 'memory size', 0x13: 'disk', 0x16: 'keyboard',
        0x19: 'reboot'}


def width_of(text):
    """'b', 'w' or '?': the size a memory operand is accessed at."""
    if re.search(r'\bbyte\b', text):
        return 'b'
    if re.search(r'\bword\b', text):
        return 'w'
    outside = MEM.sub('', text)
    if REG8.search(outside):
        return 'b'
    if REG16.search(outside):
        return 'w'
    return '?'


def references(seen, lo, hi):
    """{addr: [(site, kind, width)]} for data addresses the code points at.

    kinds: 'mem' a direct [addr] operand (a variable), 'idx' an indexed
    [reg+addr] one (an array or table base), 'ptr' an immediate loaded into
    si/di/bx/bp, 'ptr?' one loaded into dx (often a number, so a weak hint).
    """
    out = {}
    for site, (_, text) in sorted(seen.items()):
        m = IMM.match(text)
        if m and lo <= int(m.group(2), 16) < hi:
            kind = 'ptr?' if m.group(1) == 'dx' else 'ptr'
            out.setdefault(int(m.group(2), 16), []).append((site, kind, '?'))
        for m in MEM.finditer(text):
            v = int(m.group(2), 16)
            if lo <= v < hi:
                out.setdefault(v, []).append(
                    (site, 'idx' if m.group(1) else 'mem', width_of(text)))
    return out


def printable(b):
    return 0x20 <= b < 0x7f or b in (0x0d, 0x0a)


def text_span(img, p, end):
    """Start of the text inside img[p:end], or None.

    Junk in front (the tail of the previous object) is skipped: the text begins
    at the first run of TEXT_MIN printable bytes, and the rest must be mostly
    printable.
    """
    stop = end - 1 if img[end - 1] == 0 else end
    run = 0
    for k in range(p, stop):
        run = run + 1 if printable(img[k]) else 0
        if run >= TEXT_MIN:
            start = k - TEXT_MIN + 1
            body = img[start:stop]
            ok = sum(1 for b in body if printable(b))
            return start if ok / len(body) >= 0.85 else None
    return None


def classify(img, lo, tables, refs):
    """[(kind, start, end)] covering the whole area.

    Every address the code points at starts a new object, so a text run never
    swallows a neighbouring variable.  Kinds: table, zeros, var (a direct
    memory operand of known width), text, binary.
    """
    n = len(img)
    tab_at = {t - lo: 2 * len(ws) for t, ws in tables.items()
              if lo <= t < lo + n}

    def run_from(off):
        k = off
        while k < n and printable(img[k]):
            k += 1
        return k - off

    def starts_object(off, rs):
        """Direct and indexed operands always do.  A pointer does unless it
        lands inside text without a string starting there: that is a number
        that merely looks like an address."""
        if any(k in ('mem', 'idx', 'dptr') for _, k, _ in rs):
            return True
        if any(k == 'ptr' for _, k, _ in rs):
            return (off == 0 or not printable(img[off - 1])
                    or run_from(off) >= TEXT_MIN)
        return False

    cuts = {a - lo for a, rs in refs.items()
            if 0 <= a - lo < n and starts_object(a - lo, rs)}
    cuts |= set(tab_at) | {s + w for s, w in tab_at.items()}
    order = sorted(c for c in cuts if 0 <= c <= n)
    segs, p, pend = [], 0, None

    def close(upto):
        nonlocal pend
        if pend is not None:
            segs.append(('binary', lo + pend, lo + upto))
            pend = None

    def next_cut(x):
        return next((c for c in order if c > x), n)

    while p < n:
        if p in cuts:
            close(p)
        if p in tab_at:
            segs.append(('table', lo + p, lo + p + tab_at[p]))
            p += tab_at[p]
            continue
        q = p
        while q < n and img[q] == 0 and (q == p or q not in cuts):
            q += 1
        if q - p >= ZERO_MIN:
            close(p)
            segs.append(('zeros', lo + p, lo + q))
            p = q
            continue
        mem = [w for _, k, w in refs.get(lo + p, []) if k == 'mem']
        width = next((w for w in mem if w != '?'), None)
        if width:
            size = 1 if width == 'b' else 2
            close(p)
            segs.append(('var', lo + p, lo + min(p + size, next_cut(p))))
            p = min(p + size, next_cut(p))
            continue
        z = img.find(b'\0', p)
        end = min(n if z < 0 else z + 1, next_cut(p))
        start = text_span(img, p, end)
        if start is not None:
            if start > p:
                if pend is None:
                    pend = p
                close(start)
            segs.append(('text', lo + start, lo + end))
            p = end
            continue
        if pend is None:
            pend = p
        p += 1
    close(n)
    return segs


def pointer_vars(img, lo, refs):
    """Add the targets of initialised word variables that point into the area.

    `namtbl dw keynam1` is evidence that keynam1 starts an object, even if the
    code only ever reaches it through that pointer.
    """
    n = len(img)
    for a, rs in list(refs.items()):
        off = a - lo
        if (any(k == 'mem' and w == 'w' for _, k, w in rs)
                and 0 <= off and off + 2 <= n):
            v = img[off] | img[off + 1] << 8
            if lo <= v < lo + n:
                refs.setdefault(v, []).append((a, 'dptr', '?'))
    return refs


def bios_hits(blob):
    hits = {}
    for i in range(len(blob) - 1):
        if blob[i] == 0xcd and blob[i + 1] in BIOS:
            hits[blob[i + 1]] = hits.get(blob[i + 1], 0) + 1
    return hits


def bios_note(blob):
    """'int 13h x2, ...' when a blob looks like embedded real-mode code.

    At least two BIOS interrupt opcodes in 32+ bytes: a single `cd 10` is
    easily box-drawing characters inside a screen string.
    """
    h = bios_hits(blob)
    if sum(h.values()) >= 2 and len(blob) >= 32:
        return ', '.join('int %02Xh x%d' % (k, v) for k, v in sorted(h.items()))
    return None


def describe(kind, a, b, blob, tables):
    if kind == 'text':
        return repr(blob.decode('latin-1')[:44]).replace('\\x', '^')
    if kind == 'table':
        ws = tables[a][1]
        return '%d entries -> %s' % (len(ws), ' '.join('%04x' % w
                                                       for w in ws[:6]))
    if kind == 'var':
        return '%s variable' % ('byte' if b - a == 1 else 'word')
    if kind == 'binary':
        note = bios_note(blob)
        return ' '.join('%02x' % x for x in blob[:10]) + (
            ' ...' if len(blob) > 10 else '') + (
            '  BIOS: ' + note if note else '')
    return ''


def survey(binf, base, lines):
    """(lo, end, get, refs, tables, segs): the data area, classified."""
    lo, end = get_bounds(lines)
    if lo >= end:
        raise SystemExit('no data area: set the boundary first '
                         '(a86tool.py boundary ... --set)')
    seen, _, tabs, _, _, _ = discover(binf, base, end, lo)
    get = image_bytes(binf, base)
    img = bytes(get(lo, end))
    refs = pointer_vars(img, lo, references(seen, lo, end))
    tables = {t: (s, ws) for t, (s, ws) in tabs.items() if lo <= t < end}
    segs = classify(img, lo, {t: ws for t, (_, ws) in tables.items()}, refs)
    return lo, end, get, refs, tables, segs


def cmd_datamap(binf, a86, base):
    lines = read_text(a86).split('\n')
    lo, end, get, refs, tables, segs = survey(binf, base, lines)
    kinds = {}
    for k, a, b in segs:
        kinds[k] = kinds.get(k, 0) + b - a
    print('data area %04xh..%04xh, %d bytes, %d distinct addresses referenced'
          % (lo, end, end - lo, len(refs)))
    print('by kind: ' + ', '.join('%s %d' % (k, kinds[k])
                                  for k in sorted(kinds)))
    print()
    mid = {}
    for k, a, b in segs:
        blob = bytes(get(a, b))
        inside = sorted(v for v in refs if a <= v < b)
        tag = ''
        if inside:
            tag = '  <- ' + ' '.join(
                '%04x(%s)' % (v, refs[v][0][1]) for v in inside[:4])
            for v in inside:
                if v != a:
                    mid[v] = a
        print('%04x..%04x %-6s %4d  %s%s' % (a, b, k, b - a, describe(
            k, a, b, blob, tables), tag))
    if mid:
        print('\nreferenced inside a segment, not at its start (%d):' % len(mid))
        for v, a in sorted(mid.items())[:20]:
            print('  %04x is in the segment at %04x' % (v, a))

    anchor = lo
    have = {}
    for i, a, _ in data_lines(lines, anchor):
        m = re.match(r'^(\w+)\s*(?:db|dw)\s', lines[i])
        if m:
            have[a] = m.group(1)
    if have:
        bad = [(n, a) for a, n in have.items() for k, s, e in segs
               if k != 'binary' and s < a < e]
        print('\nexisting data labels: %d; inside a classified segment: %d%s'
              % (len(have), len(bad), '' if not bad else '  ' + ' '.join(
                  '%s@%04x' % x for x in bad[:6])))
