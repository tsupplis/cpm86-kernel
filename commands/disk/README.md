# DCOPY and DCOMP for CP/M-86 and CCP/M-86

The same sources build one binary per command for CP/M-86 1.1 and the IBM PC
CCP/M-86 3.1 XIOS (OS version 1431h). Other versions are rejected. These are
ports of the PC DOS 1.10 utilities from [DOS Sources](https://github.com/tsupplis/pcdos11-hacking).
Command syntax and examples are in the source headers and HELP entries.

Both commands transfer raw sectors without interpreting a filesystem. They
support installed A:/B: drives, 40 cylinders, eight 512-byte sectors per head,
single/double-sided media, small buffers, one-drive swaps and repeated pairs.
The programs and private 512-byte stacks remain resident. Buffers are aligned
to physical 4 KiB boundaries for DMA. BDOS preserves all live registers and ES.

CP/M uses ROM BIOS. CCP/M uses `ccpmio.a86`, adapted from DFORM's backend:
SYSDAT:28h, process UDA in ES, stack IOPBs, native XIOS 10/11/15 and reversed
head-one logical track numbers. Verification reads into a separate resident
scratch buffer, preserving source data for retries. CCP/M function 53 already
allocates memory; only single-user CP/M needs function 55 afterward.

The CCP/M path requires a local foreground unbuffered console and no open
files. It sets P_KEEP/NOSWITCH, raises priority, acquires MXdisk and rechecks
open files under the lock. XIOS quick-return error mode prevents an Ignore
response from silently accepting bad data. Native status 1 maps to the common
sector-error retry/format-fallback path; status 2 maps to write
protection. XIOS does not return the full ROM BIOS status byte. A native
head-one probe error therefore stops the command rather than selecting a
single side silently. Use [1] for known single-sided media; transient probe
errors are retried before stopping.

Ctrl-C follows explicit cleanup during prompts and disk access. Every exit
restores the UDA error mode, returns MXdisk, invalidates each accessed drive's
login sequence, resets BDOS state outside the disk lock, and restores console,
priority and P_KEEP state. CP/M resets both floppy login records on exit.

`make check` runs linked CMDs under emu2 through `../../tools/dsktest.py` and
the NASM harness `tests/dsktest.asm`. Tests cover both OS paths, DMA/IOPBs,
register/ES corruption, memory allocation, swaps, geometry, comparison errors,
format fallback, verification retries, cancellation and partial-lock cleanup.
Native cases reject ROM BIOS interrupts. The harness accesses no host disks.
Real-kernel and floppy-hardware validation remains outstanding.
