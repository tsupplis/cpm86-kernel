"""boundary: where the code ends, from control flow rather than guesswork."""

import re
import sys

from .build import verified_write
from .flow import CODE_START, analyse, code_end, holes
from .source import get_bounds
from .splice import LABEL, first_insn_size, splice
from .text import lbl, num, read_text

MARK = '; ---- data ----'
GROUP = ('; One group so the CMD has a single CODE descriptor (the 8080 model),\n'
         '; but the data keeps its own segment.\n'
         'cgroup\tgroup\tcode,data')


def cmd_boundary(binf, a86, base, set_to=None, verify=True):
    lines = read_text(a86).split('\n')
    _, end = get_bounds(lines)
    seen, targets = analyse(binf, base, end)
    stop = code_end(seen)
    nbytes = sum(s for s, _ in seen.values())
    hs = holes(seen, CODE_START, stop)

    print('entry %04xh: %d instructions, %d bytes reached, %d branch targets'
          % (CODE_START, len(seen), nbytes, len(targets)))
    print('reached code ends at %04xh  (image ends at %04xh, %d bytes beyond)'
          % (stop, end, end - stop))
    print('proposed data_org: %04xh%s' % (stop, '  (ODD: dseg is word aligned)'
                                          if stop % 2 else ''))
    if hs:
        print('%d unreached ranges inside the code (tables, or code reached '
              'only through a jump table):' % len(hs))
        for a, b in hs[:25]:
            print('  %04x..%04x  %d bytes' % (a, b, b - a))
        if len(hs) > 25:
            print('  ... %d more' % (len(hs) - 25))
    if set_to is not None:
        apply_boundary(binf, a86, base, lines, stop if set_to == 0 else set_to,
                       verify)
    return stop


def apply_boundary(binf, a86, base, lines, addr, verify):
    """Move [addr, image end) into a dseg and record data_org."""
    if addr % 2:
        sys.exit('%04xh is odd: dseg is word aligned and would add a pad byte '
                 'the binary does not have.' % addr)
    if any(re.match(r'^\s*dseg\b', ln) for ln in lines):
        sys.exit('a dseg already exists; the boundary is already set')
    if MARK not in lines:
        sys.exit('no "%s" marker in the source' % MARK)

    new, skipped = splice(lines, {addr}, first_insn_size(binf, base))
    if skipped:
        sys.exit('%04xh is inside already-decoded code; cannot split there'
                 % addr)
    at = new.index(lbl(addr) + ':')
    mark = new.index(MARK)
    block = new[at + 1:mark]
    inner = [ln for ln in block if LABEL.match(ln)]
    if inner:
        sys.exit('labels inside the data area: %s' % ', '.join(inner))

    out = new[:at + 1] + ['', MARK, '\tdseg'] + block + new[mark + 1:]
    first_cseg = next(i for i, ln in enumerate(out)
                      if re.match(r'^\s*cseg\b', ln))
    out[first_cseg:first_cseg] = GROUP.split('\n') + ['']
    out = [re.sub(r'^(data_org\s+equ\s+)\S+', r'\g<1>' + num(addr), ln)
           for ln in out]
    ndb = sum(1 for ln in block if ln.strip())
    verified_write(a86, out, verify, what='boundary',
                   ok='OK  data_org set to %04xh, %d db lines moved to dseg, '
                      'byte-identical' % (addr, ndb))
