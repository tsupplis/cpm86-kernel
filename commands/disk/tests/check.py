#!/usr/bin/env python3
"""Exercise the linked CMD images with synthetic BDOS/BIOS under emu2."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
count = 0


def case(tool, sides=2, tail='A: B:', memory=0x5100, mismatch=0,
         repeat=0, retry=0, formatting=0, memfail=0, error=None):
    global count
    heads = 1 if sides == 1 or '[1' in tail else 2
    reads = 0 if error else 40 * heads * (2 if tool == 'dcomp' else 1)
    writes = 0 if error or tool == 'dcomp' else 40 * heads
    options = dict(SIDES=sides, TAIL=f'"{tail}"', MEMSIZE=memory,
                   MISMATCH=mismatch, REPEAT=repeat, READ_RETRY=retry,
                   FORCE_FORMAT=formatting, MEMFAIL=memfail,
                   EXPECT_READS=reads * (repeat + 1),
                   EXPECT_WRITES=writes * (repeat + 1))
    with tempfile.TemporaryDirectory(prefix='cpm-disk-') as td:
        image = Path(td) / 'test.com'
        subprocess.run(['nasm', '-f', 'bin', str(ROOT / 'tests/harness.asm'),
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
    if mismatch and 'Diskettes compare ok' in output:
        raise AssertionError('Mismatch was also reported as a successful comparison')
    if formatting and 'Formatting while copying' not in output:
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
print(f'PASS: {count} simulated-disk cases (BDOS clobbers ES and working registers)')
