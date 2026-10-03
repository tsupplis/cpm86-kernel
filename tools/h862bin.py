#!/usr/bin/env python3
"""h862bin - turn an assembler hex file into a flat image.

usage: h862bin.py FILE.h86 OUT.bin     the raw bytes
       h862bin.py FILE.h86 OUT.inc     the same as db lines, labelled OUT

Reads Intel hex (record type 00) and the flavour ASM-86 writes by default
(81..84 for code, data, stack and extra).  The image runs from the lowest to
the highest address the records cover, so it is exactly as long as the
assembled program: no origin to skip, no padding to cut.

It refuses what it cannot be sure of: a bad checksum, a record type it does
not know, an address covered twice, a hole inside the image, or no end of
file record.  Whatever follows the end of file record is ignored, which
covers the ^Z and stale buffer a CP/M tool leaves at the end of the file.
"""
import os
import sys

DATA = (0x00, 0x81, 0x82, 0x83, 0x84)


def read_hex(path):
    """address -> byte, from the records up to the end of file record."""
    mem = {}
    seen_eof = False
    with open(path, 'rb') as f:
        lines = f.read().decode('latin-1').replace('\r', '').split('\n')
    for n, ln in enumerate(lines, 1):
        ln = ln.strip()
        if not ln:
            continue
        where = '%s:%d' % (os.path.basename(path), n)
        if not ln.startswith(':'):
            raise ValueError('%s: not a hex record' % where)
        try:
            rec = bytes.fromhex(ln[1:])
        except ValueError:
            raise ValueError('%s: not hexadecimal' % where)
        if len(rec) < 5 or len(rec) != rec[0] + 5:
            raise ValueError('%s: record length does not match' % where)
        if sum(rec) & 0xff:
            raise ValueError('%s: bad checksum' % where)
        addr = rec[1] << 8 | rec[2]
        typ = rec[3]
        if typ == 0x01:
            seen_eof = True
            break
        if typ == 0x03:                 # start address: not part of the image
            continue
        if typ not in DATA:
            raise ValueError('%s: unknown record type %02x' % (where, typ))
        for i, b in enumerate(rec[4:-1]):
            a = addr + i
            if a in mem:
                raise ValueError('%s: address %04x is covered twice'
                                 % (where, a))
            mem[a] = b
    if not seen_eof:
        raise ValueError('%s: no end of file record' % os.path.basename(path))
    if not mem:
        raise ValueError('%s: no data records' % os.path.basename(path))
    return mem


def image(path):
    """(first address, bytes) of the whole image."""
    mem = read_hex(path)
    lo, hi = min(mem), max(mem)
    for a in range(lo, hi + 1):
        if a not in mem:
            raise ValueError('%s: hole in the image at %04x'
                             % (os.path.basename(path), a))
    return lo, bytes(mem[a] for a in range(lo, hi + 1))


def _hexlit(b):
    s = '%02xh' % b
    return '0' + s if s[0] in 'abcdef' else s


def _tokens(data):
    """Printable runs of four or more bytes as strings, the rest as hex."""
    out, i = [], 0
    while i < len(data):
        j = i
        while j < len(data) and 0x20 <= data[j] < 0x7f and data[j] != 0x27:
            j += 1
        if j - i >= 4:
            while i < j:
                chunk = data[i:min(j, i + 40)]
                out.append("'%s'" % chunk.decode('ascii'))
                i += len(chunk)
        else:
            out.append(_hexlit(data[i]))
            i += 1
    return out


def to_inc(data, label, source):
    lines = ['; Generated from %s by h862bin; do not edit.' % source]
    cur, first = [], True
    for tok in _tokens(data) + [None]:
        if tok is None or len(cur) >= 12 or \
                sum(len(t) + 1 for t in cur) + len(tok or '') > 60:
            if cur:
                lines.append('%s\tdb\t%s' % (label if first else '',
                                             ','.join(cur)))
                first, cur = False, []
        if tok is not None:
            cur.append(tok)
    return ('\r\n'.join(lines) + '\r\n').encode('ascii')


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__.split('\n\n')[0] + '\n\n' +
                 '\n'.join(__doc__.split('\n\n')[1].split('\n')))
    src, dst = argv
    ext = os.path.splitext(dst)[1].lower()
    if ext not in ('.bin', '.inc'):
        sys.exit('h862bin: the output must be .bin or .inc, not %s' % dst)
    try:
        _, data = image(src)
    except (OSError, ValueError) as e:
        sys.exit('h862bin: %s' % e)
    if ext == '.inc':
        label = os.path.splitext(os.path.basename(dst))[0]
        out = to_inc(data, label, os.path.basename(src))
    else:
        out = data
    with open(dst, 'wb') as f:
        f.write(out)
    print('%s: %d bytes' % (os.path.basename(dst), len(data)))


if __name__ == '__main__':
    main(sys.argv[1:])
