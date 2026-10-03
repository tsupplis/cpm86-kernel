"""holes: classify the bytes that branch-following could not reach.

Unreached bytes inside the code are strings, tables, or code that is only
reachable through a table.  A word table is trusted only when reached code
indexes it through an indirect jmp/call (jmp word ptr tbl[bx]); its entries
are then followed as new entry points, repeatedly, so the code behind a jump
table gets found.
"""

import bisect
import re

from .flow import CODE_START, analyse, code_end, holes
from .source import get_bounds
from .text import read_text


def image_bytes(binf, base):
    with open(binf, 'rb') as f:
        data = f.read()
    return lambda a, b: data[a - base:b - base]


def printable(b):
    return 0x20 <= b < 0x7f or b in (0x0d, 0x0a)


def segments(get, a, b, ok):
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


INDIRECT = re.compile(r'\[(?:[a-z]{2}\+){0,2}0x([0-9a-f]+)\]')
# call/jmp through a bare register: the table address was put there earlier
BARE = re.compile(r'^(?:call|jmp)\s+word\s+(?:near\s+)?\[(bx|si|di|bp)\]$')
ADD_VAR = re.compile(r'^add\s+(bx|si|di|bp),\[0x([0-9a-f]+)\]$')
STORE_VAR = re.compile(r'^mov\s+word\s+\[0x([0-9a-f]+)\],0x([0-9a-f]+)$')


def pointer_vars(seen):
    """{variable address: site} for `add reg,[var]` that feeds `call word [reg]`.

    The table is not named at the call: its address lives in a variable that
    the code adds to the index.  Both instructions must be in one straight run.
    """
    order = sorted(seen)
    out = {}
    for i, a in enumerate(order):
        m = BARE.match(seen[a][1])
        if not m:
            continue
        for j in range(i - 1, max(i - 8, -1), -1):
            b = order[j]
            if b + seen[b][0] != order[j + 1]:
                break
            v = ADD_VAR.match(seen[b][1])
            if v and v.group(1) == m.group(1):
                out.setdefault(int(v.group(2), 16), a)
                break
    return out


def table_sites(seen, get=None):
    """{table address: address of the indirect jmp/call that indexes it}.

    A table is named by a displacement on the call/jmp, or held in a variable
    that is added to the index (pointer_vars).  For such a variable the table
    addresses are its value in the image and every constant stored into it.
    """
    out = {}
    for a, (_, text) in seen.items():
        if text.split(None, 1)[0] in ('jmp', 'call'):
            m = INDIRECT.search(text)
            if m and int(m.group(1), 16) >= CODE_START:
                out.setdefault(int(m.group(1), 16), a)
    if get is None:
        return out
    pv = pointer_vars(seen)
    for v, site in pv.items():
        raw = get(v, v + 2)
        cands = {raw[0] | raw[1] << 8}
        for _, text in seen.values():
            s = STORE_VAR.match(text)
            if s and int(s.group(1), 16) == v:
                cands.add(int(s.group(2), 16))
        for t in cands:
            if t >= CODE_START:
                out.setdefault(t, site)
    return out


def read_table(get, t, end, ok, stops=()):
    """Words from t on, while each is a plausible code address.

    A table ends where the code one of its own entries names begins (those
    bytes are instructions, not more entries), and where another table starts.
    """
    ws, cut = [], end
    while t + 2 * len(ws) + 2 <= cut and len(ws) < 128:
        a = t + 2 * len(ws)
        if a in stops:
            break
        raw = get(a, a + 2)
        w = raw[0] | raw[1] << 8
        if not ok(w):
            break
        ws.append(w)
        if a + 2 <= w < cut:
            cut = w
    return ws


def discover(binf, base, end, hi):
    """Fixpoint: follow table entries until no new code appears.

    Returns (seen, remaining code-area segments, {table: (site, words)}, new
    roots, ranges unreached before any table was followed, branch targets).
    Tables are found through indirect jmp/call displacements, so there is
    evidence for each.
    """
    get = image_bytes(binf, base)
    roots, first, tabs = set(), None, {}
    while True:
        seen, targets = analyse(binf, base, end, roots=roots)
        top = hi or code_end(seen)
        starts = sorted(seen)
        hs = holes(seen, CODE_START, top)
        if first is None:
            first = hs

        def ok(w):
            if not CODE_START <= w < top:
                return False
            i = bisect.bisect_right(starts, w) - 1
            return not (i >= 0 and starts[i] != w
                        and w < starts[i] + seen[starts[i]][0])

        sites = table_sites(seen, get)
        for t, site in sites.items():
            ws = read_table(get, t, end, ok, set(sites) - {t})
            if len(ws) >= 2:
                tabs[t] = (site, ws)
        fresh = {w for _, ws in tabs.values() for w in ws
                 if w not in seen} - roots
        if not fresh:
            segs = [s for a, b in hs for s in segments(get, a, b, ok)]
            return seen, segs, tabs, roots, first, targets
        roots |= fresh


def reach(binf, base, lines):
    """(reached instructions, branch and table-entry targets) for a source.

    The one definition of 'code' that boundary, labels and decode all use, so
    they cannot disagree.  Table entries are followed only below the code
    area's end (data_org once set, else the end of what branches reach).
    """
    data_org, end = get_bounds(lines)
    seen, _, _, roots, _, targets = discover(
        binf, base, end, data_org if data_org < end else None)
    return seen, targets | roots


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
    seen, segs, tabs, roots, first, _ = discover(binf, base, end, hi)
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

    if tabs:
        print('\njump tables (found through an indirect jmp/call):')
        for t in sorted(tabs):
            site, ws = tabs[t]
            print('  %04x  %d entries, indexed at %04x -> %s' % (
                t, len(ws), site, ' '.join('%04x' % w for w in ws[:8])
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
