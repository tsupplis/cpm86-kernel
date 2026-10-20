# DCOPY and DCOMP for CP/M-86

Build with `make`; the command syntax, defaults and examples are documented
in each source header. Use `DCOPY A: B:[1]` or `DCOMP A: B:[1]`
for head zero only; `[1` without the closing bracket is accepted too. At least
one drive is required, and an omitted second drive defaults to the current
CP/M drive. An empty, whitespace-only, option-only or invalid command line
prints usage and exits without starting disk operations. Both programs use the 8080 CMD model and a private
512-byte stack. They support installed A:/B: floppy units with 40 cylinders,
eight 512-byte sectors per head and one or two heads.

The disk operations remain IBM PC BIOS INT 13h calls. Console I/O, current
drive lookup, memory management and termination use BDOS INT E0h. The BDOS
wrapper saves ES and the live disk/comparison registers. Transfer buffers
are aligned to 4 KiB so individual track requests stay inside a BIOS DMA
page. The stack, initialization code and data remain resident.

In this kernel, BDOS 53 queries the largest free block; BDOS 55 must then
reserve it. Termination uses BDOS 37 to invalidate both floppy login records,
then BDOS 0 with DL=0 to release program memory and the transfer allocation.

`make check` requires NASM and emu2. It runs the actual linked CMD code with
synthetic BDOS/BIOS handlers, including deliberate ES/register corruption,
small buffers, disk swaps, single/double-sided media, [1], repeated operations,
read retries, comparison mismatches, format fallback and allocation errors.
The harness accesses no host disks. Testing with the real CP/M kernel and
its floppy BIOS remains necessary; these checks simulate those interfaces.

## BDOS 3.x / XIOS assessment

Feasible, with DCOMP first and DCOPY read/write/verify next. Formatting
needs an OEM-specific service; the standard XIOS table in the local
`ossrc/ccpmv31/D2/XIOSCB.DEF` defines no format operation. Read-back can
replace ROM BIOS verify. Translate CHS, geometry and errors in a separate
backend; retain the buffering and comparison loops.

Do not select this backend by version number alone. DRI's
[Concurrent CP/M System Guide, sections 5 and 10](https://manuals.plus/m/58d95654ae13e0dd4102c2b7d66177bc55bdbab4097a307f500e14a1ec7087d0)
describes a release-specific protocol: verify the OS, protect process and
console state, exclude competing disk access through the MXdisk queue,
then call XIOS with a stack IOPB. Cleanup invalidates affected drive login
state, releases the queue and restores the system state. Functions 10/11
perform native reads/writes; 35/36 are DOS-media operations. The CP/M-86
BDOS 50 disk-call sequence is not a substitute.

The archived `commands/mform/mformorg.a86` illustrates the MXdisk queue
and a CompuPro XIOS entry, but its fixed entry address is not portable.
Use the target system's documented XIOS entry and structures. Audit memory
allocation and termination too: the current function-53-then-55 sequence
is specific to this repository's single-user kernel. Keep all exits, disk
swaps and error recovery inside the target system's cleanup protocol.

Choose a concrete OS/XIOS release before implementation. Neither current
CMD implements the XIOS backend or is validated under BDOS 3.x.
