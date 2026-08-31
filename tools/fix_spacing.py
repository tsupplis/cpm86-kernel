#!/usr/bin/env python3
"""
fix_spacing.py  —  CPM86 ASM86 column formatter

Normalises instruction lines to:
    \t<mnemonic>\t<operand>\t\t; comment

Specifically:
  - 1 tab  before mnemonic   (already there after fix_indent)
  - 1 tab  between mnemonic and operand
  - comment (if any) padded to start at column 40 (tab-aligned)
  - lines without operands:  \t<mnemonic>\t\t\t\t; comment  (pad to col 40)

Lines left untouched:
  - blank lines
  - comment-only lines (start with ;)
  - col-0 label lines
  - assembler directive lines (DB, DW, EQU, ORG, etc.) — layout preserved
  - string data lines
"""

import re, sys

TABSIZE = 8
COMMENT_COL = 40   # target visual column for inline comments

DIRECTIVES = {
    'CSEG','DSEG','ORG','EQU','END',
    'DB','DW','DD','RB','RW','RD','RS',
    'IF','ENDIF','INCLUDE','PUBLIC','EXTRN',
}


def visual_col(s, tabsize=TABSIZE):
    """Return the visual column after string s (0-based)."""
    col = 0
    for c in s:
        if c == '\t':
            col = (col // tabsize + 1) * tabsize
        else:
            col += 1
    return col


def pad_to_col(current_col, target_col, tabsize=TABSIZE):
    """Return whitespace (tabs) to reach target_col from current_col."""
    if current_col >= target_col:
        return '\t'   # at least one space of separation
    tabs = ''
    col = current_col
    while col < target_col:
        next_stop = (col // tabsize + 1) * tabsize
        tabs += '\t'
        col = next_stop
    return tabs


def split_comment(t):
    """
    Split a line into (code_part, comment_part).
    Respects single-quoted strings so semicolons inside them are ignored.
    comment_part includes the leading ';', or is '' if no comment.
    """
    in_str = False
    for i, ch in enumerate(t):
        if ch == "'":
            in_str = not in_str
        if ch == ';' and not in_str:
            return t[:i].rstrip(), t[i:]
    return t.rstrip(), ''


def format_instr_line(t):
    """
    Reformat a single instruction line.
    Input has already been through fix_indent so it starts with \t<mnemonic>.
    """
    # Split off any trailing comment
    code, comment = split_comment(t)

    # Split code into tab-separated parts: ['', mnemonic, operand, ...]
    parts = code.split('\t')
    # parts[0] is '' (leading tab), parts[1] is mnemonic, parts[2+] is operand pieces
    if len(parts) < 2:
        return t   # safety: don't touch malformed lines

    mnemonic = parts[1]

    # Collect operand: everything after the mnemonic tab, stripped
    operand = '\t'.join(parts[2:]).strip() if len(parts) > 2 else ''

    # Build the new line
    if operand:
        body = '\t' + mnemonic + '\t' + operand
    else:
        body = '\t' + mnemonic

    if comment:
        col = visual_col(body)
        body += pad_to_col(col, COMMENT_COL)
        body += comment

    return body


def process(lines):
    out = []
    for line in lines:
        if line.endswith('\r\n'):
            eol, t = '\r\n', line[:-2]
        elif line.endswith('\n'):
            eol, t = '\n', line[:-1]
        else:
            eol, t = '', line

        # Leave blank lines, comment-only lines, col-0 lines untouched
        if t == '' or t.startswith(';') or (t and t[0] not in (' ', '\t')):
            out.append(t + eol)
            continue

        stripped = t.lstrip()

        # Leave directive lines untouched (DB, DW, ORG, EQU, RS, RB, RW…)
        first_word = re.match(r'[A-Za-z]+', stripped)
        if first_word and first_word.group().upper() in DIRECTIVES:
            out.append(t + eol)
            continue

        # Must start with \t and a lowercase letter (instruction line)
        if re.match(r'^\t[a-z]', t):
            out.append(format_instr_line(t) + eol)
            continue

        # Everything else (data lines, mixed content) — leave alone
        out.append(t + eol)

    return out


def main():
    if len(sys.argv) < 2:
        print("usage: fix_spacing.py <file.a86>", file=sys.stderr)
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
