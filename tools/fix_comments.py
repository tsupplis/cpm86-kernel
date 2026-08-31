#!/usr/bin/env python3
"""
fix_comments.py  —  CPM86 ASM86 comment style normaliser

Rules applied to standalone comment lines (col 0, starting with ';'):

1. Box headers  ';***...' / ';* text *'  →  ';----------------------------------------'
                                              '; <text>'
                                              ';----------------------------------------'
   (empty box padding lines dropped)

2. Tab-indented  ';\t<text>'  →  '; <text>'

3. No-space      ';<text>'    →  '; <text>'
   (except ';-' lines which are already separators, and ';' alone)

4. '; ------' style separators normalised to ';----------------------------------------'
   (the standard 40-dash form already dominant in the file)

Inline comments (after code) are left completely untouched.
"""

import re, sys

SEP = ';' + '-' * 40        # standard separator line
SEP_RE = re.compile(r'^;[-=]{3,}\s*$')   # any run of dashes or equals


def extract_box_title(box_lines):
    """
    Given a list of raw lines forming a ;*...*  box, extract the non-empty
    text lines (strip the border padding lines that contain only spaces/stars).
    Returns list of text strings.
    """
    titles = []
    for t in box_lines:
        # Strip leading ;* and trailing *
        inner = re.sub(r'^;\*\s*', '', t)
        inner = re.sub(r'\s*\*\s*$', '', inner).strip()
        # Skip if what remains is empty or all stars (border rows)
        if not inner or re.match(r'^\*+$', inner):
            continue
        titles.append(inner)
    return titles


def process(lines):
    out = []
    i = 0
    n = len(lines)

    while i < n:
        raw = lines[i]
        if raw.endswith('\r\n'):
            eol, t = '\r\n', raw[:-2]
        elif raw.endswith('\n'):
            eol, t = '\n', raw[:-1]
        else:
            eol, t = '', raw

        # ── Not a standalone comment line: pass through ──────────────────
        if not t.lstrip().startswith(';') or not (t == t.lstrip()):
            # either not a comment, or an inline comment on a code line
            out.append(t + eol)
            i += 1
            continue

        # From here: t starts at col 0 with ';'

        # ── 1. Box header: starts with ;*** ──────────────────────────────
        if re.match(r'^;\*{3,}', t):
            # Collect the whole box (border + content + closing border)
            box = []
            j = i
            while j < n:
                raw_j = lines[j]
                tj = raw_j[:-2] if raw_j.endswith('\r\n') else \
                     raw_j[:-1] if raw_j.endswith('\n') else raw_j
                if re.match(r'^;\*', tj):
                    box.append(tj)
                    j += 1
                else:
                    break
            titles = extract_box_title(box)
            if titles:
                out.append(SEP + eol)
                for title in titles:
                    out.append('; ' + title + eol)
                out.append(SEP + eol)
            else:
                out.append(SEP + eol)
            i = j
            continue

        # ── 2. Separator variants: normalise to standard SEP ─────────────
        # Also catch '; ----' (space then dashes) used in a few places
        if SEP_RE.match(t) or re.match(r'^; [-=]{3,}\s*$', t):
            out.append(SEP + eol)
            i += 1
            continue

        # ── 3. Tab-indented comment: ';\t...' → '; ...' ──────────────────
        if t.startswith(';\t'):
            # Collapse multiple leading tabs to a single space
            body = t[1:].lstrip('\t')
            # Preserve internal tab alignment in Exit/Entry lines
            # e.g.  ';\tExit:\tAL = ...' → '; Exit:  AL = ...'
            # Replace internal tabs with spaces (2 spaces to keep readable)
            body = body.replace('\t', '  ')
            out.append('; ' + body + eol)
            i += 1
            continue

        # ── 4. No-space comment: ';text' → '; text' ─────────────────────
        if len(t) > 1 and t[1] not in (' ', '\t', '-', '=', '*', '\r', '\n'):
            out.append('; ' + t[1:] + eol)
            i += 1
            continue

        # ── Everything else: pass through ────────────────────────────────
        out.append(t + eol)
        i += 1

    return out


def main():
    if len(sys.argv) < 2:
        print("usage: fix_comments.py <file.a86>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    with open(path, 'rb') as f:
        raw = f.read()

    lines = raw.decode('latin-1').splitlines(keepends=True)
    out = process(lines)

    with open(path, 'wb') as f:
        f.write(''.join(out).encode('latin-1'))

    print(f"Done: {path}")


if __name__ == '__main__':
    main()
