"""labels: splice an lXXXX: label at every code address that needs one.

Targets come from control flow (flow.analyse), not a linear sweep, so strings
never get labels.  Run edges are labelled too, which leaves every region
between two labels either fully code or fully not - the unit `decode` works on.
"""

import re
import sys

from .build import verified_write
from .disasm import disasm
from .flow import CODE_START, runs
from .holes import reach
from .source import get_bounds, line_size, split_db_line
from .text import lbl, read_text

LABEL = re.compile(r'^l([0-9a-f]{4}):')


def first_insn_size(binf, base):
    return len(disasm(binf, CODE_START, CODE_START + 16, base)[0][1]) // 2


def code_db_lines(lines, first_size):
    """[(index, addr, size)] for db lines in the code area with a known address.

    Addresses are re-synchronised at every lXXXX: label.  Only the first
    instruction after `start:` has a known size; a db run after any other
    instruction has no address until the next label, so it cannot be split.
    """
    out, addr, started, after_start = [], None, False, False
    for i, ln in enumerate(lines):
        if re.match(r'^\s*org\s+100h\b', ln, re.I):
            addr, started = CODE_START, True
            continue
        if not started:
            continue
        if re.match(r'^(; ---- data|\s*dseg\b|\s*end\s*$)', ln):
            break
        m = LABEL.match(ln)
        if m:
            want = int(m.group(1), 16)
            if addr is not None and addr != want:
                sys.exit('address drift at line %d: counted %04xh but the label '
                         'says %04xh - the source no longer matches the layout'
                         % (i + 1, addr, want))
            addr = want
            continue
        if re.match(r'^start:', ln):
            addr, after_start = CODE_START, True
            continue
        sz = line_size(ln)
        if sz is not None:
            if addr is not None:
                out.append((i, addr, sz))
                addr += sz
            continue
        s = ln.strip()
        if not s or s.startswith(';'):
            continue
        if after_start and addr is not None:
            addr += first_size
            after_start = False
        else:
            addr = None
    return out


def decoded_hit(lines, t, binf, base):
    """Index of the source line holding the instruction at address t, or None.

    For a target inside a region that is already instructions: the enclosing
    label gives the region start, the binary's disassembly gives each
    instruction's address, and decoded regions are one line per instruction.
    """
    labs = [(i, int(m.group(1), 16)) for i, m in
            ((i, LABEL.match(ln)) for i, ln in enumerate(lines)) if m]
    below = [(i, a) for i, a in labs if a < t]
    if not below:
        return None
    i0, a0 = max(below, key=lambda x: x[1])
    ins = disasm(binf, a0, t + 1, base)
    if not ins or ins[-1][0] != t:
        return None
    body = []
    for k in range(i0 + 1, len(lines)):
        ln = lines[k]
        if LABEL.match(ln) or re.match(r'^(; ---- data|\s*dseg\b|\s*end\s*$)', ln):
            break
        if ln.strip() and not ln.strip().startswith(';'):
            body.append(k)
    n = len(ins) - 1
    return body[n] if n < len(body) else None


def splice(lines, wanted, first_size, binf=None, base=0):
    """(new lines, [addresses that could not be labelled])."""
    lines = list(lines)
    have = {int(m.group(1), 16) for m in map(LABEL.match, lines) if m}
    skipped = []
    for t in sorted(wanted):
        if t in have or t <= CODE_START:
            continue
        hit = next(((i, a) for i, a, sz in code_db_lines(lines, first_size)
                    if a <= t < a + sz), None)
        if hit is None:
            k = decoded_hit(lines, t, binf, base) if binf else None
            if k is None:
                skipped.append(t)
                continue
            lines[k:k] = ['', lbl(t) + ':']
            have.add(t)
            continue
        i, a = hit
        if a == t:
            lines[i:i] = ['', lbl(t) + ':']
        else:
            first, second = split_db_line(lines[i], t - a)
            lines[i:i + 1] = [first, '', lbl(t) + ':', second]
        have.add(t)
    return lines, skipped


def cmd_labels(binf, a86, base, verify=True):
    lines = read_text(a86).split('\n')
    _, end = get_bounds(lines)
    seen, targets = reach(binf, base, lines)
    edges = {x for a, e in runs(seen) for x in (a, e) if x < end}
    size = first_insn_size(binf, base)
    new, skipped = splice(lines, targets | edges, size, binf, base)
    added = sum(1 for ln in new if LABEL.match(ln)) - \
        sum(1 for ln in lines if LABEL.match(ln))
    if added == 0:
        print('no labels to add')
    else:
        verified_write(a86, new, verify, what='labels',
                       ok='OK  %d labels spliced (%d branch targets, %d run '
                          'edges), byte-identical'
                          % (added, len(targets), len(edges)))
    if skipped:
        print('not labelled (not on an instruction boundary of decoded code): '
              + ' '.join('%04x' % t for t in skipped))
