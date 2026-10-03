#!/usr/bin/env python3
"""Self-test for the a86 reconstruction tools.

Re-proves, in throwaway copies, what was verified by hand while building them.
The real tree is only read.

usage: a86selftest.py [--keep] [name-substring ...]
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NEEDED = ('make', 'pcdev_rasm86', 'pcdev_linkcmd', 'cmdinfo', 'ndisasm',
          'unix2dos')
BUILD = ('*.obj', '*.cmd', '*.log', '*.sym', '*.lst', '*.prn', '*.h86',
         '*.bak')
TMP = None
STAGES = {}

sys.path.insert(0, HERE)


def sandbox(bins=(), cmds=()):
    """A tree shaped like the repo: tools/, base/, commands/."""
    root = tempfile.mkdtemp(dir=TMP)
    os.makedirs(root + '/base')
    os.makedirs(root + '/commands')
    shutil.copytree(HERE + '/a86', root + '/tools/a86',
                    ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy(HERE + '/a86tool.py', root + '/tools/a86tool.py')
    for b in bins:
        shutil.copy('%s/base/%s.cmd' % (ROOT, b), root + '/base/')
    for c in cmds:
        shutil.copytree('%s/commands/%s' % (ROOT, c),
                        '%s/commands/%s' % (root, c),
                        ignore=shutil.ignore_patterns(*BUILD))
    return root


def clone(root):
    dst = tempfile.mkdtemp(dir=TMP) + '/r'
    shutil.copytree(root, dst)
    return dst


def tool(root, cmd, *args):
    cwd = '%s/commands/%s' % (root, cmd) if cmd else root
    r = subprocess.run([sys.executable, root + '/tools/a86tool.py', *args],
                       cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def make_check(d):
    subprocess.run(['make', 'clean'], cwd=d, capture_output=True)
    r = subprocess.run(['make', 'check'], cwd=d, capture_output=True,
                       text=True)
    return r.returncode == 0 and 'PASS' in r.stdout


def read(path):
    with open(path, 'rb') as f:
        return f.read()


def code_db_lines(path):
    text = read(path).decode('latin-1').replace('\r', '')
    code = text.split('org\t100h')[1].split('; ---- data')[0]
    return sum(1 for ln in code.split('\n') if ln.startswith('\tdb\t'))


# --------------------------------------------------------------------------
# the dskmaint pipeline, built once and snapshotted for the tests that follow
# --------------------------------------------------------------------------
def org_name(name):
    from a86.scaffold import org_name as f
    return f(name)


def pipeline():
    if 'out' in STAGES:
        return STAGES['out']
    root = sandbox(bins=['dskmaint'])
    d = root + '/commands/dskmaint'
    org = org_name('dskmaint') + '.a86'
    binf = '../../base/dskmaint.cmd'
    out = {'root': root, 'org': org}
    out['scaffold'] = tool(root, None, 'scaffold', 'dskmaint')
    out['labels'] = tool(root, 'dskmaint', 'labels', binf, org)
    out['boundary'] = tool(root, 'dskmaint', 'boundary', binf, org, '--set')
    STAGES['bounded'] = clone(root)
    out['decode'] = tool(root, 'dskmaint', 'decode', binf, org)
    out['annotate'] = tool(root, 'dskmaint', 'annotate', binf, org)
    out['typedata'] = tool(root, 'dskmaint', 'typedata', binf, org)
    out['typedata2'] = tool(root, 'dskmaint', 'typedata', binf, org)
    STAGES['typed'] = clone(root)
    out['usedata'] = tool(root, 'dskmaint', 'usedata', org)
    out['usedata2'] = tool(root, 'dskmaint', 'usedata', org)
    out['check'] = make_check(d)
    out['db_left'] = code_db_lines(d + '/' + org)
    STAGES['out'] = out
    return out


# --------------------------------------------------------------------------
# tests
# --------------------------------------------------------------------------
def t_compile():
    for dp, _, fs in os.walk(HERE + '/a86'):
        for f in fs:
            if f.endswith('.py'):
                path = os.path.join(dp, f)
                compile(read(path), path, 'exec')


def t_hex_literal_bounds():
    from a86.source import get_bounds
    got = get_bounds(['data_org\tequ\t0734h', 'image_end\tequ\t1060h'])
    assert got == (0x734, 0x1060), \
        'digit-leading hex literals are not recognised: %s' % (got,)


def t_scaffold_assign():
    root = sandbox(bins=['assign'])
    rc, out = tool(root, None, 'scaffold', 'assign')
    assert rc == 0 and 'PASS' in out, out
    real = '%s/commands/assign/Makefile' % ROOT
    if os.path.exists(real):
        assert read(root + '/commands/assign/Makefile') == read(real), \
            'generated Makefile differs from commands/assign/Makefile ' \
            '(template drift)'
    rc, out = tool(root, None, 'scaffold', 'assign')
    assert rc != 0 and 'never overwrites' in out, 'second scaffold not refused'


def t_pipeline_dskmaint():
    p = pipeline()
    for step in ('scaffold', 'labels', 'boundary', 'decode', 'annotate',
                 'typedata'):
        rc, out = p[step]
        assert rc == 0, '%s failed: %s' % (step, out)
    assert 'OK  data_org set to 0734h' in p['boundary'][1], p['boundary'][1]
    m = re.search(r'OK\s+(\d+) regions, (\d+) instructions decoded',
                  p['decode'][1])
    assert m, p['decode'][1]
    assert int(m.group(2)) >= 374, 'decoded only %s instructions (was 374)' \
        % m.group(2)
    assert 'kept as db' not in p['decode'][1], p['decode'][1]
    assert 'OK  2 annotated' in p['annotate'][1], p['annotate'][1]
    assert 'OK  typed' in p['typedata'][1], p['typedata'][1]
    assert 'left as they were' not in p['typedata'][1], \
        'some data segments were not typed: ' + p['typedata'][1]
    assert 'nothing to type' in p['typedata2'][1], 'typedata is not idempotent'
    rc, out = p['usedata']
    assert rc == 0 and out.startswith('OK  '), out
    assert 'did not build' not in out, 'some substitutions did not build: ' + out
    assert 'nothing to substitute' in p['usedata2'][1], \
        'usedata is not idempotent'
    assert p['check'], 'final make check failed'
    assert p['db_left'] == 1, '%d db lines left in the code' % p['db_left']


def t_markers_not_used_as_names():
    """data_org / image_end are tool bookkeeping, never program symbols."""
    p = pipeline()
    text = read(p['root'] + '/commands/dskmaint/' + p['org']).decode('latin-1')
    body = [ln for ln in text.replace('\r', '').split('\n')
            if not re.match(r'^(data_org|image_end)\s+equ\b', ln)]
    leaks = [ln for ln in body
             if re.search(r'\b(data_org|image_end)\b', ln.split(';')[0])]
    assert not leaks, 'markers used as names: %s' % leaks[:3]


def finished():
    return sandbox(bins=['function', 'assign'], cmds=['function', 'assign'])


KNOWN = (('function', 'funcorg', '074f', 3, '0550h'),
         ('assign', 'assiorg', '08e7', 6, '0736h'))


def t_holes_known_tools():
    root = finished()
    for name, org, tbl, n, _ in KNOWN:
        rc, out = tool(root, name, 'holes', '../../base/%s.cmd' % name,
                       org + '.a86')
        assert rc == 0, out
        assert re.search(r'%s\s+%d entries' % (tbl, n), out), out
        assert 'text 36 bytes, unknown 5 bytes' in out, out


def t_boundary_known_tools():
    root = finished()
    for name, org, _, _, want in KNOWN:
        rc, out = tool(root, name, 'boundary', '../../base/%s.cmd' % name,
                       org + '.a86')
        assert rc == 0 and 'proposed data_org: ' + want in out, out


def t_annotate_restrictive():
    root = finished()
    for name, org, _, _, _ in KNOWN:
        f = '%s/commands/%s/%s.a86' % (root, name, org)
        before = read(f)
        rc, out = tool(root, name, 'annotate', '../../base/%s.cmd' % name,
                       org + '.a86')
        assert rc == 0 and 'nothing to annotate' in out, out
        assert 'already quoted' in out and 'already dw' in out, \
            'skipped for the wrong reason (the intended check is gone): ' + out
        assert read(f) == before, '%s was modified' % org


def t_relabel_noop():
    root = finished()
    for name, org, _, _, _ in KNOWN:
        f = '%s/commands/%s/%s.a86' % (root, name, org)
        before = read(f).replace(b'\r', b'')
        rc, out = tool(root, name, 'relabel', org + '.a86')
        assert rc == 0 and 'nothing to relabel' in out, out
        assert read(f).replace(b'\r', b'') == before, '%s changed' % org


def t_guard_and_revert():
    root = finished()
    d = root + '/commands/function'
    with open(root + '/m.map', 'w') as f:
        f.write('mainloop\tmenuloop\n')
    before = read(d + '/function.a86')
    rc, out = tool(root, 'function', 'rename', 'function.a86',
                   root + '/m.map')
    assert rc != 0 and 'not built by' in out, 'working copy not refused: ' + out
    assert read(d + '/function.a86') == before, 'refused but modified'
    rc, out = tool(root, 'function', 'rename', 'funcorg.a86', root + '/m.map')
    assert rc == 0 and 'OK' in out, out
    code = ("import sys; sys.path.insert(0, sys.argv[1] + '/tools')\n"
            "from a86.build import verified_write\n"
            "t = open('funcorg.a86', newline='').read().replace('\\r\\n', '\\n')\n"
            "i = t.rfind('\\n\\tend')\n"
            "verified_write('funcorg.a86', (t[:i] + '\\n\\tmov\\tax,,,' + t[i:])"
            ".split('\\n'), True, what='injected')\n")
    keep = read(d + '/funcorg.a86')
    r = subprocess.run([sys.executable, '-c', code, root], cwd=d,
                       capture_output=True, text=True)
    assert r.returncode != 0 and 'reverted' in r.stdout, r.stdout + r.stderr
    assert read(d + '/funcorg.a86') == keep, 'broken edit not reverted'
    assert not os.path.exists(d + '/funcorg.a86.bak'), '.bak left behind'


DEMOTE = r'''
import os, sys
root, org = sys.argv[1], sys.argv[2]
sys.path.insert(0, root + '/tools')
from a86 import disasm as D
from a86.decode import cmd_decode
from a86.holes import reach
from a86.text import read_text
os.chdir(root + '/commands/dskmaint')
binf = root + '/base/dskmaint.cmd'
seen, _ = reach(binf, -128, read_text(org).split('\n'))
print('EXPECT', sum(1 for _, t in seen.values()
                    if t in ('mov ds,ax', 'mov ss,ax')))
orig = D.Converter.line
def line(self, hexb, text):
    if text == 'mov ds,ax':
        return '\tmov\tax,ax'
    if text == 'mov ss,ax':
        return '\tmov\tax,,,'
    return orig(self, hexb, text)
D.Converter.line = line
cmd_decode(binf, org, -128)
'''


def t_decode_demotion():
    p = pipeline()
    root = clone(STAGES['bounded'])
    r = subprocess.run([sys.executable, '-c', DEMOTE, root, p['org']],
                       cwd=root, capture_output=True, text=True)
    out = r.stdout + r.stderr
    want = int(re.search(r'EXPECT (\d+)', out).group(1))
    assert want >= 1, 'nothing to inject into'
    m = re.search(r'(\d+) kept as db', out)
    assert r.returncode == 0 and m and int(m.group(1)) == want, out
    assert make_check(root + '/commands/dskmaint'), \
        'demoted result does not rebuild identically'


def t_decode_restores_on_failure():
    p = pipeline()
    root = clone(STAGES['bounded'])
    f = '%s/commands/dskmaint/%s' % (root, p['org'])
    data = read(f)
    nl = b'\r\n' if b'\r\n' in data else b'\n'
    i = data.rfind(b'\tend')
    bad = data[:i] + b'\tmov\tax,,,' + nl + data[i:]
    with open(f, 'wb') as fh:
        fh.write(bad)
    rc, out = tool(root, 'dskmaint', 'decode', '../../base/dskmaint.cmd',
                   p['org'])
    assert rc != 0 and 'restored' in out, out
    assert read(f) == bad, 'source not restored byte-for-byte'
    assert not os.path.exists(f + '.bak'), '.bak left behind'


def t_datamap_known_tools():
    root = finished()
    for name, org, _, _, _ in KNOWN:
        rc, out = tool(root, name, 'datamap', '../../base/%s.cmd' % name,
                       org + '.a86')
        assert rc == 0, out
        m = re.search(r'existing data labels: (\d+); inside a classified '
                      r'segment: (\d+)', out)
        assert m and int(m.group(1)) > 20, out
        assert int(m.group(2)) == 0, \
            '%s: %s known data labels fall inside a classified segment' \
            % (name, m.group(2))


def t_datamap_embedded_code():
    p = pipeline()
    rc, out = tool(p['root'], 'dskmaint', 'datamap',
                   '../../base/dskmaint.cmd', p['org'])
    assert rc == 0, out
    hits = [ln.split()[0] for ln in out.split('\n') if 'BIOS:' in ln]
    assert hits == ['0a79..0acd', '0b0c..0d40'], \
        'embedded boot images: expected exactly two, got %s' % hits
    assert re.search(r'08ab\.\.08b5 table', out), 'jump table not found'


def tiles(out):
    area = int(re.search(r'data area .*?, (\d+) bytes', out).group(1))
    kinds = re.search(r'by kind: (.*)', out).group(1)
    return area, sum(int(x) for x in re.findall(r'\w+ (\d+)', kinds))


def t_datamap_tiles():
    root = finished()
    outs = []
    for name, org, _, _, _ in KNOWN:
        rc, out = tool(root, name, 'datamap', '../../base/%s.cmd' % name,
                       org + '.a86')
        assert rc == 0, out
        outs.append((name, out))
    p = pipeline()
    rc, out = tool(p['root'], 'dskmaint', 'datamap', '../../base/dskmaint.cmd',
                   p['org'])
    assert rc == 0, out
    outs.append(('dskmaint', out))
    for name, out in outs:
        area, total = tiles(out)
        assert area == total, '%s: segments cover %d bytes of a %d byte area' \
            % (name, total, area)


def t_typedata_restrictive():
    root = finished()
    for name, org, _, _, _ in KNOWN:
        f = '%s/commands/%s/%s.a86' % (root, name, org)
        before = read(f)
        rc, out = tool(root, name, 'typedata', '../../base/%s.cmd' % name,
                       org + '.a86')
        assert rc == 0 and 'nothing to type' in out, out
        assert read(f) == before, '%s was modified' % org


def t_usedata_restrictive():
    root = finished()
    for name, org, _, _, _ in KNOWN:
        f = '%s/commands/%s/%s.a86' % (root, name, org)
        before = read(f)
        rc, out = tool(root, name, 'usedata', org + '.a86')
        assert rc == 0 and 'nothing to substitute' in out, out
        assert read(f) == before, '%s was modified' % org


def t_usedata_drops_what_does_not_build():
    """Poison one candidate so it cannot assemble: it must stay numeric."""
    p = pipeline()
    root = clone(STAGES['typed'])
    code = ("import os, sys\n"
            "sys.path.insert(0, sys.argv[1] + '/tools')\n"
            "from a86 import usedata as U\n"
            "orig = U.rewrite\n"
            "def rw(line, labels, lo, end):\n"
            "    new, forms, skips = orig(line, labels, lo, end)\n"
            "    if forms and new.startswith('\\tinc\\t'):\n"
            "        return '\\tinc\\tbyte ptr nosuchlabel', forms, skips\n"
            "    return new, forms, skips\n"
            "U.rewrite = rw\n"
            "os.chdir(sys.argv[1] + '/commands/dskmaint')\n"
            "U.cmd_usedata(sys.argv[2])\n")
    d = root + '/commands/dskmaint'
    r = subprocess.run([sys.executable, '-c', code, root, p['org']], cwd=d,
                       capture_output=True, text=True)
    out = r.stdout + r.stderr
    assert r.returncode == 0 and 'did not build' in out, out
    assert 'OK  ' in out, out
    assert make_check(d), 'result does not rebuild identically'
    text = read(d + '/' + p['org']).decode('latin-1')
    assert 'nosuchlabel' not in text, 'a line that did not build was kept'


TESTS = [t_compile, t_hex_literal_bounds, t_scaffold_assign,
         t_pipeline_dskmaint, t_markers_not_used_as_names, t_holes_known_tools, t_boundary_known_tools,
         t_annotate_restrictive, t_relabel_noop, t_guard_and_revert,
         t_decode_demotion, t_decode_restores_on_failure,
         t_datamap_known_tools, t_datamap_embedded_code, t_datamap_tiles,
         t_typedata_restrictive, t_usedata_restrictive,
         t_usedata_drops_what_does_not_build]


def main():
    global TMP
    args = sys.argv[1:]
    keep = '--keep' in args
    filt = [a for a in args if not a.startswith('--')]
    missing = [t for t in NEEDED if not shutil.which(t)]
    if missing:
        sys.exit('missing tools: ' + ', '.join(missing))
    TMP = tempfile.mkdtemp(prefix='a86selftest-')
    failed = 0
    for t in TESTS:
        name = t.__name__[2:]
        if filt and not any(f in name for f in filt):
            continue
        try:
            t()
            print('PASS  %s' % name)
        except Exception as e:                      # noqa: BLE001
            failed += 1
            msg = (str(e) or e.__class__.__name__).strip().splitlines()
            print('FAIL  %s\n      %s' % (name, '\n      '.join(msg[-6:])))
    print('\n%s' % ('all passed' if not failed else '%d FAILED' % failed))
    if keep or failed:
        print('sandboxes kept in %s' % TMP)
    else:
        shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
