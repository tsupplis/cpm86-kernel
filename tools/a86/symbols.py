"""RASM-86 .sym parsing and numeric-address substitution."""

import os
import re
import subprocess
import sys

from .source import IMAGE_END


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
RE_ABS = re.compile(r'\.([0-9][0-9a-fA-F]*h)\b')          # .08f3h
RE_IDX = re.compile(r'\b([0-9][0-9a-fA-F]*h)(\[)')        # 08ffh[bx]
# Must not match when an index follows: `mov si,07d2h[di]` reads the table,
# it does not load its address.
RE_PTR = re.compile(r'\b(mov\s+(?:bx|si|di|bp)\s*,\s*)([0-9][0-9a-fA-F]*h)(?!\s*\[)\b')


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
