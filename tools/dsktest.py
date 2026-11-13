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
         queue_fail=0, initial_keep=0, floppy_count=2, abort=-1, abort_write=-1, fail_native=0, fail_times=1, native_status=1, fail_probe=False, probe_drive=-1, sectors=8, second_sectors=None, bpb=1, extended=0, bad_ninth=0, cylinders=40, bad_bpb=0, corrupt_verify=False, source_fail=False, relocation=0, poison_padding=False, repeat_sectors=None, expected_prompts=None):
    global count
    slot_paragraphs = 0x100 if sectors == 8 else 0x200 if sectors <= 16 else 0x400
    probe_error = native and '[1' not in tail and (
        sides == 1 or (fail_probe and fail_times >= 4))
    if probe_error:
        error = 'Cannot read head 1'
    heads = 1 if sides == 1 or '[1' in tail else 2
    reads = 0 if error else cylinders * heads * (2 if tool == 'dcomp' else 1)
    writes = 0 if error or tool == 'dcomp' else cylinders * heads
    if abort >= 0:
        reads, writes = abort, 0
    if abort_write >= 0:
        reads, writes = min(cylinders*heads,((memory-0x3ff)//slot_paragraphs)//heads*heads), abort_write
    if fail_native == 4:
        reads = cylinders * heads
        writes = cylinders * heads + min(fail_times, 3)
    if tool == 'dcomp' and fail_native == 2 and fail_times == 4 and not fail_probe:
        reads = cylinders * heads * 2 - 1
    if probe_error:
        reads = (min((memory-0x3ff)//slot_paragraphs,2*cylinders)&~1)+1 if probe_drive == 1 and tool == 'dcomp' else 1
        writes = 0
    geometry_memory_error = error == 'Insufficient memory' and not memfail and memory >= 0x5ff
    geometry_error = geometry_memory_error or error in ('Cannot determine','Incompatible or conflicting','Nine-sector/probe support')
    second_geometry_error = tool == "dcomp" and second_sectors is not None and second_sectors != sectors and geometry_error
    if second_geometry_error:
        reads = min((memory-0x3ff)//slot_paragraphs,cylinders*heads) & ~1
    if corrupt_verify:
        reads=cylinders*heads; writes=4*cylinders*heads
    if source_fail:
        reads=heads; writes=0
    touched = 0
    if native and (reads or writes or geometry_error):
        drives = re.findall(r'([AB]):', tail.upper())
        first = ord(drives[0]) - ord('A')
        second = ord(drives[1]) - ord('A') if len(drives) > 1 else 0
        touched = 1 << first
        if writes or (abort < 0 and not probe_error and not geometry_error) or (probe_error and probe_drive == 1) or second_geometry_error:
            touched |= 1 << second
    if source_fail and native:
        touched=1
    reset = int((not native and version in (None, 0x22)) or (native and bool(reads or writes or geometry_error)))
    options = dict(BAD_BPB=bad_bpb, CYLINDERS=cylinders, SECTORS=sectors, SECOND_SECTORS=second_sectors or sectors, BPB=bpb, EXTENDED=extended, BAD_NINTH=bad_ninth, NATIVE=int(native), OSVER=version if version is not None else (0x1431 if native else 0x22),
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
    if repeat_sectors is not None: options['REPEAT_SECTORS']=repeat_sectors
    supported=native and full_version==0x1441 and ((options['OSVER']>>8)&15) in (4,6)
    status=3 if error=='Cancelled.' or abort>=0 or abort_write>=0 else 2 if error else 1 if mismatch else 0
    options['EXPECT_STATUS']=status if supported else -1
    if poison_padding: options['POISON_PADDING']=1
    if corrupt_verify: options['CORRUPT_VERIFY']=1
    if source_fail: options['SOURCE_FAIL']=1
    if relocation:
        data=(ROOT/(tool+'.cmd')).read_bytes()[128:]
        end=data.index(b'$',data.index(b'Nine-sector/probe'))+1
        options['BUFFER_START']=end
        options['LOAD_SEG']=relocation-(end>>4)
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
    if mismatch==4:
        locations=re.findall(r'Track (\d+), Side (\d)',output)
        assert locations==[(f'{c:02}', '1') for c in range(cylinders)]*(repeat+1),locations
    if expected_prompts is not None:
        assert output.count('Insert ') == expected_prompts, output
    count += 1


for tool in ('dcopy', 'dcomp'):
    for sides in (1, 2):
        for tail in ('A: B:', 'A: A:', 'A: B: [1]'):
            for memory in (0x5100, 0x1401):
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
    for memory in (0x80, 0x100, 0x3ff):
        case(tool, memory=memory, error='Insufficient memory')
    for function in (53, 55):
        case(tool, memfail=function, error='Insufficient memory')
for sides in (1, 2):
    case('dcomp', sides=sides, mismatch=1)
    case('dcopy', sides=sides, formatting=1)
for tool in ('dcopy', 'dcomp'):
    for sides in (1, 2):
        for tail in ('A: B:', 'A: A:', 'A: B: [1]'):
            for memory in (0x5100, 0x1401):
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
for tool in ('dcopy','dcomp'):
    for native,full_version,extended in [(False,0x1431,0),(True,0x1441,0),(True,0x1431,1)]:
        for sectors in (8,9):
            for memory in (0x5100,0x1401):
                case(tool,native=native,full_version=full_version,extended=extended,sectors=sectors,memory=memory)
            case(tool,native=native,full_version=full_version,extended=extended,sectors=sectors,tail=f'A: A: [{sectors}]',repeat=1)
        case(tool,native=native,full_version=full_version,extended=extended,sectors=8,bpb=0,tail='A: B: [8]')
        case(tool,native=native,full_version=full_version,extended=extended,sectors=9,bpb=0)
    case(tool,native=True,sectors=9,error='Nine-sector/probe support')
    for tail in ['A: B: [8] [9]','A: B: [9x]']:
        case(tool,tail=tail,error='Invalid parameter')
    case(tool,bpb=0,error='Cannot determine')
    case(tool,sectors=9,bad_ninth=1,error='Cannot determine')
    case('dcomp',sectors=9,mismatch=2)
for native,version,extended in [(False,0x1431,0),(True,0x1441,0),(True,0x1431,1)]:
    for sectors,second in [(8,9),(9,8)]:
        case('dcomp',native=native,full_version=version,extended=extended,sectors=sectors,second_sectors=second,error='Incompatible or conflicting')
    for tool in ('dcopy','dcomp'):
        case(tool,native=native,full_version=version,extended=extended,sectors=9,tail='A: B: [8]',error='Incompatible or conflicting')
for tool in ('dcopy','dcomp'):
    for sectors in (9,15,18):
        for memory in (0x5100,0x1401):
            case(tool,native=True,full_version=0x1441,sectors=sectors,
                 cylinders=80,memory=memory)
        case(tool,native=True,full_version=0x1441,sectors=sectors,
             cylinders=80,tail='A: A:',repeat=1)
        case('dcopy',native=True,full_version=0x1441,sectors=sectors,
             cylinders=80,formatting=1)
        case('dcomp',native=True,full_version=0x1441,sectors=sectors,
             cylinders=80,mismatch=2)
for tool in ('dcopy','dcomp'):
    for sectors in (9,15,18):
        case(tool,native=True,full_version=0x1441,sectors=sectors,
             cylinders=80,bad_bpb=1,error='Incompatible or conflicting')
for native,version in ((False,0x1431),(True,0x1431),(True,0x1441)):
    case('dcopy',native=native,full_version=version,corrupt_verify=True,
         error='Target diskette may be unusable')
    case('dcopy',native=native,full_version=version,source_fail=True,
         error='Copy aborted; unread source batch was not written')
    for boundary in (0x1400,0x1800,0x1c00):
        case('dcomp',native=native,full_version=version,relocation=boundary)
for native,version,extended in ((False,0x1431,0),(True,0x1431,1),(True,0x1441,0)):
    for sectors in (8,9):
        case('dcomp',native=native,full_version=version,extended=extended,
             sectors=sectors,poison_padding=True)
        for mismatch in (3,4):
            case('dcomp',native=native,full_version=version,extended=extended,
                 sectors=sectors,mismatch=mismatch)
for sectors in (15,18):
    case('dcomp',native=True,full_version=0x1441,sectors=sectors,cylinders=80,poison_padding=True)
    case('dcomp',native=True,full_version=0x1441,sectors=sectors,cylinders=80,mismatch=4)
for tool in ('dcopy','dcomp'):
    case(tool,native=True,full_version=0x1441,tail='A: [bad]',error='Invalid parameter')
    case(tool,native=True,full_version=0x1441,abort=1,error='Cancelled.')
    case(tool,native=True,full_version=0x1441,memfail=53,error='Insufficient memory')
case('dcomp',native=True,full_version=0x1441,mismatch=1)
case('dcomp',native=True,full_version=0x1441,fail_native=2,fail_times=4,error='Unrecoverable read error')
for tool in ('dcopy','dcomp'):
    case(tool,native=True,version=0x1641,full_version=0x1441)
    case(tool,native=True,full_version=0x1442,error='Requires CP/M-86')
# Allocation can fit two small slots but fail after detecting larger geometry.
for tool in ('dcopy', 'dcomp'):
    for native, version, extended in [(False,0x1431,0),(True,0x1431,1),(True,0x1441,0)]:
        case(tool, native=native, full_version=version, extended=extended,
             sectors=9, memory=0x5ff, error='Insufficient memory')
    case(tool, native=True, full_version=0x1441, sectors=18, cylinders=80,
         memory=0x7ff, error='Insufficient memory')
# Exact fit and odd head counts; reduced swap counts with 256 KiB usable.
for tool in ('dcopy', 'dcomp'):
    for sectors in (8, 9):
        for memory in (0x5ff if sectors == 8 else 0x7ff,
                       0x6ff if sectors == 8 else 0x9ff):
            case(tool, sectors=sectors, memory=memory, tail='A: A:')
        case(tool, sectors=sectors, memory=0x43ff, tail='A: A:',
             expected_prompts=(4 if sectors == 8 else 6) if tool == 'dcopy' else (3 if sectors == 8 else 4))
        for native,version,extended in [(False,0x1431,0),(True,0x1431,1),(True,0x1441,0)]:
            case(tool, sectors=sectors, repeat=1, repeat_sectors=17-sectors,
                 tail='A: A:', memory=0x1401, native=native,
                 full_version=version,extended=extended)
print(f'PASS: {count} dual-OS simulated-disk cases (BDOS clobbers ES and working registers)')
