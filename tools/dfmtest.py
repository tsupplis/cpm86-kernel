#!/usr/bin/env python3
"""Run the linked DFORM code with synthetic BDOS/BIOS, including boot bytes."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent / "commands/dskmaint"
count = 0


def case(tail='A:', sides=2, verify=False, answer='Y', abort=-1,
         fail=0, status=3, error=None, version=0x22, equipment=0x41,
         drive=0, retry=False, abort_verify=False, native=False,
         console_state=0, open_files=0, queue_fail=0, console_number=0,
         floppy_count=2, full_version=0x1431, initial_keep=0,
         open_after_lock=0, initial_error_mode=7, ignore_errors=False):
    global count
    if native and version == 0x22:
        version = 0x0431
    formats = sides * 40
    writes = 1
    verifies = sides * 40 if verify else 0
    failures = (1 if retry else 5) if fail else 0
    if error or answer.upper() != 'Y':
        formats = writes = verifies = 0
    elif abort >= 0:
        formats, writes, verifies = abort, 0, 0
    elif abort_verify:
        verifies = 0
    elif fail == 5 and not retry:
        formats = writes = verifies = 0
    elif fail == 3 and not retry:
        writes = verifies = 0
    elif fail == 4 and not retry:
        verifies = 0
    reset = int(bool(formats or fail))
    options = dict(SIDES=sides, ANSWER=ord(answer), TAIL=f'"{tail}"',
                   ABORT_AT=abort, ABORT_VERIFY=int(abort_verify), FAIL_OP=fail,
                   FAIL_LIMIT=failures, FAIL_STATUS=status,
                   OSVER=version, EQUIPMENT=equipment, DRIVE=drive,
                   NATIVE=int(native), CONSOLE_STATE=console_state,
                   OPEN_FILES=open_files, QUEUE_FAIL=queue_fail,
                   CONSOLE_NUMBER=console_number, FLOPPY_COUNT=floppy_count,
                   FULL_VERSION=full_version, INITIAL_KEEP=initial_keep,
                   OPEN_AFTER_LOCK=open_after_lock,
                   INITIAL_ERROR_MODE=initial_error_mode, IGNORE_ERRORS=int(ignore_errors),
                   EXPECT_FORMATS=formats, EXPECT_WRITES=writes,
                   EXPECT_VERIFIES=verifies, EXPECT_FAILURES=failures,
                   EXPECT_RESET=reset)
    track = bytearray([0xE5]) * 4096
    boot = (ROOT / 'bootsect.bin').read_bytes()
    loader = (ROOT / 'loader.bin').read_bytes()
    assert len(boot) == 0x93 and len(loader) == 0x34e
    track[:len(boot)] = boot
    track[0x1ff] = sides - 1
    track[0x900:0x900 + len(loader)] = loader
    track[0x951] = 3 if native else 2
    with tempfile.TemporaryDirectory(prefix='dform-test-') as temp:
        temp = Path(temp)
        (temp / 'track.bin').write_bytes(track)
        subprocess.run(['nasm', '-f', 'bin', str(ROOT / 'tests/dfmtest.asm'),
                        '-o', str(temp / 'test.com'),
                        f'-DIMAGE="{ROOT / "dform.cmd"}"',
                        f'-DTRACK="{temp / "track.bin"}"',
                        *(f'-D{k}={v}' for k, v in options.items())], check=True)
        p = subprocess.run(['emu2', str(temp / 'test.com')],
                           capture_output=True, timeout=10)
    output = p.stdout.decode(errors='replace')
    expected = error or ('Cancelled.' if answer.upper() != 'Y' or abort >= 0 or abort_verify
                         else f'BIOS/XIOS status {status:02X}' if fail and not retry
                         else 'Format complete.')
    assert not p.returncode and expected in output, (options, p.returncode,
                                                    output, p.stderr)
    if error and not (native and (open_files or queue_fail or open_after_lock)):
        assert 'Continue (Y/N)?' not in output, output
    if error or abort >= 0 or abort_verify or (fail and not retry) or answer.upper() != 'Y':
        assert 'Format complete.' not in output, output
    else:
        assert ('Verifying...' in output) == verify, output
        assert ('160K, single-sided' in output) == (sides == 1), output
        assert ('verification enabled.' in output) == verify, output
    count += 1


for tail in ('A:', 'A:[2]', 'A: [2', 'a:'):
    case(tail)
for tail in ('A:[1]', 'A: [1', 'A: [1] [1]'):
    case(tail, sides=1)
for tail in ('A:[V]', 'A: [V', 'A: [2V]', 'A:[V2]', 'a:[v]'):
    case(tail, verify=True)
for tail in ('A:[1V]', 'A: [1] [V', 'A: [1V', 'A: [1] [V]',
             'A:[V1]', 'a: [v] [1', 'A:[1][V]', 'A:\t[1V]'):
    case(tail, sides=1, verify=True)
case('B:[1V]', sides=1, verify=True, drive=1)
case(answer='N')
case(answer='n')
case(answer='y')
case(answer=chr(3))
for n in (0, 1, 40, 80):
    case('A:[V]', verify=True, abort=n)
case('A:[V]', verify=True, abort_verify=True)
for op in (5, 3, 4):
    case('A:[V]', verify=True, fail=op)
    case('A:[V]', verify=True, fail=op, retry=True)
case('A:[V]', verify=True, fail=5, status=0x80)
for tail in ('', ' ', '\t'):
    case(tail, error='USAGE:')
for tail in ('A', 'A:[]', 'A:[', 'A:[3]', 'A:[X]', 'A:[12]',
             'A:[1] [2]', 'A:[1V]]', 'A: V', 'A: B:', 'A:/1'):
    case(tail, error='Invalid parameter.')
for tail in ('C:', '1:'):
    case(tail, error='Invalid drive specification.')
case('A:', equipment=0, error='Invalid drive specification.')
case('B:', equipment=1, drive=1, error='Invalid drive specification.')
for ver in (0x31, 0x0122):
    case(version=ver, error='requires CP/M-86 1.1 or Concurrent CP/M-86 3.1')
# The same binary also executes native CCP/M XIOS without any ROM BIOS call.
for sides in (1, 2):
    for verify in (False, True):
        for drive in (0, 1):
            tail = ('A:' if drive == 0 else 'B:') + ('[1' if sides == 1 else '[2') + ('V]' if verify else ']')
            case(tail, native=True, sides=sides, verify=verify, drive=drive)
for n in (0, 1, 40, 80):
    case('A:[V]', native=True, verify=True, abort=n)
case('A:[V]', native=True, verify=True, abort_verify=True)
for op in (5, 3, 4):
    case('A:[V]', native=True, verify=True, fail=op)
    case('A:[V]', native=True, verify=True, fail=op, retry=True)
case(native=True, answer='N')
case(native=True, answer=chr(3))
case(native=True, console_state=1, error='background or buffered')
case(native=True, open_files=1, error='Close all open files')
case(native=True, open_after_lock=1, error='Close all open files')
case(native=True, console_number=1)
case(native=True, initial_keep=2)
case(native=True, queue_fail=0xffff, error='Cannot acquire')
case(native=True, console_number=4, error='local virtual console')
case(native=True, floppy_count=0, error='Invalid drive specification.')
case(native=True, full_version=0x1430, error='requires CP/M-86')
for mode in (0, 7, 0xfe, 0xff):
    case(native=True, initial_error_mode=mode)
    case(native=True, initial_error_mode=mode, abort=0)
for op in (5, 3, 4):
    case('A:[V]', native=True, verify=True, fail=op, ignore_errors=True)
    case('A:[V]', native=True, verify=True, fail=op, retry=True,
         ignore_errors=True)
print(f'PASS: {count} dual-OS DFORM cases; boot images, BIOS/XIOS, locks and cleanup checked')
