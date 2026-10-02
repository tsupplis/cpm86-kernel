"""scaffold: create commands/<name>/ from a shipped .CMD, byte-identical from step zero.

Produces the directory, the standard Makefile, and a skeleton source whose only
real instruction is the first one.  Everything else is a raw db dump, so
`make check` passes immediately and the other subcommands have something to
chew on.
"""

import os
import re
import struct
import sys

from .build import rebuild
from .disasm import BRANCH, Converter, disasm
from .text import lbl, num

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HDR = 128              # CMD header length; file offset 128 is image address 0
CODE_START = 0x100     # 8080 model: the base page occupies 0-0FFh

# Recipe lines are written with four leading spaces and turned into tabs.
MAKEFILE = r'''RASM86=pcdev_rasm86
LINK86=pcdev_linkcmd

TOOLS=@NAME@.cmd @ORG@.cmd

SNIPPETS=

all: $(TOOLS) $(SNIPPETS)

@NAME@.obj: @NAME@.a86

@ORG@.obj: @ORG@.a86

# @NAME@ is an 8080-model CMD: one CODE group holding code, data and stack,
# with the base page at 0-0FFh.  Collapsing the data group keeps it that way.
%.cmd: %.obj
    $(LINK86) $* '[$$sz, cod[ori[0]], dat[ori[0],max[0]]]'
    cmdinfo $@

# RASM-86 exits 0 and still writes an .obj when it reports errors, so neither
# the exit status nor the file's existence can be trusted; check the count.
%.obj: %.a86
    unix2dos $<
    rm -f $@
    @$(RASM86) $< $$ pz sz > $*.log 2>&1; cat $*.log
    @grep -qE 'Number of errors: +0\.' $*.log || \
      { echo "*** $<: assembly errors"; rm -f $@; exit 1; }

# The reconstruction reproduces the shipped binary exactly; keep it that way.
REF=@REF@

check: @ORG@.cmd
    cmp $< $(REF)
    @echo "PASS: @NAME@.cmd is byte-identical to $(REF)"

clean:
    rm -f *.sys *.loc *.cmd *.obj *.h86 *.sym *.lin *.lst *.prn
    rm -f *.loc *.mp? *.lnk *.log
'''

BANNER = '''\
;***********************************************************
;  @NAME@.A86 - reconstructed from @REFNAME@
;  Skeleton from `a86tool.py scaffold`: the first instruction is real,
;  the rest of the image is a raw db dump still to be decoded.
;
;  Build:   make
;  Check:   make check
;***********************************************************
'''


def org_name(name):
    """Reference-source stem: funcorg, assiorg, mformorg.

    Fitted to those three; override with --org-name when it guesses wrong.
    """
    return (name if len(name) <= 5 else name[:4]) + 'org'


def render_makefile(name, org, ref):
    text = MAKEFILE
    for k, v in (('@NAME@', name), ('@ORG@', org), ('@REF@', ref)):
        text = text.replace(k, v)
    return re.sub(r'(?m)^ {4}', '\t', text)


def find_cmd(name, cmd):
    if cmd:
        return os.path.abspath(cmd)
    for sub in ('base', 'dev', 'extra'):
        p = os.path.join(ROOT, sub, name + '.cmd')
        if os.path.exists(p):
            return p
    sys.exit('no %s.cmd in base/, dev/ or extra/ (use --cmd)' % name)


def parse_header(data):
    groups = []
    for i in range(8):
        typ, length, base, mn, mx = struct.unpack('<BHHHH',
                                                  data[i * 9:i * 9 + 9])
        if typ:
            groups.append((typ, length * 16, base, mn * 16, mx * 16))
    return groups


def dump(blob):
    return ['\tdb\t' + ','.join(num(b) for b in blob[i:i + 8])
            for i in range(0, len(blob), 8)]


def skeleton(name, refname, cmdpath, data, end):
    """Source text and a one-line description of the decoded instruction."""
    first = disasm(cmdpath, CODE_START, CODE_START + 16, -HDR)[0]
    _, hexb, text = first
    n = len(hexb) // 2
    parts = text.split(None, 1)
    labels, target = set(), None
    if parts[0] in BRANCH and len(parts) > 1:
        m = re.search(r'0x([0-9a-f]+)', parts[1])
        if m and CODE_START + n <= int(m.group(1), 16) < end:
            target = int(m.group(1), 16)
            labels.add(target)
    insn = Converter(labels, {}, CODE_START, end).line(hexb, text)

    rest = data[HDR + CODE_START + n:HDR + end]
    body = ['start:', insn]
    if target is None:
        body += dump(rest)
    else:
        cut = target - CODE_START - n
        body += dump(rest[:cut]) + ['', lbl(target) + ':'] + dump(rest[cut:])

    src = BANNER.replace('@NAME@', name.upper()).replace('@REFNAME@', refname)
    src += '\n; Bounds for tools/a86tool.py: where the data starts and the image ends.\n'
    src += 'data_org\tequ\t%s\n' % num(end)
    src += 'image_end\tequ\t%s\n\n' % num(end)
    src += '\tcseg\n\torg\t100h\n\n'
    src += '\n'.join(body) + '\n\n; ---- data ----\n\tend\n'
    return src, insn.strip().replace('\t', ' '), target


def cmd_scaffold(name, cmd=None, org=None):
    cmdpath = find_cmd(name, cmd)
    d = os.path.join(ROOT, 'commands', name)
    if os.path.exists(d):
        sys.exit('%s already exists; scaffold never overwrites' % d)

    data = open(cmdpath, 'rb').read()
    groups = parse_header(data)
    if not (len(groups) == 1 and groups[0][0] == 1
            and groups[0][3] == groups[0][1]):
        sys.exit('not a plain 8080-model CMD (one CODE group, MIN == LEN): %s\n'
                 'groups (type, len, base, min, max): %s'
                 % (os.path.basename(cmdpath), groups))
    end = groups[0][1]

    org = org or org_name(name)
    ref = os.path.relpath(cmdpath, d)
    src, insn, target = skeleton(name, os.path.relpath(cmdpath, ROOT),
                                 cmdpath, data, end)

    os.makedirs(d)
    with open(os.path.join(d, 'Makefile'), 'w') as f:
        f.write(render_makefile(name, org, ref))
    for stem in (org, name):
        with open(os.path.join(d, stem + '.a86'), 'w') as f:
            f.write(src)

    print('created %s' % os.path.relpath(d, ROOT))
    print('  image %04xh bytes, first instruction: %s%s'
          % (end, insn, '  (label l%04x)' % target if target else ''))
    r = rebuild(d)
    if r.returncode == 0:
        print('PASS  skeleton is byte-identical to %s' % os.path.relpath(cmdpath, ROOT))
        return
    print('FAIL  skeleton does not reproduce the binary (files kept for inspection):')
    print('  ' + '\n  '.join((r.stdout + r.stderr).strip().splitlines()[-8:]))
    sys.exit(1)
