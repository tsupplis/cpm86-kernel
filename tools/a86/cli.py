"""Argument parsing for a86tool."""

import re
import sys

from . import __doc__ as USAGE
from .annotate import cmd_annotate
from .boundary import cmd_boundary
from .datamap import cmd_datamap
from .decode import cmd_decode
from .holes import cmd_holes
from .commands import (cmd_data, cmd_gen, cmd_mklabel,
                       cmd_mklabels, cmd_mkvars, cmd_mark, cmd_names,
                       cmd_patch, cmd_relabel, cmd_rename, cmd_unequ)
from .scaffold import cmd_scaffold
from .splice import cmd_labels
from .typedata import cmd_typedata

BIN_CMDS = {'boundary', 'gen', 'patch', 'data', 'mkvars', 'labels', 'decode',
            'holes', 'annotate', 'datamap', 'typedata'}


def opt(a, flag):
    """Pop `flag VALUE` from the argument list; None when absent."""
    if flag not in a:
        return None
    i = a.index(flag)
    v = a[i + 1]
    del a[i:i + 2]
    return v


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(USAGE)
    base = None
    verify = True
    if '--base' in a:
        i = a.index('--base'); base = int(a[i + 1], 16); del a[i:i + 2]
    if '--no-verify' in a:
        a.remove('--no-verify'); verify = False
    cmd_opt, org_opt = opt(a, '--cmd'), opt(a, '--org-name')
    sub = a[0]
    if base is None:
        # A CMD file has a 128-byte header, so image address 0 is at offset 128.
        base = -0x80 if sub in BIN_CMDS and a[1].lower().endswith('.cmd') else 0
    if sub == 'scaffold':
        cmd_scaffold(a[1], cmd_opt, org_opt)
    elif sub == 'boundary':
        set_to = None
        if '--set' in a:
            i = a.index('--set')
            nxt = a[i + 1] if i + 1 < len(a) else ''
            set_to = int(nxt, 16) if re.fullmatch(r'[0-9a-fA-F]+', nxt) else 0
            del a[i:i + (2 if nxt and set_to else 1)]
        cmd_boundary(a[1], a[2], base, set_to, verify)
    elif sub == 'decode':
        cmd_decode(a[1], a[2], base)
    elif sub == 'holes':
        cmd_holes(a[1], a[2], base)
    elif sub == 'datamap':
        cmd_datamap(a[1], a[2], base)
    elif sub == 'typedata':
        cmd_typedata(a[1], a[2], base, verify)
    elif sub == 'annotate':
        what = a[3] if len(a) > 3 else None
        if what not in (None, 'text', 'tables'):
            sys.exit('annotate takes `text` or `tables` (or nothing for both)')
        cmd_annotate(a[1], a[2], base, what, verify)
    elif sub == 'gen':
        cmd_gen(a[1], a[2], int(a[3], 16), int(a[4], 16), base)
    elif sub == 'patch':
        cmd_patch(a[1], a[2], int(a[3], 16), int(a[4], 16), base, verify)
    elif sub == 'data':
        cmd_data(a[1], a[2], int(a[3], 16), int(a[4], 16), base, verify)
    elif sub == 'relabel':
        cmd_relabel(a[1], verify)
    elif sub == 'mklabel':
        cmd_mklabel(a[1], int(a[2], 16), a[3])
    elif sub == 'mklabels':
        cmd_mklabels(a[1], a[2] if len(a) > 2 else 'd', verify)
    elif sub == 'mkvars':
        cmd_mkvars(a[1], a[2], base, verify)
    elif sub == 'mark':
        cmd_mark(a[1], a[2] if len(a) > 2 else 'xyz', verify)
    elif sub == 'unequ':
        cmd_unequ(a[1], verify)
    elif sub == 'names':
        cmd_names(a[1])
    elif sub == 'rename':
        cmd_rename(a[1], a[2], verify)
    elif sub == 'labels':
        cmd_labels(a[1], a[2], base, verify)
    else:
        sys.exit(USAGE)


if __name__ == '__main__':
    main()
