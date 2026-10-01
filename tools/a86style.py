#!/usr/bin/env python3
"""
a86style.py - ASM86 source style normaliser for this repo.

Replaces fix_indent.py, lowercase_mnemonics.py, fix_spacing.py and
fix_comments.py.  Those four had to run in exactly that order and nothing said
so: fix_spacing only matches lines whose mnemonic is already lowercase, so run
before lowercase_mnemonics it matched nothing, changed nothing, and still
reported success.  Folding them into one tool removes the ordering hazard.

Phases, applied in this order:

  indent     split "LABEL:<tab>instr" onto two lines, space indent -> one tab
  mnemonics  lowercase mnemonics, registers and ptr/offset/segment keywords
  spacing    <tab>mnemonic<tab>operand, inline comment aligned to column 40
  layout     comment-line layout: box headers and separators, "; " prefix
  case       ALL-CAPS comment prose -> sentence case, identifiers preserved

Only the `case` phase is new.  It lowercases prose inside comments but keeps
anything that names something: registers, well-known acronyms, and every
uppercase symbol the file itself defines or references in code.  That symbol
set is read from the source, so it stays correct per file.

Comments, whitespace and letter case in code do not affect the assembled
bytes.  Verify with `make check` in the repo root for the kernel, or in
commands/<tool> for the utilities.

usage:  a86style.py [--check] [--only phase,phase] <file.a86> ...
        --check   report what would change, write nothing
        --only    run just these phases (default: all)
"""

import re
import sys

PHASES = ['indent', 'mnemonics', 'spacing', 'layout', 'case']

TABSIZE = 8
COMMENT_COL = 40
SEP = ';' + '-' * 40

DIRECTIVES = {
    'CSEG', 'DSEG', 'ORG', 'EQU', 'END',
    'DB', 'DW', 'DD', 'RB', 'RW', 'RD', 'RS',
    'IF', 'ENDIF', 'INCLUDE', 'PUBLIC', 'EXTRN',
}

MNEMONICS = {
    'AAA', 'AAD', 'AAM', 'AAS', 'ADC', 'ADD', 'AND',
    'CALL', 'CBW', 'CLC', 'CLD', 'CLI', 'CMC', 'CMP', 'CMPS', 'CMPSB', 'CMPSW',
    'CWD', 'DAA', 'DAS', 'DEC', 'DIV', 'ESC', 'HLT',
    'IDIV', 'IMUL', 'IN', 'INC', 'INT', 'INTO', 'IRET', 'JCXZ',
    'JA', 'JAE', 'JB', 'JBE', 'JC', 'JE', 'JG', 'JGE', 'JL', 'JLE',
    'JMP', 'JMPS',
    'JNA', 'JNAE', 'JNB', 'JNBE', 'JNC', 'JNE', 'JNG', 'JNGE', 'JNL', 'JNLE',
    'JNO', 'JNP', 'JNS', 'JNZ', 'JO', 'JP', 'JPE', 'JPO', 'JS', 'JZ',
    'LAHF', 'LDS', 'LEA', 'LES', 'LOCK', 'LODS', 'LODSB', 'LODSW',
    'LOOP', 'LOOPE', 'LOOPNE', 'LOOPNZ', 'LOOPZ',
    'MOV', 'MOVS', 'MOVSB', 'MOVSW', 'MUL',
    'NEG', 'NOP', 'NOT', 'OR', 'OUT',
    'POP', 'POPF', 'PUSH', 'PUSHF',
    'RCL', 'RCR', 'REP', 'REPE', 'REPNE', 'REPNZ', 'REPZ',
    'RET', 'RETF', 'RETN', 'ROL', 'ROR',
    'SAHF', 'SAL', 'SAR', 'SBB', 'SCAS', 'SCASB', 'SCASW',
    'SHL', 'SHR', 'STC', 'STD', 'STI', 'STOS', 'STOSB', 'STOSW', 'SUB',
    'TEST', 'WAIT', 'XCHG', 'XLAT', 'XOR',
}

REGISTERS = {
    'AX', 'BX', 'CX', 'DX',
    'AH', 'AL', 'BH', 'BL', 'CH', 'CL', 'DH', 'DL',
    'SP', 'BP', 'SI', 'DI',
    'CS', 'DS', 'ES', 'SS',
    'IP', 'FLAGS',
}

KEYWORDS = {'BYTE', 'WORD', 'DWORD', 'PTR', 'OFFSET', 'SHORT', 'NEAR', 'FAR'}

LOWER_TOKENS = MNEMONICS | REGISTERS | KEYWORDS | DIRECTIVES

# Terms that are names, not prose, and must survive the case phase.
ACRONYMS = {
    'CP/M', 'I/O', 'R/O', 'R/W', 'A/D',
    'BDOS', 'BIOS', 'CCP', 'XIOS', 'CBIOS', 'TPA', 'DRI', 'DMA',
    'FCB', 'DPB', 'DPH', 'DIRBUF', 'ALV', 'CSV',
    'IBM', 'PC', 'XT', 'AT', 'MSDOS', 'DOS', 'ROM', 'RAM', 'CPU', 'ALU',
    'ASCII', 'EBCDIC', 'CR', 'LF', 'NUL', 'EOF', 'ESC', 'TAB', 'BS',
    'MSB', 'LSB', 'LSW', 'MSW', 'BCD', 'HEX',
    'CON', 'LST', 'AUX', 'PUN', 'RDR', 'USR', 'TTY', 'CRT', 'UC1',
    'CMD', 'COM', 'SUB', 'SYS', 'PFK',
    'LBA', 'CHS', 'FAT', 'MBR', 'DPT',
    'FIFO', 'LIFO', 'TOS',
    'OK', 'ID', 'NO', 'OS',
}

SEP_RE = re.compile(r'^;[-=]{3,}\s*$')
LABEL_INSTR_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):([ \t]+)([^;\s]\S*.*)')
SPACE_INDENT_RE = re.compile(r'^( +)(\S.*)')

SPLIT_RE = re.compile(
    r"('(?:[^']|'')*')"                 # 1 string literal
    r'|(;.*$)'                          # 2 comment
    r'|([0-9][0-9A-Fa-f]*[Hh])'         # 3 hex literal
    r'|([A-Za-z_][A-Za-z0-9_]*)'        # 4 identifier
    r'|(.)',                            # 5 anything else
    re.S)


def split_eol(line):
    if line.endswith('\r\n'):
        return line[:-2], '\r\n'
    if line.endswith('\n'):
        return line[:-1], '\n'
    return line, ''


def split_comment(t):
    """Split into (code, comment). Quote-aware, so ';' inside a string is safe."""
    i = comment_index(t)
    if i < 0:
        return t.rstrip(), ''
    return t[:i].rstrip(), t[i:]


def comment_index(t):
    """Index of the comment's ';', or -1. Quote-aware."""
    in_str = False
    for i, ch in enumerate(t):
        if ch == "'":
            in_str = not in_str
        elif ch == ';' and not in_str:
            return i
    return -1


def visual_col(s):
    col = 0
    for c in s:
        col = (col // TABSIZE + 1) * TABSIZE if c == '\t' else col + 1
    return col


def pad_to_col(current, target):
    if current >= target:
        return '\t'
    tabs = ''
    col = current
    while col < target:
        col = (col // TABSIZE + 1) * TABSIZE
        tabs += '\t'
    return tabs


# --------------------------------------------------------------------------
# phase: indent
# --------------------------------------------------------------------------
def phase_indent(lines):
    out = []
    for line in lines:
        t, eol = split_eol(line)
        m = LABEL_INSTR_RE.match(t)
        if m:
            label, _ws, rest = m.groups()
            out.append(label + ':' + eol)
            out.append('\t' + rest + eol)
            continue
        m = SPACE_INDENT_RE.match(t)
        if m and not t.lstrip().startswith(';'):
            out.append('\t' + t.lstrip() + eol)
            continue
        out.append(t + eol)
    return out


# --------------------------------------------------------------------------
# phase: mnemonics
# --------------------------------------------------------------------------
def phase_mnemonics(lines):
    out = []
    for line in lines:
        t, eol = split_eol(line)
        if t.lstrip().startswith(';') or not t.strip():
            out.append(t + eol)
            continue
        buf = []
        for m in SPLIT_RE.finditer(t):
            lit, com, hexlit, ident, other = m.groups()
            if lit is not None:
                buf.append(lit)
            elif com is not None:
                buf.append(com)
            elif hexlit is not None:
                buf.append(hexlit[:-1] + hexlit[-1].lower())
            elif ident is not None:
                buf.append(ident.lower() if ident.upper() in LOWER_TOKENS
                           else ident)
            else:
                buf.append(other)
        out.append(''.join(buf) + eol)
    return out


# --------------------------------------------------------------------------
# phase: spacing
# --------------------------------------------------------------------------
def phase_spacing(lines):
    out = []
    for line in lines:
        t, eol = split_eol(line)
        if t == '' or t.startswith(';') or (t and t[0] not in (' ', '\t')):
            out.append(t + eol)
            continue
        stripped = t.lstrip()
        first = re.match(r'[A-Za-z]+', stripped)
        if first and first.group().upper() in DIRECTIVES:
            out.append(t + eol)
            continue
        # Mnemonics have been lowercased by now; match either case so the
        # phase still works when run on its own.
        if re.match(r'^\t[A-Za-z]', t):
            code, comment = split_comment(t)
            parts = code.split('\t')
            if len(parts) < 2:
                out.append(t + eol)
                continue
            mnemonic = parts[1]
            operand = '\t'.join(parts[2:]).strip() if len(parts) > 2 else ''
            body = '\t' + mnemonic + ('\t' + operand if operand else '')
            if comment:
                body += pad_to_col(visual_col(body), COMMENT_COL) + comment
            out.append(body + eol)
            continue
        out.append(t + eol)
    return out


# --------------------------------------------------------------------------
# phase: layout
# --------------------------------------------------------------------------
def extract_box_title(box):
    titles = []
    for t in box:
        inner = re.sub(r'^;\*\s*', '', t)
        inner = re.sub(r'\s*\*\s*$', '', inner).strip()
        if not inner or re.match(r'^\*+$', inner):
            continue
        titles.append(inner)
    return titles


def phase_layout(lines):
    out = []
    i, n = 0, len(lines)
    while i < n:
        t, eol = split_eol(lines[i])
        if not t.lstrip().startswith(';') or t != t.lstrip():
            out.append(t + eol)
            i += 1
            continue

        if re.match(r'^;\*{3,}', t):
            box, j = [], i
            while j < n:
                tj, _ = split_eol(lines[j])
                if re.match(r'^;\*', tj):
                    box.append(tj)
                    j += 1
                else:
                    break
            titles = extract_box_title(box)
            out.append(SEP + eol)
            for title in titles:
                out.append('; ' + title + eol)
            if titles:
                out.append(SEP + eol)
            i = j
            continue

        if SEP_RE.match(t) or re.match(r'^; [-=]{3,}\s*$', t):
            out.append(SEP + eol)
            i += 1
            continue

        if t.startswith(';\t'):
            body = t[1:].lstrip('\t').replace('\t', '  ')
            out.append('; ' + body + eol)
            i += 1
            continue

        if len(t) > 1 and t[1] not in (' ', '\t', '-', '=', '*', '\r', '\n'):
            out.append('; ' + t[1:] + eol)
            i += 1
            continue

        out.append(t + eol)
        i += 1
    return out


# --------------------------------------------------------------------------
# phase: case
# --------------------------------------------------------------------------
# A word that may carry a '/' so CP/M and READ/WRITE are single tokens.
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_/']*")

WORDLIST = '/usr/share/dict/words'


def load_english():
    """Common English words, used to tell prose from symbol names.

    Labels in this codebase are ordinary words (OPEN, FILE, SEARCH, MEMORY),
    so "appears in the code" alone is not enough to mark a token as a name.
    Without a word list we keep only registers and acronyms, which lowercases
    a few genuine symbol references but never leaves prose half-capitalised.
    """
    try:
        with open(WORDLIST, 'r', encoding='latin-1') as f:
            return {w.strip().lower() for w in f if len(w.strip()) > 1}
    except OSError:
        return None


def collect_symbols(lines):
    """Uppercase identifiers used in the code part of the file."""
    syms = set()
    for line in lines:
        t, _ = split_eol(line)
        code, _comment = split_comment(t)
        if not code.strip():
            continue
        for m in re.finditer(r'[A-Za-z_][A-Za-z0-9_]*', code):
            w = m.group()
            if w.isupper() and w not in DIRECTIVES and w not in LOWER_TOKENS:
                syms.add(w)
    return syms


def normalise_comment_body(body, keep, symbols, english):
    """Lowercase ALL-CAPS prose, leave anything that names something."""
    def repl(m):
        w = m.group()
        u = w.upper()
        if u in keep:                       # registers, acronyms
            return w
        if any(c.isdigit() or c == '_' for c in w):   # B0-4, 21H, F1
            return w
        if len(w) == 1:                     # drive letters
            return w
        if not w.isupper():                 # already mixed or lower
            return w
        if u in symbols and (english is None or u.lower() not in english):
            return w                        # a real symbol, not a word
        return w.lower()

    return WORD_RE.sub(repl, body)


def sentence_case(body):
    """Capitalise the first letter of the prose, if it starts lowercase."""
    # Commented-out code is not prose; leave it looking like code.
    first = WORD_RE.match(body.lstrip())
    if first and first.group().upper() in MNEMONICS:
        return body
    for i, ch in enumerate(body):
        if ch.isalpha():
            word = WORD_RE.match(body[i:])
            if word and word.group().isupper():
                return body
            return body[:i] + ch.upper() + body[i + 1:]
        if ch not in ' \t':
            return body
    return body


def phase_case(lines):
    keep = {w.upper() for w in REGISTERS | ACRONYMS}
    symbols = collect_symbols(lines)
    english = load_english()
    out = []
    for line in lines:
        t, eol = split_eol(line)
        i = comment_index(t)
        if i < 0:
            out.append(t + eol)
            continue
        code = t[:i]            # keep the original alignment whitespace
        comment = t[i:]
        m = re.match(r'^(;+)(\s*)(.*)$', comment, re.S)
        if not m:
            out.append(t + eol)
            continue
        marks, gap, body = m.groups()
        if not body.strip() or re.match(r'^[-=*]+$', body.strip()):
            out.append(t + eol)
            continue
        new = normalise_comment_body(body, keep, symbols, english)
        if not code.strip():
            new = sentence_case(new)
        out.append(code + marks + gap + new + eol)
    return out


PHASE_FN = {
    'indent': phase_indent,
    'mnemonics': phase_mnemonics,
    'spacing': phase_spacing,
    'layout': phase_layout,
    'case': phase_case,
}


def main():
    args = sys.argv[1:]
    check = False
    only = PHASES
    files = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == '--check':
            check = True
        elif a == '--only':
            i += 1
            only = [p.strip() for p in args[i].split(',')]
            bad = [p for p in only if p not in PHASE_FN]
            if bad:
                sys.exit(f"unknown phase(s): {', '.join(bad)}\n"
                         f"available: {', '.join(PHASES)}")
        elif a.startswith('-'):
            sys.exit(f"unknown option {a}")
        else:
            files.append(a)
        i += 1

    if not files:
        sys.exit(__doc__.strip().splitlines()[-4].strip())

    rc = 0
    for path in files:
        with open(path, 'rb') as f:
            original = f.read()
        lines = original.decode('latin-1').splitlines(keepends=True)

        changed = []
        for p in PHASES:
            if p not in only:
                continue
            before = lines
            lines = PHASE_FN[p](lines)
            if lines != before:
                changed.append(p)

        new = ''.join(lines).encode('latin-1')
        if new == original:
            print(f"{path}: already normalised")
            continue

        n = sum(1 for a, b in zip(original.split(b'\n'), new.split(b'\n'))
                if a != b)
        if check:
            print(f"{path}: would change ~{n} lines ({', '.join(changed)})")
            rc = 1
        else:
            with open(path, 'wb') as f:
                f.write(new)
            print(f"{path}: {n} lines ({', '.join(changed)})")
    return rc


if __name__ == '__main__':
    sys.exit(main())
