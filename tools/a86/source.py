"""Reading and rewriting the .a86 source: bounds, labels, data lines."""

import re
import sys

from .text import num, read_text, split_operands, strip_comment


DATA_ORG = 0x736

# Upper bound of the image, used to filter implausible label candidates.
# Both bounds are per-source: override with `data_org equ 0xxxxh` /
# `image_end equ 0xxxxh` near the top of the .a86 (see get_bounds below).
IMAGE_END = 0xda0


def get_bounds(lines):
    """(data_org, image_end) for this source: an explicit equ if present,
    else the module defaults (which is what assign.a86 relies on)."""
    anchor, end = DATA_ORG, IMAGE_END
    for ln in lines:
        m = re.match(r'^data_org\s+equ\s+([0-9][0-9a-fA-F]*)h', ln)
        if m:
            anchor = int(m.group(1), 16)
        m = re.match(r'^image_end\s+equ\s+([0-9][0-9a-fA-F]*)h', ln)
        if m:
            end = int(m.group(1), 16)
    return anchor, end


def load_equates(a86):
    """value -> name, from the `name equ 0xxxxh` block."""
    eq = {}
    for ln in read_text(a86).splitlines():
        m = re.match(r'^(\w+)\s+equ\s+([0-9][0-9a-fA-F]*)h\s*(;.*)?$', ln)
        if m:
            eq.setdefault(int(m.group(2), 16), m.group(1))
    return eq


def load_labels(a86):
    return {int(m.group(1), 16)
            for m in re.finditer(r'^l([0-9a-f]{4}):', read_text(a86), re.M)}


def line_size(line):
    """Bytes emitted by one db/dw source line, or None if it emits nothing."""
    m = re.match(r'^\S*\s*(db|dw)\s+(.*)$', strip_comment(line))
    if not m:
        return None
    width = 1 if m.group(1) == 'db' else 2
    n = 0
    for op in split_operands(m.group(2).strip()):
        if op.startswith("'"):
            n += len(op.strip("'"))
        else:
            n += width
    return n


def data_lines(lines, anchor_addr):
    """[(index, addr, size)] for every data-emitting line after the data mark.

    The mark is a `data:` label or a `dseg` directive, whichever appears.
    """
    out, addr, started = [], anchor_addr, False
    for i, ln in enumerate(lines):
        if not started:
            if re.match(r'^data:', ln) or re.match(r'^\s*dseg\b', ln):
                started = True
            continue
        if re.match(r'^\s*end\s*$', ln):
            break
        sz = line_size(ln)
        if sz is not None:
            out.append((i, addr, sz))
            addr += sz
    return out


def emit_data(blob, base, minrun=4):
    """Render bytes as db lines, quoting printable runs and leaving the rest
    numeric.  Handles strings with embedded control bytes (CR/LF/NUL)."""
    toks, run = [], ''

    def flush():
        nonlocal run
        while len(run) > 40:
            # Avoid leaving a tail too short to stay quoted.
            cut = 40 if len(run) - 40 >= minrun else len(run) - minrun
            toks.append(("'%s'" % run[:cut], cut))
            run = run[cut:]
        if run:
            toks.append(("'%s'" % run, len(run)))
        run = ''

    for b in blob:
        if 0x20 <= b < 0x7f and b != 0x27:
            run += chr(b)
        else:
            flush()
            toks.append((num(b), 1))
    flush()

    # Merge short printable runs back into numeric form so we do not emit
    # things like 'a' for one stray character.
    out, line, width = [], [], 0
    for tok, n in toks:
        if tok.startswith("'") and n < minrun:
            tok = ','.join(num(ord(c)) for c in tok.strip("'"))
        w = len(tok) + 1
        if line and width + w > 50:
            out.append('\tdb\t' + ','.join(line))
            line, width = [], 0
        line.append(tok)
        width += w
    if line:
        out.append('\tdb\t' + ','.join(line))
    return out


def split_db_line(line, n):
    """Split a db/dw line so the first part emits exactly n bytes."""
    m = re.match(r'^(\S*)\s*(db|dw)\s+(.*)$', strip_comment(line))
    label, kind, ops = m.group(1), m.group(2), m.group(3).strip()
    width = 1 if kind == 'db' else 2
    first, second, used = [], [], 0
    for op in split_operands(ops):
        if used >= n:
            second.append(op)
            continue
        if op.startswith("'"):
            s = op.strip("'")
            if used + len(s) <= n:
                first.append(op)
                used += len(s)
            else:
                k = n - used
                first.append("'%s'" % s[:k])
                second.append("'%s'" % s[k:])
                used = n
        else:
            first.append(op)
            used += width
    out = []
    if first:
        out.append('%s\t%s\t%s' % (label, kind, ','.join(first)))
    if second:
        out.append('\t%s\t%s' % (kind, ','.join(second)))
    return out


def infer_width(text, name):
    """'word' or 'byte' for a variable, from how the source uses it."""
    w8 = r'\b(a|b|c|d)[lh]\b'
    for ln in text.split('\n'):
        if not re.search(r'[.\b]%s\b' % name, ln):
            continue
        if 'word ptr' in ln:
            return 'word'
        if 'byte ptr' in ln:
            return 'byte'
        rest = re.sub(r'[.]?%s(\[\w+\])?' % name, '', ln)
        if re.search(w8, rest):
            return 'byte'
        if re.search(r'\b(ax|bx|cx|dx|si|di|bp|sp|es|ds|ss|cs)\b', rest):
            return 'word'
    return 'byte'


def read_text_lines_split(lines, anchor, addr):
    """Ensure a data line starts at `addr`, splitting one if necessary."""
    for i, a, sz in data_lines(lines, anchor):
        if a == addr:
            return lines
        if a < addr < a + sz:
            parts = split_db_line(lines[i], addr - a)
            return lines[:i] + parts + lines[i + 1:]
    return lines


def retype_word(line):
    """Turn a numeric `db` line into the equivalent `dw` line, or None."""
    m = re.match(r'^(\w*)\s*db\s+(.*)$', strip_comment(line))
    if not m:
        return None
    label = m.group(1)
    cmt = line[len(strip_comment(line)):]
    ops = split_operands(m.group(2).strip())
    if any(o.startswith("'") for o in ops) or len(ops) % 2:
        return None
    vals = []
    for i in range(0, len(ops), 2):
        try:
            lo = int(ops[i].rstrip('h'), 16)
            hi = int(ops[i + 1].rstrip('h'), 16)
        except ValueError:
            return None
        vals.append(num(lo | (hi << 8)))
    return '%s\tdw\t%s%s' % (label, ','.join(vals), cmt)


def find_region(lines, start, end):
    """Index range of the lines between label `start` and the next label >= end."""
    starts = {}
    for i, ln in enumerate(lines):
        m = re.match(r'^l([0-9a-f]{4}):', ln)
        if m:
            starts[int(m.group(1), 16)] = i
    if start not in starts:
        sys.exit('no label l%04x: in source' % start)
    i0 = starts[start]
    after = sorted(a for a in starts if a >= end)
    if after:
        return i0, starts[after[0]]
    # End of the code area: fall back to the start of the data section.
    for i in range(i0, len(lines)):
        if re.match(r'^(data:|; ---- data)', lines[i]):
            return i0, i
    sys.exit('no label at or after %04x to bound the region' % end)
