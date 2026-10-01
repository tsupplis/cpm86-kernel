#!/usr/bin/env python3
"""Reconstruct DRI RASM-86 sources from shipped CP/M-86 .CMD binaries.

The workflow is always: splice labels at every branch target, then convert the
raw `db` blocks to instructions a region at a time, checking after each step
that the rebuilt binary is still byte-identical to the original.

  a86tool.py labels <bin> <a86> [--org 126] [--end 736]
      Splice an `lXXXX:` label at every branch target found in the range.

  a86tool.py gen <bin> <a86> <start> <end>
      Print the converted source for a range (does not modify anything).

  a86tool.py patch <bin> <a86> <start> <end> [--no-verify]
      Convert a range and splice it into the .a86 in place, replacing the `db`
      block between the bounding labels.  Runs `make check` afterwards and
      restores the original file if it fails.

Addresses are hex.  Names are taken from the `name equ 0xxxxh` block in the
.a86, so adding an equate there is enough to have it used everywhere after.
"""
import os
import re
import shutil
import subprocess
import sys

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
        m = re.match(r'^data_org\s+equ\s+(0[0-9a-fA-F]*)h', ln)
        if m:
            anchor = int(m.group(1), 16)
        m = re.match(r'^image_end\s+equ\s+(0[0-9a-fA-F]*)h', ln)
        if m:
            end = int(m.group(1), 16)
    return anchor, end


def num(v):
    s = format(v, 'x')
    if len(s) % 2:
        s = '0' + s
    if s[0] not in '0123456789':
        s = '0' + s
    return s + 'h'


def lbl(v):
    return 'l%04x' % v


def read_text(path):
    with open(path, newline='') as f:
        return f.read().replace('\r\n', '\n')


def write_text(path, text):
    with open(path, 'w', newline='\n') as f:
        f.write(text)


def load_equates(a86):
    """value -> name, from the `name equ 0xxxxh` block."""
    eq = {}
    for ln in read_text(a86).splitlines():
        m = re.match(r'^(\w+)\s+equ\s+(0[0-9a-fA-F]*)h\s*(;.*)?$', ln)
        if m:
            eq.setdefault(int(m.group(2), 16), m.group(1))
    return eq


def load_labels(a86):
    return {int(m.group(1), 16)
            for m in re.finditer(r'^l([0-9a-f]{4}):', read_text(a86), re.M)}


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
            return '%s[%s][%s]' % (seg, m.group(1), m.group(2))
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


def cmd_gen(binf, a86, start, end, base):
    conv = Converter(load_labels(a86), load_equates(a86), start, end)
    print('\n'.join(conv.render(disasm(binf, start, end, base))))


def cmd_labels(binf, a86, base, lo, hi):
    """Splice a label at every branch target, splitting db blocks as needed."""
    insns = disasm(binf, lo, hi, base)
    targets = set()
    for _, _, text in insns:
        parts = text.split(None, 1)
        if parts[0] in BRANCH and len(parts) > 1:
            for m in re.finditer(r'0x([0-9a-f]+)', parts[1]):
                v = int(m.group(1), 16)
                if lo <= v < hi:
                    targets.add(v)
    print('%d branch targets in %04x..%04x' % (len(targets), lo, hi))
    return targets


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


def rebuild(d):
    """Rebuild from scratch and report success.

    `make clean` first: make compares mtimes to the second, so a file written
    and built in the same second can be judged up to date and the stale object
    linked instead - which silently validates a broken source.
    """
    subprocess.run(['make', 'clean'], cwd=d, capture_output=True)
    return subprocess.run(['make', 'check'], cwd=d, capture_output=True,
                          text=True)

def cmd_patch(binf, a86, start, end, base, verify=True):
    text = read_text(a86)
    lines = text.split('\n')
    i0, i1 = find_region(lines, start, end)
    region = lines[i0:i1]
    if not any(re.match(r'^\tdb\t0', l) for l in region):
        print('l%04x..%04x: already decoded, nothing to do' % (start, end))
        return
    conv = Converter(load_labels(a86), load_equates(a86), start, end)
    body = conv.render(disasm(binf, start, end, base), skip_first_label=True)
    new = lines[:i0] + ['%s:' % lbl(start)] + body + [''] + lines[i1:]

    backup = a86 + '.bak'
    shutil.copy2(a86, backup)
    write_text(a86, '\n'.join(new))
    if not verify:
        os.remove(backup)
        return
    r = rebuild(os.path.dirname(a86) or '.')
    if r.returncode == 0:
        os.remove(backup)
        ndb = sum(1 for l in new if re.match(r'^\tdb\t0', l))
        print('OK  l%04x..%04x decoded, byte-identical (%d db lines left)'
              % (start, end, ndb))
    else:
        shutil.move(backup, a86)
        tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
        print('FAIL l%04x..%04x - reverted:\n  %s'
              % (start, end, '\n  '.join(tail)))
        sys.exit(1)


def split_operands(ops):
    """Split a db/dw operand list on commas that are outside quotes."""
    out, cur, q = [], '', False
    for ch in ops:
        if ch == "'":
            q = not q
        if ch == ',' and not q:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def strip_comment(s):
    """Drop a trailing `;` comment, ignoring semicolons inside quotes.

    The data really does contain strings like ';<=>?@ABCD' (PC scan codes), so
    a plain regex mistakes them for comments and undercounts the line.
    """
    q = False
    for i, ch in enumerate(s):
        if ch == "'":
            q = not q
        elif ch == ';' and not q:
            return s[:i]
    return s


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


def cmd_data(binf, a86, start, end, base, verify=True):
    text = read_text(a86)
    lines = text.split('\n')
    anchor, _ = get_bounds(lines)
    dl = data_lines(lines, anchor)
    sel = [(i, a, s) for (i, a, s) in dl if start <= a < end]
    if not sel:
        sys.exit('no data lines in %04x..%04x' % (start, end))
    if sel[0][1] != start:
        sys.exit('range must start on a line boundary (nearest %04x)' % sel[0][1])
    last = sel[-1]
    if last[1] + last[2] != end:
        sys.exit('range must end on a line boundary (nearest %04x)'
                 % (last[1] + last[2]))
    i0, i1 = sel[0][0], sel[-1][0] + 1
    with open(binf, 'rb') as f:
        f.seek(start - base)
        blob = f.read(end - start)
    new = lines[:i0] + emit_data(blob, start) + lines[i1:]

    backup = a86 + '.bak'
    shutil.copy2(a86, backup)
    write_text(a86, '\n'.join(new))
    if not verify:
        os.remove(backup)
        return
    r = rebuild(os.path.dirname(a86) or '.')
    if r.returncode == 0:
        os.remove(backup)
        print('OK  data %04x..%04x converted, byte-identical' % (start, end))
    else:
        shutil.move(backup, a86)
        tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
        print('FAIL data %04x..%04x - reverted:\n  %s'
              % (start, end, '\n  '.join(tail)))
        sys.exit(1)


def load_sym(symfile):
    """address -> (name, kind) from a RASM-86 .sym file.

    kind is 'VAR' (data label), 'NUM' (equate) or 'LAB' (code label).  A data
    label beats an equate beats a code label when several share an address.
    """
    rank = {'VARIABLES': (0, 'VAR'), 'NUMBERS': (1, 'NUM'),
            'LABELS': (2, 'LAB')}
    # Bounds markers are not variables - never substitute them into code.
    skip = {'DATA_ORG', 'IMAGE_END'}
    cur, best = None, {}
    with open(symfile, errors='ignore') as f:
        for ln in f:
            # Section headers are page-break prefixed: "\f0000 VARIABLES".
            ln = ln.replace('\r', '').replace('\f', '').rstrip()
            m = re.match(r'^0000\s+(VARIABLES|NUMBERS|LABELS)\s*$', ln)
            if m:
                cur = rank[m.group(1)]
                continue
            if cur is None:
                continue
            for a, n in re.findall(r'([0-9A-F]{4})\s+(\w+)', ln):
                if n in skip:
                    continue
                v = int(a, 16)
                if v not in best or cur[0] < best[v][0]:
                    best[v] = (cur[0], n.lower(), cur[1])
    return {v: (n, k) for v, (p, n, k) in best.items()}


# Only these three forms are genuinely address references.  Anything else that
# happens to look like an address (screen coordinates, masks, glyph pairs) must
# be left alone - substituting those produced `sub dx,l051b` and broke the build.
RE_ABS = re.compile(r'\.(0[0-9a-fA-F]+h)\b')          # .08f3h
RE_IDX = re.compile(r'\b(0[0-9a-fA-F]+h)(\[)')        # 08ffh[bx]
# Must not match when an index follows: `mov si,07d2h[di]` reads the table,
# it does not load its address.
RE_PTR = re.compile(r'\b(mov\s+(?:bx|si|di|bp)\s*,\s*)(0[0-9a-fA-F]+h)(?!\s*\[)\b')


def relabel_line(ln, sym, unresolved, minaddr=0x100, image_end=IMAGE_END):
    if re.match(r'^\w+\s+equ\s', ln):          # the definitions themselves
        return ln
    out = []
    for i, part in enumerate(ln.split("'")):
        if i % 2:                              # inside a string literal
            out.append(part)
            continue

        def note(v):
            # Only addresses inside the image are plausible label candidates;
            # masks and glyph pairs that look like addresses are not.
            if minaddr <= v < image_end:
                unresolved[v] = unresolved.get(v, 0) + 1

        def abs_sub(m):
            v = int(m.group(1)[:-1], 16)
            if v < minaddr:
                return m.group(0)
            e = sym.get(v)
            # An indexed/absolute operand must use an equate: a code label
            # there makes RASM-86 emit a CS: override and shift everything.
            if e and e[1] == 'NUM':
                return '.' + e[0]
            note(v)
            return m.group(0)

        def idx_sub(m):
            v = int(m.group(1)[:-1], 16)
            if v < minaddr:
                return m.group(0)
            e = sym.get(v)
            if e and e[1] == 'NUM':
                return e[0] + m.group(2)
            note(v)
            return m.group(0)

        def ptr_sub(m):
            v = int(m.group(2)[:-1], 16)
            if v < minaddr:
                return m.group(0)
            e = sym.get(v)
            if e and e[1] == 'VAR':
                return m.group(1) + 'offset ' + e[0]
            if e and e[1] == 'NUM':
                return m.group(1) + e[0]
            note(v)
            return m.group(0)

        part = RE_ABS.sub(abs_sub, part)
        part = RE_IDX.sub(idx_sub, part)
        part = RE_PTR.sub(ptr_sub, part)
        out.append(part)
    return "'".join(out)


def cmd_relabel(a86, verify=True):
    d = os.path.dirname(a86) or '.'
    stem = os.path.splitext(os.path.basename(a86))[0]
    subprocess.run(['unix2dos', '-q', os.path.basename(a86)], cwd=d,
                   capture_output=True)
    subprocess.run(['pcdev_rasm86', os.path.basename(a86), '$', 'pz'], cwd=d,
                   capture_output=True)
    symf = os.path.join(d, stem + '.sym')
    if not os.path.exists(symf):
        sys.exit('no %s - does the source assemble?' % symf)
    sym = load_sym(symf)

    lines = read_text(a86).split('\n')
    _, image_end = get_bounds(lines)
    unresolved = {}
    new = [relabel_line(l, sym, unresolved, image_end=image_end) for l in lines]
    nsub = sum(1 for a, b in zip(lines, new) if a != b)
    if nsub == 0:
        print('nothing to relabel')
    else:
        backup = a86 + '.bak'
        shutil.copy2(a86, backup)
        write_text(a86, '\n'.join(new))
        r = rebuild(d)
        if r.returncode == 0:
            os.remove(backup)
            print('OK  %d lines relabelled, byte-identical' % nsub)
        else:
            shutil.move(backup, a86)
            tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
            print('FAIL relabel - reverted:\n  %s' % '\n  '.join(tail))
            sys.exit(1)
    if unresolved:
        print('unresolved addresses (need a label):')
        for v in sorted(unresolved):
            print('  %04xh  x%d' % (v, unresolved[v]))


def cmd_mklabel(a86, addr, name):
    """Insert a data label at `addr`, splitting the db line if necessary."""
    lines = read_text(a86).split('\n')
    anchor, _ = get_bounds(lines)
    for i, a, sz in data_lines(lines, anchor):
        if a == addr:
            lines[i] = re.sub(r'^\s*', name + '\t', lines[i], count=1) \
                if not re.match(r'^\w', lines[i]) else lines[i]
            write_text(a86, '\n'.join(lines))
            print('label %s at %04xh' % (name, addr))
            return
        if a < addr < a + sz:
            sys.exit('%04xh is %d bytes into a db line (addr %04xh); split it '
                     'first' % (addr, addr - a, a))
    sys.exit('no data line at %04xh' % addr)


def scan_unresolved(lines, sym, image_end=IMAGE_END):
    u = {}
    for ln in lines:
        relabel_line(ln, sym, u, image_end=image_end)
    return u


def assemble_sym(a86):
    """Assemble and return the address -> (name, kind) map."""
    d = os.path.dirname(a86) or '.'
    stem = os.path.splitext(os.path.basename(a86))[0]
    subprocess.run(['unix2dos', '-q', os.path.basename(a86)], cwd=d,
                   capture_output=True)
    subprocess.run(['pcdev_rasm86', os.path.basename(a86), '$', 'pz'], cwd=d,
                   capture_output=True)
    symf = os.path.join(d, stem + '.sym')
    if not os.path.exists(symf):
        sys.exit('no %s - does the source assemble?' % symf)
    return load_sym(symf)


def cmd_mklabels(a86, prefix='d', verify=True):
    """Define an equate for every address still referenced numerically.

    Equates rather than labels: an indexed or absolute operand that names a
    label makes RASM-86 emit a CS: override, which changes the encoding.  An
    equate assembles identically to the literal, and needs no splitting of the
    data lines.  Give them real names afterwards with `rename`.
    """
    sym = assemble_sym(a86)
    lines = read_text(a86).split('\n')
    _, image_end = get_bounds(lines)
    todo = sorted(a for a in scan_unresolved(lines, sym, image_end) if a not in sym)
    if not todo:
        print('no unresolved addresses')
        return

    last = max(i for i, ln in enumerate(lines) if re.match(r'^\w+\s+equ\s', ln))
    new = ['%s%04x\tequ\t%s' % (prefix, a, num(a)) for a in todo]
    lines = lines[:last + 1] + new + lines[last + 1:]

    sym.update({a: ('%s%04x' % (prefix, a), 'NUM') for a in todo})
    u = {}
    lines = [relabel_line(l, sym, u) for l in lines]

    backup = a86 + '.bak'
    shutil.copy2(a86, backup)
    write_text(a86, '\n'.join(lines))
    if not verify:
        os.remove(backup)
        return
    r = rebuild(os.path.dirname(a86) or '.')
    if r.returncode == 0:
        os.remove(backup)
        print('OK  %d equates added and substituted, byte-identical:'
              % len(todo))
        print('  ' + ' '.join('%s%04x' % (prefix, a) for a in todo))
    else:
        shutil.move(backup, a86)
        tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
        print('FAIL mklabels - reverted:\n  %s' % '\n  '.join(tail))
        sys.exit(1)


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


def cmd_mkvars(binf, a86, base=0, verify=True):
    """Turn data-area equates into real, typed data labels.

    Equates are a crutch: the original source would have declared storage and
    let the label carry its own type.  With a typed label every `byte ptr` /
    `word ptr` override disappears, and a `ds:` prefix keeps the encoding
    identical (the symbol lives in cseg, so without it RASM-86 emits a CS:
    override and changes the bytes).
    """
    text = read_text(a86)
    lines = text.split('\n')
    anchor, image_end = get_bounds(lines)

    eq = {}
    for i, ln in enumerate(lines):
        m = re.match(r'^(\w+)\s+equ\s+(0[0-9a-fA-F]*)h\s*(;.*)?$', ln)
        if m:
            v = int(m.group(2), 16)
            if anchor <= v < image_end:
                eq[m.group(1)] = (v, m.group(3) or '')
    if not eq:
        print('no data-area equates left')
        return

    width = {n: infer_width(text, n) for n in eq}
    addrs = sorted(set(v for v, _ in eq.values()))
    byaddr = {}
    for n, (v, c) in eq.items():
        byaddr.setdefault(v, []).append((n, c))

    # Split the data lines so every target address starts a line.
    for a in addrs:
        lines = read_text_lines_split(lines, anchor, a)

    # Attach the labels and re-type the storage.
    dl = data_lines(lines, anchor)
    with open(binf, 'rb') as f:
        blob = f.read()
    # A label owns every byte up to the next label, which may span several of
    # the original db lines; merge them so the storage gets one typed name.
    # Lines that already carry a label bound the span - never absorb those.
    named = set(ad for i, ad, sz in dl if re.match(r'^\w+\s*(db|dw)\s', lines[i]))
    stops = sorted(set(addrs) | named | {image_end})
    for k in range(len(addrs) - 1, -1, -1):
        a = addrs[k]
        b = next(x for x in stops if x > a)
        owned = [(i, ad, sz) for i, ad, sz in dl if a <= ad < b]
        if not owned:
            continue
        first = owned[0][0]
        size = sum(sz for _, _, sz in owned)
        names = byaddr[a]
        name, cmt = names[0]
        want = 'word' if any(width[n] == 'word' for n, _ in names) else 'byte'
        data = blob[a - base:a - base + size]
        if want == 'word' and size % 2 == 0:
            vals = ','.join(num(data[j] | (data[j + 1] << 8))
                            for j in range(0, size, 2))
            body = ['%s\tdw\t%s' % (name, vals)]
        else:
            # Keep text readable rather than dumping hex bytes.
            body = emit_data(data, a)
            body[0] = name + body[0]
        if cmt:
            body[0] += '\t' + cmt
        for extra, _ in names[1:]:
            body.insert(0, '%s\tequ\t%s' % (extra, num(a)))
        last = owned[-1][0]
        lines[first:last + 1] = body

    # Drop the equates and rewrite every reference to name the label directly.
    # No segment or size overrides are added here: assemble afterwards and let
    # the errors say what actually needs adjusting.
    lines = [l for l in lines
             if not re.match(r'^(%s)\s+equ\s' % '|'.join(eq), l)]
    out = []
    for ln in lines:
        for n in eq:
            ln = re.sub(r'\.%s\b' % n, n, ln)
            ln = re.sub(r'\b(mov\s+(?:bx|si|di|bp)\s*,\s*)%s\b(?!\[)' % n,
                        r'\1offset ' + n, ln)
        out.append(ln)

    backup = a86 + '.bak'
    shutil.copy2(a86, backup)
    write_text(a86, '\n'.join(out))
    if not verify:
        os.remove(backup)
        return
    r = rebuild(os.path.dirname(a86) or '.')
    if r.returncode == 0:
        os.remove(backup)
        print('OK  %d equates became data labels, byte-identical:' % len(eq))
        print('  ' + ' '.join(sorted(eq)))
    else:
        shutil.move(backup, a86)
        tail = (r.stdout + r.stderr).strip().splitlines()[-8:]
        print('FAIL mkvars - reverted:\n  %s' % '\n  '.join(tail))
        sys.exit(1)


def read_text_lines_split(lines, anchor, addr):
    """Ensure a data line starts at `addr`, splitting one if necessary."""
    for i, a, sz in data_lines(lines, anchor):
        if a == addr:
            return lines
        if a < addr < a + sz:
            parts = split_db_line(lines[i], addr - a)
            return lines[:i] + parts + lines[i + 1:]
    return lines


def cmd_mark(a86, prefix='xyz', verify=True):
    """Put a label on the storage each data-area equate points at.

    Only adds labels: the equates stay, references are untouched, so the
    encoding cannot change.  Splits a db/dw line when an equate points into
    the middle of one.
    """
    lines = read_text(a86).split('\n')
    anchor, image_end = get_bounds(lines)

    eq = {}
    for ln in lines:
        m = re.match(r'^(\w+)\s+equ\s+(0[0-9a-fA-F]*)h\s*(;.*)?$', ln)
        if m and m.group(1) not in ('data_org', 'image_end'):
            v = int(m.group(2), 16)
            if anchor <= v < image_end:
                eq.setdefault(v, []).append(m.group(1))
    if not eq:
        print('no data-area equates')
        return

    for a in sorted(eq):
        lines = read_text_lines_split(lines, anchor, a)

    added, skipped = [], []
    for i, a, sz in data_lines(lines, anchor):
        if a not in eq:
            continue
        if re.match(r'^\w', lines[i]):              # already carries a label
            skipped.append('%s@%04x' % (eq[a][0], a))
            continue
        name = prefix + eq[a][0]
        lines[i] = name + lines[i]
        added.append(name)

    backup = a86 + '.bak'
    shutil.copy2(a86, backup)
    write_text(a86, '\n'.join(lines))
    if not verify:
        os.remove(backup)
        return
    r = rebuild(os.path.dirname(a86) or '.')
    if r.returncode == 0:
        os.remove(backup)
        print('OK  %d labels added, byte-identical' % len(added))
        print('  ' + ' '.join(added))
        if skipped:
            print('  already labelled: ' + ' '.join(skipped))
    else:
        shutil.move(backup, a86)
        tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
        print('FAIL mark - reverted:\n  %s' % '\n  '.join(tail))
        sys.exit(1)


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


def cmd_unequ(a86, verify=True):
    """Replace each data-area equate with the label already on its storage.

    Expects `mark` to have run: the storage carries a label, so this only has
    to rename it, retype it when the variable is used as a word, repoint the
    references and delete the equate.
    """
    lines = read_text(a86).split('\n')
    text = '\n'.join(lines)
    anchor, image_end = get_bounds(lines)

    eqs, eqline = {}, {}
    for i, ln in enumerate(lines):
        m = re.match(r'^(\w+)\s+equ\s+(0[0-9a-fA-F]*)h\s*(;.*)?$', ln)
        if m and m.group(1) not in ('data_org', 'image_end'):
            v = int(m.group(2), 16)
            if anchor <= v < image_end:
                eqs[m.group(1)] = v
                eqline[m.group(1)] = (i, m.group(3) or '')
    if not eqs:
        print('no data-area equates left')
        return

    labelat = {}
    for i, a, sz in data_lines(lines, anchor):
        m = re.match(r'^(\w+)\s*(db|dw)\s', lines[i])
        if m:
            labelat[a] = (i, sz, m.group(1))

    done, missing = [], []
    for name, addr in sorted(eqs.items(), key=lambda kv: kv[1]):
        if addr not in labelat:
            missing.append('%s@%04x' % (name, addr))
            continue
        i, sz, lab = labelat[addr]
        lines[i] = re.sub(r'^%s' % lab, name, lines[i], count=1)
        if infer_width(text, name) == 'word' and lines[i].find('\tdb\t') > 0:
            rt = retype_word(lines[i])
            if rt:
                lines[i] = rt
        cmt = eqline[name][1]
        if cmt and ';' not in lines[i]:
            lines[i] += '\t' + cmt
        done.append(name)

    lines = [l for i, l in enumerate(lines)
             if not (re.match(r'^(%s)\s+equ\s' % '|'.join(done), l))]
    out = []
    for ln in lines:
        for n in done:
            ln = re.sub(r'\bxyz%s\b' % n, n, ln)
            # Order matters: `.name` is a memory reference and `name` an
            # immediate, so decide before the dot is stripped.  Getting this
            # backwards silently turns `mov bx,.sel` into `mov bx,offset sel`.
            ln = re.sub(r'\b(les|lds)(\s+\w+\s*,\s*)\.%s\b' % n,
                        r'\1\2dword ptr ' + n, ln)
            ln = re.sub(r'\b((?:mov|add|sub)\s+(?:bx|si|di|bp)\s*,\s*)'
                        r'(?<!\.)%s\b(?!\[)' % n, r'\1offset ' + n, ln)
            ln = re.sub(r'\.%s\b' % n, n, ln)
        out.append(ln)

    backup = a86 + '.bak'
    shutil.copy2(a86, backup)
    write_text(a86, '\n'.join(out))
    if not verify:
        os.remove(backup)
        return
    r = rebuild(os.path.dirname(a86) or '.')
    if r.returncode == 0:
        os.remove(backup)
        print('OK  %d equates replaced by labels, byte-identical' % len(done))
        if missing:
            print('  no storage label for: ' + ' '.join(missing))
    else:
        shutil.move(backup, a86)
        tail = (r.stdout + r.stderr).strip().splitlines()[-8:]
        print('FAIL unequ - reverted:\n  %s' % '\n  '.join(tail))
        sys.exit(1)


def cmd_names(a86):
    """List every lXXXX label with its reference count and following code,
    as raw material for a rename map."""
    lines = read_text(a86).split('\n')
    refs = {}
    for ln in lines:
        for m in re.finditer(r'\bl([0-9a-f]{4})\b', ln):
            if not ln.startswith('l' + m.group(1) + ':'):
                refs[m.group(1)] = refs.get(m.group(1), 0) + 1
    for i, ln in enumerate(lines):
        m = re.match(r'^l([0-9a-f]{4}):', ln)
        if not m:
            continue
        body = []
        for nxt in lines[i + 1:]:
            t = nxt.strip()
            if not t or t.startswith(';'):
                continue
            if re.match(r'^l[0-9a-f]{4}:', nxt):
                break
            body.append(re.sub(r'\s+', ' ', t))
            if len(body) >= 3:
                break
        print('l%s  refs=%-3d  %s' % (m.group(1), refs.get(m.group(1), 0),
                                      ' | '.join(body)))


def load_map(path):
    """old -> new, from a file of `old new [# comment]` lines."""
    ren = {}
    for ln in open(path):
        ln = ln.split('#')[0].strip()
        if not ln:
            continue
        parts = ln.split()
        if len(parts) != 2:
            sys.exit('bad map line: %s' % ln)
        ren[parts[0]] = parts[1]
    dups = [v for v in set(ren.values()) if list(ren.values()).count(v) > 1]
    if dups:
        sys.exit('duplicate target names: %s' % ', '.join(sorted(dups)))
    return ren


def cmd_rename(a86, mapfile, verify=True):
    ren = load_map(mapfile)
    text = read_text(a86)
    present = set(re.findall(r'\b\w+\b', text))
    # Entries already applied are dropped, so a map can be re-run safely.
    ren = {k: v for k, v in ren.items() if k in present}
    if not ren:
        print('nothing to rename (map already applied)')
        return
    existing = set(re.findall(r'^(\w+)[:\s]', text, re.M))
    clash = [v for v in ren.values() if v in existing and v not in ren]
    if clash:
        sys.exit('target name already used: %s' % ', '.join(sorted(clash)))

    pat = re.compile(r'\b(%s)\b' % '|'.join(sorted(ren, key=len, reverse=True)))
    out, nsub = [], 0
    for ln in text.split('\n'):
        parts = ln.split("'")
        for i in range(0, len(parts), 2):        # skip string literals
            new = pat.sub(lambda m: ren[m.group(1)], parts[i])
            if new != parts[i]:
                nsub += 1
            parts[i] = new
        out.append("'".join(parts))
    if nsub == 0:
        print('no occurrences found')
        return

    backup = a86 + '.bak'
    shutil.copy2(a86, backup)
    write_text(a86, '\n'.join(out))
    if not verify:
        os.remove(backup)
        return
    r = rebuild(os.path.dirname(a86) or '.')
    if r.returncode == 0:
        os.remove(backup)
        print('OK  %d names applied on %d lines, byte-identical'
              % (len(ren), nsub))
    else:
        shutil.move(backup, a86)
        tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
        print('FAIL rename - reverted:\n  %s' % '\n  '.join(tail))
        sys.exit(1)


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    base = 0
    verify = True
    if '--base' in a:
        i = a.index('--base'); base = int(a[i + 1], 16); del a[i:i + 2]
    if '--no-verify' in a:
        a.remove('--no-verify'); verify = False
    sub = a[0]
    if sub == 'gen':
        cmd_gen(a[1], a[2], int(a[3], 16), int(a[4], 16), base)
    elif sub == 'patch':
        cmd_patch(a[1], a[2], int(a[3], 16), int(a[4], 16), base, verify)
    elif sub == 'data':
        cmd_data(a[1], a[2], int(a[3], 16), int(a[4], 16), base, verify)
    elif sub == 'relabel':
        cmd_relabel(a[1], verify)
    elif sub == 'mklabel':
        cmd_mklabel(a[1], int(a[2], 16), a[3])
    elif sub == 'mklabels':
        cmd_mklabels(a[1], a[2] if len(a) > 2 else 'd', verify)
    elif sub == 'mkvars':
        cmd_mkvars(a[1], a[2], base, verify)
    elif sub == 'mark':
        cmd_mark(a[1], a[2] if len(a) > 2 else 'xyz', verify)
    elif sub == 'unequ':
        cmd_unequ(a[1], verify)
    elif sub == 'names':
        cmd_names(a[1])
    elif sub == 'rename':
        cmd_rename(a[1], a[2], verify)
    elif sub == 'labels':
        cmd_labels(a[1], a[2], base, int(a[3], 16), int(a[4], 16))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
