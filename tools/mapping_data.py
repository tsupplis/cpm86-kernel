#!/usr/bin/env python3
"""Resolve the symbols and hex addresses cited in mapping.md against the .sym files.

Usage:
  mapaddr.py                      report every backticked symbol and hex address in mapping.md
  mapaddr.py SYMBOL [SYMBOL ...]  look up specific symbols
  Options: --doc PATH (default ./mapping.md), --root DIR (default: directory of --doc)
"""
import argparse
import re
from pathlib import Path

SYM_FILES = ["ccpexp.sym", "bdosexp.sym", "pcbioexp.sym"]
SECTION_HEADERS = {"VARIABLES", "NUMBERS", "LABELS"}
# "ADDR NAME" pairs; the lookbehind keeps the 4-digit match at the start of a token.
ENTRY = re.compile(r"(?<!\S)([0-9A-Fa-f]{4}) (\S+)")
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
HEXLIT = re.compile(r"~?([0-9A-Fa-f]{1,4})[hH]")


def load_syms(root):
    """Return a list of (value, name, file, section) tuples from every .sym file."""
    entries = []
    for fname in SYM_FILES:
        path = root / fname
        if not path.exists():
            continue
        section = None
        for line in path.read_text().splitlines():
            for match in ENTRY.finditer(line):
                value, name = int(match.group(1), 16), match.group(2)
                if name in SECTION_HEADERS:
                    section = name
                else:
                    entries.append((value, name, fname, section))
    return entries


def show_symbol(name, entries):
    hits = [e for e in entries if e[1].upper() == name.upper()]
    if not hits:
        return f"{name:<16} NOT FOUND in .sym files"
    return "  ".join(f"{name:<16} {v:04X}h  {f}  [{s}]" for v, _, f, s in hits)


def symbols_at(value, entries):
    names = sorted({e[1] for e in entries if e[0] == value})
    return ", ".join(names) if names else "-"


def report_doc(doc, entries):
    known = {e[1].upper() for e in entries}
    unresolved = set()
    lines = doc.read_text().splitlines()
    for lineno, text in enumerate(lines, start=1):
        for token in re.findall(r"`([^`]+)`", text):
            token = token.strip()
            hexmatch = HEXLIT.fullmatch(token)
            if hexmatch:
                value = int(hexmatch.group(1), 16)
                print(f"{lineno:>4}  {token:<12} {value:04X}h  -> {symbols_at(value, entries)}")
            elif IDENT.fullmatch(token):
                if token.upper() in known:
                    print(f"{lineno:>4}  {show_symbol(token, entries)}")
                else:
                    unresolved.add(token)
    print()
    print("Not in .sym files (keywords or non-symbols): " + ", ".join(sorted(unresolved)))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("symbols", nargs="*", help="symbols to look up (default: scan mapping.md)")
    parser.add_argument("--doc", default="mapping.md")
    parser.add_argument("--root", default=None)
    args = parser.parse_args()

    doc = Path(args.doc).resolve()
    root = Path(args.root).resolve() if args.root else doc.parent
    entries = load_syms(root)

    if args.symbols:
        for name in args.symbols:
            print(show_symbol(name, entries))
    else:
        report_doc(doc, entries)


if __name__ == "__main__":
    main()
