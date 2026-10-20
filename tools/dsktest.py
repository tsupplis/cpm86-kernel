#!/usr/bin/env python3
"""Exercise the linked CMD images with synthetic BDOS/BIOS under emu2."""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent / "commands/disk"
count = 0


def case(tool, sides=2, tail='A: B:', memory=0x5100, mismatch=0,
         repeat=0, retry=0, formatting=0, memfail=0, error=None, native=False, version=None, full_version=0x1431,
         console_state=0, console_number=0, open_files=0, open_after_lock=0,
         queue_fail=0, initial_keep=0, floppy_count=2, abort=-1, abort_write=-1, fail_native=0, fail_times=1, native_status=1, fail_probe=False, probe_drive=-1):
    global count
    probe_error = native and '[1' not in tail and (
        sides == 1 or (fail_probe and fail_times >= 4))
    if probe_error:
        error = 'Cannot read head 1'
    heads = 1 if sides == 1 or '[1' in tail else 2
    reads = 0 if error else 40 * heads * (2 if tool == 'dcomp' else 1)
    writes = 0 if error or tool == 'dcomp' else 40 * heads
    if abort >= 0:
        reads, writes = abort, 0
    if abort_write >= 0:
        reads, writes = 40 * heads, abort_write
    if fail_native == 4:
        reads = 40 * heads
        writes = 40 * heads + min(fail_times, 3)
    if tool == 'dcomp' and fail_native == 2 and fail_times == 4 and not fail_probe:
        reads = 40 * heads * 2 - 1
    if probe_error:
        reads = 81 if probe_drive == 1 and tool == 'dcomp' else 1
        writes = 0
    touched = 0
    if native and (reads or writes):
        drives = re.findall(r'([AB]):', tail.upper())
        first = ord(drives[0]) - ord('A')
        second = ord(drives[1]) - ord('A') if len(drives) > 1 else 0
        touched = 1 << first
        if writes or (abort < 0 and not probe_error) or (probe_error and probe_drive == 1):
            touched |= 1 << second
    reset = int((not native and version in (None, 0x22)) or (native and bool(reads or writes)))
    options = dict(NATIVE=int(native), OSVER=version if version is not None else (0x1431 if native else 0x22),
                   NATIVE_STATUS=native_status, EXPECT_TOUCHED=touched,
                   FAIL_PROBE=int(fail_probe), PROBE_DRIVE=probe_drive,
                   FULL_VERSION=full_version, CONSOLE_STATE=console_state,
                   CONSOLE_NUMBER=console_number, OPEN_FILES=open_files,
                   OPEN_AFTER_LOCK=open_after_lock, QUEUE_FAIL=queue_fail,
                   INITIAL_KEEP=initial_keep, FLOPPY_COUNT=floppy_count,
                   ABORT_AT=abort, ABORT_WRITE=abort_write,
                   FAIL_NATIVE=fail_native, FAIL_TIMES=fail_times, IS_COPY=int(tool == 'dcopy'),
                   EXPECT_RESET=reset, SIDES=sides, TAIL=f'"{tail}"', MEMSIZE=memory,
                   MISMATCH=mismatch, REPEAT=repeat, READ_RETRY=retry,
                   FORCE_FORMAT=formatting, MEMFAIL=memfail,
                   EXPECT_READS=reads * (repeat + 1),
                   EXPECT_WRITES=writes * (repeat + 1))
    with tempfile.TemporaryDirectory(prefix='cpm-disk-') as td:
        image = Path(td) / 'test.com'
        subprocess.run(['nasm', '-f', 'bin', str(ROOT / 'tests/dsktest.asm'),
                        '-o', str(image), f'-DIMAGE="{ROOT / tool}.cmd"',
                        *(f'-D{k}={v}' for k, v in options.items())], check=True)
        result = subprocess.run(['emu2', str(image)], capture_output=True,
                                timeout=15)
    output = result.stdout.decode(errors='replace')
    expected = error or ('Compare error(s)' if mismatch else
                        'Diskettes compare ok' if tool == 'dcomp' else
                        'Copy complete')
    if result.returncode or (expected not in output if mismatch else
                             output.count(expected) != repeat + 1):
        raise AssertionError(f'{tool} {options}: exit {result.returncode}\n'
                             f'{output}\n{result.stderr.decode(errors="replace")}')
    usage_expected = error in ('USAGE:', 'Invalid parameter',
                               'Invalid drive specification')
    if ('USAGE:' in output) != usage_expected:
        raise AssertionError(f'Unexpected usage visibility: {output}')
    if usage_expected and ('Insert ' in output or 'Strike any key' in output):
        raise AssertionError('Usage must exit without a disk prompt')
    if (mismatch or error) and 'Diskettes compare ok' in output:
        raise AssertionError('Mismatch was also reported as a successful comparison')
    if probe_error and ('Copy complete' in output or 'Diskettes compare ok' in output):
        raise AssertionError('Ambiguous probe failure reported success')
    if probe_error and ('Copying 1 side' in output or 'Comparing 1 side' in output):
        raise AssertionError('Ambiguous probe failure selected single-sided media')
    if formatting and not probe_error and 'Formatting while copying' not in output:
        raise AssertionError('Formatting path was not reached')
    count += 1


for tool in ('dcopy', 'dcomp'):
    for sides in (1, 2):
        for tail in ('A: B:', 'A: A:', 'A: B: [1]'):
            for memory in (0x5100, 0x501):
                case(tool, sides, tail, memory)
    for tail in ('A:', 'B:', 'a:\tb: [1]', '[1] A: B:', 'A: [1] B:',
                 'A: B:[1]', 'A: B:[1', 'A: A: [1', '[1 A: B:'):
        case(tool, tail=tail)
    for tail in ('', ' ', '   \t', '[1]', '[1'):
        case(tool, tail=tail, error='USAGE:')
    case(tool, repeat=1)
    case(tool, retry=1)
    for tail in ('C: A:', 'A: C:'):
        case(tool, tail=tail, error='Invalid drive specification')
    for tail in ('A: B: A:', 'A', '[2]', 'A:[', 'A: [1x]',
                 'A: [1]]', 'A: B: a.bin'):
        case(tool, tail=tail, error='Invalid parameter')
    for memory in (0x80, 0x100, 0x1ff):
        case(tool, memory=memory, error='Insufficient memory')
    for function in (53, 55):
        case(tool, memfail=function, error='Insufficient memory')
for sides in (1, 2):
    case('dcomp', sides=sides, mismatch=1)
    case('dcopy', sides=sides, formatting=1)
for tool in ('dcopy', 'dcomp'):
    for sides in (1, 2):
        for tail in ('A: B:', 'A: A:', 'A: B: [1]'):
            for memory in (0x5100, 0x501):
                case(tool, sides=sides, tail=tail, memory=memory, native=True)
    for tail in ('', '[1]', 'A:', 'B:', 'a: b:[1', '[1] A: B:'):
        case(tool, tail=tail, native=True, error='USAGE:' if tail in ('', '[1]') else None)
    case(tool, native=True, repeat=1)
    case(tool, native=True, retry=1)
    case(tool, native=True, memfail=55)  # Function 53 has already allocated.
    case(tool, native=True, initial_keep=2, console_number=1)
    case(tool, native=True, memfail=53, error='Insufficient memory')
    case(tool, native=True, memory=0x100, error='Insufficient memory')
    case(tool, native=True, tail='C: A:', error='Invalid drive specification')
    case(tool, native=True, console_state=1, error='background or buffered')
    case(tool, native=True, console_number=4, error='local virtual console')
    case(tool, native=True, open_files=1, error='Close all open files')
    case(tool, native=True, open_after_lock=1, error='Close all open files')
    case(tool, native=True, queue_fail=135, error='MXdisk queue')
    case(tool, native=True, queue_fail=137, error='MXdisk queue')
    case(tool, native=True, floppy_count=0, error='Invalid drive specification')
    case(tool, native=True, full_version=0x1430, error='Requires CP/M-86')
    case(tool, version=0x31, error='Requires CP/M-86')
    for native in (False, True):
        for abort in (0, 1, 4):
            case(tool, native=native, abort=abort, error='Cancelled.')
    case(tool, native=True, fail_native=2)
    if tool == 'dcomp':
        case(tool, native=True, mismatch=1)
        case(tool, native=True, fail_native=2, fail_times=4, error='Unrecoverable read error')
    else:
        case(tool, native=True, sides=1, tail='A: B:[1]', formatting=1)
        case(tool, native=True, sides=2, formatting=1)
        case(tool, native=True, sides=2, formatting=1, fail_native=5)
        case(tool, native=True, fail_native=3)
        case(tool, native=True, fail_native=3, native_status=2)
        case(tool, native=True, formatting=1, fail_native=5, native_status=2)
        case(tool, native=True, fail_native=4)
        case(tool, native=True, fail_native=4, fail_times=4, error='Target diskette may be unusable')
        case(tool, native=True, abort_write=1, error='Cancelled.')
# Errors during the second-side probe do not prove that a side is absent.
for tool in ('dcopy', 'dcomp'):
    for tail in ('A: B:', 'A: A:', 'B: A:'):
        case(tool, native=True, tail=tail, fail_native=2, fail_times=4,
             fail_probe=True)
    case(tool, native=True, fail_native=2, fail_times=3, fail_probe=True)
    case(tool, native=True, tail='A: B:[1]', fail_native=2, fail_times=4,
         fail_probe=True)  # Explicit head-zero selection never probes head one.
    case(tool, native=True, sides=1, tail='A: B:[1]')
case('dcomp', native=True, fail_native=2, fail_times=4, fail_probe=True,
     probe_drive=1)
print(f'PASS: {count} dual-OS simulated-disk cases (BDOS clobbers ES and working registers)')
