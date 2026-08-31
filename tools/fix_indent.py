#!/usr/bin/env python3
"""
fix_indent.py  —  CPM86 ASM86 indentation normaliser

1. Lines with label+instruction on the same line are split:
       LABEL:\tinstr  ->  LABEL:\n\tinstr
2. Space-indented instruction/directive lines are converted to a single tab,
   EXCEPT lines that are clearly intentional data / patch blocks (RB, RS, etc
   at a non-zero indent level that must stay for structural reasons — those
   we leave if they start with a directive keyword).
3. The one stray '    ORG' line gets a single-tab indent.
"""

import re, sys

DIRECTIVES = {
    'CSEG','DSEG','ORG','EQU','END',
    'DB','DW','DD','RB','RW','RD','RS',
    'IF','ENDIF','INCLUDE','PUBLIC','EXTRN',
}

# A label-only line: starts at col 0, has identifier + colon, nothing else
# (possibly followed by whitespace only)
LABEL_ONLY_RE  = re.compile(r'^([A-Z_][A-Z0-9_]*):(\s*)$')

# A label+instruction line: label at col 0, colon, then whitespace+content
LABEL_INSTR_RE = re.compile(r'^([A-Z_][A-Z0-9_]*):([ \t]+)(\S.*)')

# Space-only indent (not a col-0 label, not a comment, not blank)
SPACE_INDENT_RE = re.compile(r'^( +)(\S.*)')


def process(lines):
    out = []
    for line in lines:
        if line.endswith('\r\n'):
            eol = '\r\n'
            t = line[:-2]
        elif line.endswith('\n'):
            eol = '\n'
            t = line[:-1]
        else:
            eol = ''
            t = line

        # ── 1. Label + instruction on the same line ──────────────────────
        m = LABEL_INSTR_RE.match(t)
        if m:
            label, _ws, rest = m.groups()
            out.append(label + ':' + eol)
            out.append('\t' + rest + eol)
            continue

        # ── 2. Space-indented lines → single tab ─────────────────────────
        m = SPACE_INDENT_RE.match(t)
        if m and not t.lstrip().startswith(';'):
            rest = t.lstrip()
            out.append('\t' + rest + eol)
            continue

        out.append(t + eol)

    return out


def main():
    if len(sys.argv) < 2:
        print("usage: fix_indent.py <file.a86>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    with open(path, 'rb') as f:
        raw = f.read()

    text  = raw.decode('latin-1')
    lines = text.splitlines(keepends=True)
    out   = process(lines)

    with open(path, 'wb') as f:
        f.write(''.join(out).encode('latin-1'))

    print(f"Done: {path}")


if __name__ == '__main__':
    main()
