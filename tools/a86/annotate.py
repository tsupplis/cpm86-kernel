"""annotate: quote strings and name jump tables, only where there is evidence.

Restrictive on purpose: a binary may have neither.  Text is quoted only when an
unreached code range is at least TEXT_MIN printable bytes on plain db lines; a
table becomes dw only when reached code indexes it through an indirect
jmp/call and every entry already has a label.  Anything else is left alone and
reported, and running it twice changes nothing.
"""

import re

from .build import verified_write
from .holes import discover, image_bytes
from .source import data_lines, emit_data, get_bounds, split_db_line
from .splice import LABEL, code_db_lines, first_insn_size
from .text import read_text

TEXT_MIN = 8


def locate(lines, anchor, size):
    """[(index, addr, size)] for every db/dw line with a known address."""
    return code_db_lines(lines, size) + data_lines(lines, anchor)


def split_at(lines, addr, anchor, size):
    for i, a, sz in locate(lines, anchor, size):
        if a < addr < a + sz:
            return lines[:i] + split_db_line(lines[i], addr - a) + lines[i + 1:]
    return lines


def replace_range(lines, a, b, make, anchor, size, accept=None):
    """lines with [a, b) swapped for make(existing label); None if it cannot be.

    Only plain, contiguous db/dw lines are replaced, and only if accept() (when
    given) approves the lines about to go.  A label already on the first line
    is handed to make() so it is kept, not dropped.
    """
    lines = split_at(split_at(lines, a, anchor, size), b, anchor, size)
    sel = [(i, ad, sz) for i, ad, sz in locate(lines, anchor, size)
           if a <= ad < b]
    if not sel or sel[0][1] != a or sel[-1][1] + sel[-1][2] != b:
        return None
    i0, i1 = sel[0][0], sel[-1][0] + 1
    if len(sel) != i1 - i0:
        return None
    if accept and not accept(lines[i0:i1]):
        return None
    m = re.match(r'^(\w+)\s*(?:db|dw)\s', lines[i0])
    return lines[:i0] + make(m.group(1) if m else None) + lines[i1:]


def covering(lines, a, b, anchor, size):
    return [lines[i] for i, ad, sz in locate(lines, anchor, size)
            if ad < b and ad + sz > a]


def cmd_annotate(binf, a86, base, only=None, verify=True):
    lines = read_text(a86).split('\n')
    anchor, end = get_bounds(lines)
    seen, segs, tabs, _, _, _ = discover(binf, base, end,
                                         anchor if anchor < end else None)
    get = image_bytes(binf, base)
    size = first_insn_size(binf, base)
    names = {int(m.group(1), 16): 'l' + m.group(1)
             for m in map(LABEL.match, lines) if m}
    done, skipped = [], []

    if only in (None, 'text'):
        for kind, a, b, _ in segs:
            if kind != 'text' or b - a < TEXT_MIN:
                continue
            where = 'text %04x..%04x' % (a, b)
            if any("'" in ln for ln in covering(lines, a, b, anchor, size)):
                skipped.append('%s: already quoted' % where)
                continue
            blob = bytes(get(a, b))

            def make(label, blob=blob, a=a):
                out = emit_data(blob, a)
                if label:
                    out[0] = label + out[0]
                return out

            new = replace_range(lines, a, b, make, anchor, size)
            if new is None:
                skipped.append('%s: not on plain db lines' % where)
                continue
            lines = new
            done.append('%s quoted (%d bytes)' % (where, b - a))

    if only in (None, 'tables'):
        for t, (site, ws) in sorted(tabs.items()):
            where = 'table %04x' % t
            if any(re.search(r'\bdw\b', ln)
                   for ln in covering(lines, t, t + 2 * len(ws), anchor, size)):
                skipped.append('%s: already dw' % where)
                continue
            missing = [w for w in ws if w not in names]
            if missing:
                skipped.append('%s: no label at %s' % (
                    where, ' '.join('%04x' % w for w in missing)))
                continue

            def make(label, t=t, ws=ws):
                return ['%s\tdw\t%s' % (label or 'd%04x' % t,
                                       ','.join(names[w] for w in ws))]

            new = replace_range(lines, t, t + 2 * len(ws), make, anchor, size)
            if new is None:
                skipped.append('%s: not on plain db lines' % where)
                continue
            lines = new
            done.append('%s -> dw, %d entries (%s ...)' % (
                where, len(ws), names[ws[0]]))

    if done:
        verified_write(a86, lines, verify, what='annotate',
                       ok='OK  %d annotated, byte-identical:\n  %s'
                          % (len(done), '\n  '.join(done)))
    else:
        print('nothing to annotate')
    for s in skipped:
        print('skipped: ' + s)
