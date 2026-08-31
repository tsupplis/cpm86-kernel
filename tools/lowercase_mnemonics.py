#!/usr/bin/env python3
"""
lowercase_mnemonics.py  —  CPM86 ASM86 style normaliser
Lowercases instruction mnemonics, registers, and instruction keywords
(byte ptr, word ptr, dword ptr, offset, cs:/ds:/es:/ss:)
while preserving labels, assembler directives, comments, and string literals.
"""

import re, sys

# ---------------------------------------------------------------------------
# Assembler directives — keep these UPPERCASE
# ---------------------------------------------------------------------------
DIRECTIVES = {
    'CSEG','DSEG','ORG','EQU','END',
    'DB','DW','DD','RB','RW','RD','RS',
    'IF','ENDIF','INCLUDE','PUBLIC','EXTRN',
}

# ---------------------------------------------------------------------------
# 8086 instruction mnemonics — lowercase these
# ---------------------------------------------------------------------------
MNEMONICS = {
    'AAA','AAD','AAM','AAS','ADC','ADD','AND',
    'CALL','CBW','CLC','CLD','CLI','CMC','CMP','CMPS','CMPSB','CMPSW',
    'CWD',
    'DAA','DAS','DEC','DIV',
    'ESC',
    'HLT',
    'IDIV','IMUL','IN','INC','INT','INTO','IRET',
    'JCXZ',
    'JA','JAE','JB','JBE','JC','JE','JG','JGE','JL','JLE',
    'JMP','JMPS',
    'JNA','JNAE','JNB','JNBE','JNC','JNE','JNG','JNGE','JNL','JNLE',
    'JNO','JNP','JNS','JNZ','JO','JP','JPE','JPO','JS','JZ',
    'LAHF','LDS','LEA','LES','LOCK','LODS','LODSB','LODSW',
    'LOOP','LOOPE','LOOPNE','LOOPNZ','LOOPZ',
    'MOV','MOVS','MOVSB','MOVSW','MUL',
    'NEG','NOP','NOT',
    'OR','OUT',
    'POP','POPF','PUSH','PUSHF',
    'RCL','RCR','REP','REPE','REPNE','REPNZ','REPZ',
    'RET','RETF','RETN','ROL','ROR',
    'SAHF','SAL','SAR','SBB','SCAS','SCASB','SCASW',
    'SHL','SHR','STC','STD','STI','STOS','STOSB','STOSW','SUB',
    'TEST',
    'WAIT',
    'XCHG','XLAT','XOR',
}

# ---------------------------------------------------------------------------
# Registers — lowercase these
# ---------------------------------------------------------------------------
REGISTERS = {
    'AX','BX','CX','DX',
    'AH','AL','BH','BL','CH','CL','DH','DL',
    'SP','BP','SI','DI',
    'CS','DS','ES','SS',
    'IP','FLAGS',
}

# ---------------------------------------------------------------------------
# Instruction keywords — lowercase these (as words)
# ---------------------------------------------------------------------------
KEYWORDS = {
    'BYTE','WORD','DWORD','PTR','OFFSET','SHORT','NEAR','FAR',
}

# Build a combined set of all tokens to lowercase
LOWER_TOKENS = MNEMONICS | REGISTERS | KEYWORDS

# ---------------------------------------------------------------------------
# Token splitter
# Order matters: more specific patterns first.
# Groups: string_lit | comment | hex_lit | ident | other
# ---------------------------------------------------------------------------
SPLIT_RE = re.compile(
    r"('(?:[^']|'')*')"                  # 1: single-quoted string literal
    r'|(;.*$)'                            # 2: comment to end of line
    r'|([0-9][0-9A-Fa-f]*[Hh])'          # 3: hex literal with digit start (e.g. 0FFh, 34DCh, 1h)
    r'|([A-Za-z_][A-Za-z0-9_]*)'         # 4: identifier / keyword / label
    r'|([0-9]+)',                         # 5: decimal number
    re.MULTILINE,
)

def process_line(line: str) -> str:
    """Process one source line, lowercasing only mnemonic/register/keyword tokens."""
    result = []
    pos = 0
    length = len(line)

    for m in SPLIT_RE.finditer(line):
        # Append any literal text between last match and this one (spaces, punctuation, etc.)
        if m.start() > pos:
            result.append(line[pos:m.start()])
        pos = m.end()

        string_lit, comment, hex_lit, ident, decimal = m.groups()

        if comment is not None:
            result.append(comment)
        elif string_lit is not None:
            result.append(string_lit)
        elif hex_lit is not None:
            # Preserve hex literals exactly as written
            result.append(hex_lit)
        elif decimal is not None:
            # Decimal number: keep as-is
            result.append(decimal)
        elif ident is not None:
            col = m.start()
            upper = ident.upper()

            # Identifier at column 0 is always a label definition — keep as-is
            if col == 0:
                result.append(ident)
                continue

            # Assembler directives — keep uppercase
            if upper in DIRECTIVES:
                result.append(ident)
                continue

            # Mnemonic, register, or keyword — lowercase
            if upper in LOWER_TOKENS:
                result.append(ident.lower())
                continue

            # Everything else (user labels, EQU names, TRUE/FALSE constants, etc.): keep as-is
            result.append(ident)

    # Append any trailing text after the last match
    if pos < length:
        result.append(line[pos:])

    return ''.join(result)


def main():
    if len(sys.argv) < 2:
        print("usage: lowercase_mnemonics.py <file.a86>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    with open(path, 'rb') as f:
        raw = f.read()

    # Detect and preserve line ending style
    crlf = b'\r\n' in raw
    text = raw.decode('latin-1')
    lines = text.splitlines(keepends=True)

    out = []
    for line in lines:
        # Strip any line ending for processing, remember what it was
        ending = ''
        if line.endswith('\r\n'):
            ending = '\r\n'
            stripped = line[:-2]
        elif line.endswith('\n'):
            ending = '\n'
            stripped = line[:-1]
        else:
            ending = ''
            stripped = line

        # Preserve blank lines and pure comment lines untouched
        if stripped == '' or stripped.lstrip().startswith(';'):
            out.append(stripped + ending)
        else:
            out.append(process_line(stripped) + ending)

    with open(path, 'wb') as f:
        f.write(''.join(out).encode('latin-1'))

    print(f"Done: {path}")

if __name__ == '__main__':
    main()
