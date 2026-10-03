"""typedata: type and label the data area, only where the source is still raw.

Uses the datamap classification.  A segment is rewritten only if every source
line it covers is still a bare scaffold dump (hex bytes, no label, no comment),
so anything already typed, named or commented is left exactly as it is.  Typing
is size-preserving by construction (db/dw/quoted strings of the same bytes);
the rebuild is the check, and it restores the file if it ever disagrees.

A label (dXXXX) is added only where something points: a direct or indexed
memory operand, a pointer loaded into si/di/bx/bp, or a pointer stored in data.
A pointer loaded into dx counts only at the start of a string, since dx often
holds a plain number.
"""

import re

from .annotate import replace_range
from .build import verified_write
from .datamap import bios_note, survey
from .source import emit_data
from .splice import first_insn_size
from .text import num, read_text

RAW = re.compile(r'^\tdb\t(?:[0-9][0-9a-f]{1,2}h,)*[0-9][0-9a-f]{1,2}h$')
STRONG = {'mem', 'idx', 'ptr', 'dptr'}


def is_raw(lines):
    return all(RAW.match(ln) for ln in lines)


def wants_label(a, kind, refs):
    kinds = {k for _, k, _ in refs.get(a, [])}
    return bool(kinds & STRONG) or (kind == 'text' and 'ptr?' in kinds)


def builder(kind, blob, name, note):
    def make(existing):
        label = existing or name
        if kind == 'var':
            op = 'db' if len(blob) == 1 else 'dw'
            return ['%s\t%s\t%s' % (label, op,
                                    num(int.from_bytes(blob, 'little')))]
        out = emit_data(blob, 0)
        if label:
            out[0] = label + out[0]
        if note:
            out.insert(0, '; embedded real-mode code (%s), kept as data' % note)
        return out
    return make


def cmd_typedata(binf, a86, base, verify=True):
    lines = read_text(a86).split('\n')
    lo, end, get, refs, tables, segs = survey(binf, base, lines)
    size = first_insn_size(binf, base)

    cur, done, labels, skipped = lines, {}, 0, []
    for kind, a, b in segs:
        if kind == 'table':
            continue                      # annotate owns jump tables
        blob = bytes(get(a, b))
        name = 'd%04x' % a if wants_label(a, kind, refs) else None
        note = bios_note(blob) if kind == 'binary' else None
        new = replace_range(cur, a, b, builder(kind, blob, name, note), lo,
                            size, accept=is_raw)
        if new is None:
            skipped.append('%s %04x..%04x' % (kind, a, b))
            continue
        cur = new
        done[kind] = done.get(kind, 0) + 1
        labels += 1 if name else 0

    if cur == lines:
        print('nothing to type')
    else:
        summary = ', '.join('%d %s' % (n, k) for k, n in sorted(done.items()))
        verified_write(a86, cur, verify, what='typedata',
                       ok='OK  typed %s; %d labels, byte-identical'
                          % (summary, labels))
    if skipped:
        print('left as they were (not raw scaffold lines): %d segments, '
              'e.g. %s' % (len(skipped), ', '.join(skipped[:4])))
