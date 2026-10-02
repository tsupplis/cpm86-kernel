"""The subcommands. Each one mutates the source and verifies it."""

import os
import re
import subprocess
import sys

from .build import verified_write
from .disasm import Converter, disasm
from .source import (data_lines, emit_data, find_region, get_bounds,
                     infer_width, load_equates, load_labels,
                     read_text_lines_split, retype_word)
from .symbols import (assemble_sym, load_sym, relabel_line, scan_unresolved)
from .text import lbl, num, read_text, write_text


def cmd_gen(binf, a86, start, end, base):
    conv = Converter(load_labels(a86), load_equates(a86), start, end)
    print('\n'.join(conv.render(disasm(binf, start, end, base))))



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

    ndb = sum(1 for l in new if re.match(r'^\tdb\t0', l))
    verified_write(a86, new, verify, what='l%04x..%04x' % (start, end),
                   ok='OK  l%04x..%04x decoded, byte-identical '
                      '(%d db lines left)' % (start, end, ndb))


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

    verified_write(a86, new, verify, what='data %04x..%04x' % (start, end),
                   ok='OK  data %04x..%04x converted, byte-identical'
                      % (start, end))


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
        verified_write(a86, new, True, what='relabel',
                       ok='OK  %d lines relabelled, byte-identical' % nsub)
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

    verified_write(a86, lines, verify, what='mklabels',
                   ok='OK  %d equates added and substituted, byte-identical:'
                      '\n  %s' % (len(todo),
                                  ' '.join('%s%04x' % (prefix, a)
                                           for a in todo)))


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
        m = re.match(r'^(\w+)\s+equ\s+([0-9][0-9a-fA-F]*)h\s*(;.*)?$', ln)
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

    verified_write(a86, out, verify, what='mkvars', tail=8,
                   ok='OK  %d equates became data labels, byte-identical:'
                      '\n  %s' % (len(eq), ' '.join(sorted(eq))))


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
        m = re.match(r'^(\w+)\s+equ\s+([0-9][0-9a-fA-F]*)h\s*(;.*)?$', ln)
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

    msg = 'OK  %d labels added, byte-identical\n  %s' % (len(added),
                                                        ' '.join(added))
    if skipped:
        msg += '\n  already labelled: ' + ' '.join(skipped)
    verified_write(a86, lines, verify, what='mark', ok=msg)


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
        m = re.match(r'^(\w+)\s+equ\s+([0-9][0-9a-fA-F]*)h\s*(;.*)?$', ln)
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

    msg = 'OK  %d equates replaced by labels, byte-identical' % len(done)
    if missing:
        msg += '\n  no storage label for: ' + ' '.join(missing)
    verified_write(a86, out, verify, what='unequ', tail=8, ok=msg)


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

    verified_write(a86, out, verify, what='rename',
                   ok='OK  %d names applied on %d lines, byte-identical'
                      % (len(ren), nsub))
