"""holes: classify the bytes that branch-following could not reach.

Unreached bytes inside the code are strings, tables, or code that is only
reachable through a table.  Word tables whose entries all look like code
addresses are followed as new entry points, repeatedly, so the code behind a
jump table gets found.  Tables live in the data area too (function's dsptbl),
so that is scanned for them as well.
"""

import bisect

from .flow import CODE_START, analyse, code_end, holes
from .source import get_bounds
from .text import read_text


def image_bytes(binf, base):
    with open(binf, 'rb') as f:
        data = f.read()
    return lambda a, b: data[a - base:b - base]


def printable(b):
    return 0x20 <= b < 0x7f or b in (0x0d, 0x0a)


def segments(get, a, b, ok, tables_only=False):
    """Split [a, b) into (kind, start, end, words) pieces.

    kind is 'table' (two or more consecutive words ok() accepts), 'text'
    (four or more printable bytes, plus a trailing NUL) or 'unknown'.
    """
    d, out, p, unk = get(a, b), [], 0, None

    def flush(upto):
        nonlocal unk
        if unk is not None:
            out.append(('unknown', a + unk, a + upto, None))
            unk = None

    while p < len(d):
        q, ws = p, []
        while q + 1 < len(d) and ok(d[q] | d[q + 1] << 8):
            ws.append(d[q] | d[q + 1] << 8)
            q += 2
        if len(ws) >= 2:
            flush(p)
            out.append(('table', a + p, a + q, ws))
            p = q
            continue
        if not tables_only:
            q = p
            while q < len(d) and printable(d[q]):
                q += 1
            if q - p >= 4:
                if q < len(d) and d[q] == 0:
                    q += 1
                flush(p)
                out.append(('text', a + p, a + q, None))
                p = q
                continue
            if unk is None:
                unk = p
        p += 1
    flush(len(d))
    return out


def discover(binf, base, end, hi):
    """Fixpoint: follow table entries until no new code appears.

    Returns (seen, remaining code-area segments, data-area tables, new roots,
    bytes unreached before any table was followed).
    """
    get = image_bytes(binf, base)
    roots, first = set(), None
    while True:
        seen, _ = analyse(binf, base, end, roots=roots)
        top = hi or code_end(seen)
        starts = sorted(seen)
        hs = holes(seen, CODE_START, top)
        if first is None:
            first = hs

        def in_hole(w):
            return any(a <= w < b for a, b in hs)

        def ok(w):
            if not CODE_START <= w < top:
                return False
            i = bisect.bisect_right(starts, w) - 1
            return not (i >= 0 and starts[i] != w
                        and w < starts[i] + seen[starts[i]][0])

        segs = [s for a, b in hs for s in segments(get, a, b, ok)]
        dtabs = [s for s in segments(get, top, end, ok, tables_only=True)
                 if any(in_hole(w) for w in s[3])]
        fresh = {w for s in segs + dtabs if s[0] == 'table'
                 for w in s[3] if w not in seen} - roots
        if not fresh:
            return seen, segs, dtabs, roots, first
        roots |= fresh


def preview(get, a, b, kind):
    d = get(a, min(b, a + 36))
    if kind == 'text':
        return repr(bytes(d).decode('latin-1'))
    return ' '.join('%02x' % x for x in d[:12]) + (' ...' if b - a > 12 else '')


def cmd_holes(binf, a86, base):
    lines = read_text(a86).split('\n')
    data_org, end = get_bounds(lines)
    hi = data_org if data_org < end else None
    get = image_bytes(binf, base)
    seen, segs, dtabs, roots, first = discover(binf, base, end, hi)
    top = hi or code_end(seen)

    total = lambda hs: sum(b - a for a, b in hs)
    print('code area %04xh..%04xh' % (CODE_START, top))
    print('following branches only : %d ranges, %d bytes unreached'
          % (len(first), total(first)))
    left = [(s[1], s[2]) for s in segs]
    print('after following tables  : %d new entry points, %d bytes unreached'
          % (len(roots), total(left)))

    kinds = {}
    for k, a, b, _ in segs:
        kinds[k] = kinds.get(k, 0) + (b - a)
    print('remaining, by kind      : ' + ', '.join(
        '%s %d bytes' % (k, kinds[k]) for k in sorted(kinds)))

    if dtabs:
        print('\njump tables found in the data area:')
        for _, a, b, ws in dtabs:
            print('  %04x..%04x  %d entries -> %s' % (
                a, b, len(ws), ' '.join('%04x' % w for w in ws[:8])
                + (' ...' if len(ws) > 8 else '')))

    print('\nremaining unreached ranges in the code:')
    for kind, a, b, ws in segs[:40]:
        if kind == 'table':
            note = '%d entries -> %s' % (len(ws), ' '.join('%04x' % w
                                                           for w in ws[:6]))
        else:
            note = preview(get, a, b, kind)
        print('  %04x..%04x  %-8s %4d bytes  %s' % (a, b, kind, b - a, note))
    if len(segs) > 40:
        print('  ... %d more' % (len(segs) - 40))
