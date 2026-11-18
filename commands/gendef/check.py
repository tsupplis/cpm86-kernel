"""Check historical output and DPB-only generation under emu2."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OPTIONS = ['', '$C', '$O', '$Z', '$COZ']


def dpb_statements(data):
    """Extract DPB declarations from historical output, including aliases."""
    result = []
    active = False
    for raw in data.split(b'\x1a', 1)[0].decode('ascii').splitlines():
        line = raw.split(';', 1)[0].strip()
        if not line:
            continue
        if re.match(r'^dpb\d+\s+equ\b', line):
            active = True
        elif not re.match(r'^(db|dw)\s', line):
            active = False
        if active:
            result.append(line)
    return result


def statements(data):
    return [line for raw in data.split(b'\x1a', 1)[0].decode('ascii').splitlines()
            if (line := raw.split(';', 1)[0].strip())]


def run(emu, work, binary, definition, option, valid=True):
    work.mkdir()
    program = work / 'gendef.cmd'
    shutil.copyfile(binary, program)
    (work / 'sample.def').write_bytes(definition)
    env = dict(os.environ, EMU2_DRIVE_D=str(work),
               EMU2_PROGNAME='D:GENDEF.CMD')
    result = subprocess.run([emu, str(program), 'sample'] +
                            ([option] if option else []), cwd=work,
                            env=env, capture_output=True, timeout=20)
    result.check_returncode()
    if valid:
        assert b'No Error(s)' in result.stdout, result.stdout
    else:
        assert b'No Error(s)' not in result.stdout, result.stdout
        assert b'Error(s)' in result.stdout, result.stdout
    return (work / 'sample.lib').read_bytes()


def main():
    emu = shutil.which('emu2')
    if not emu:
        asm = shutil.which('cpm86_asm86')
        if asm:
            emu = str(Path(asm).parent / 'emu2')
    if not emu:
        raise SystemExit('emu2 or cpm86_asm86 must be on PATH')

    fixtures = {
        'pc': (HERE / 'pcold.def').read_bytes(),
        'apple': (ROOT / 'apdisks.def').read_bytes(),
        # Skew emits a real translation table in full mode; aliases must
        # retain only the DPB equivalence in B mode.
        'skew': b'DISKS 2\r\nDISKDEF 0,1,26,6,1024,243,64,64,2\r\n'
                b'DISKDEF 1,0\r\nENDEF\r\n\x1a',
    }
    workroot = ROOT / 'local/gendef-tests'
    workroot.mkdir(parents=True, exist_ok=True)
    passed = 0
    with tempfile.TemporaryDirectory(prefix='check-', dir=workroot) as tmp:
        for fixture, definition in fixtures.items():
            for option in OPTIONS:
                outputs = {}
                for version, binary in [('rebuilt', HERE / 'gendef.cmd'),
                                        ('original', ROOT / 'base/gendef.cmd')]:
                    work = Path(tmp) / (fixture + version + option.replace('$', '_'))
                    outputs[version] = run(emu, work, binary, definition, option)
                assert outputs['rebuilt'] == outputs['original'], (fixture, option)
                passed += 1
                boption = '$B' + option.lstrip('$')
                work = Path(tmp) / (fixture + boption.replace('$', '_'))
                blocks = run(emu, work, HERE / 'gendef.cmd', definition, boption)
                expected = dpb_statements(outputs['original'])
                assert expected, (fixture, option)
                # Every emitted assembler statement must be a historical
                # DPB statement: catches extra tables/storage/end markers.
                assert statements(blocks) == expected, (fixture, boption)
                passed += 1
            print(f'PASS: {fixture}: 5 historical comparisons, 5 DPB-only comparisons')
        # ORG changes placement only, in both full and DPB-only modes.
        located = (ROOT / 'pcdisks.def').read_bytes()
        for option in OPTIONS + ['$B', '$BC', '$BO', '$BZ', '$BCOZ']:
            work = Path(tmp) / ('org' + option.replace('$', '_'))
            output = run(emu, work, HERE / 'gendef.cmd', located, option)
            origins = [line for line in statements(output) if line.startswith('org')]
            assert origins == ['org\tFD160', 'org\tFD320', 'org\tFDTABLES'], origins
            reference = run(emu, Path(tmp) / ('plain' + option.replace('$', '_')),
                            HERE / 'gendef.cmd', fixtures['pc'], option)
            assert [line for line in statements(output)
                    if not line.startswith('org')] == statements(reference)
            passed += 1
        print('PASS: 10 symbolic-origin comparisons')
        # Reject missing/non-symbol operands and trailing expressions rather
        # than emitting partially accepted assembler directives.
        for index, operand in enumerate(['', '123', 'BASE+1', 'BASE OTHER', 'X'*40]):
            definition = ('DISKS 1\r\nORG ' + operand + '\r\n'
                          'DISKDEF 0,0,31,,1024,156,64,64,1\r\nENDEF\r\n').encode()
            for option in ['', '$B']:
                work = Path(tmp) / ('bad' + str(index) + option.replace('$', '_'))
                output = run(emu, work, HERE / 'gendef.cmd', definition, option, valid=False)
                assert not any(line.startswith('org') for line in statements(output))
                passed += 1
        print('PASS: 10 malformed-origin rejections')
    print(f'PASS: {passed} checks, 0 failures')


if __name__ == '__main__':
    main()
