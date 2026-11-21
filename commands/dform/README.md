# DFORM

Build with `make`; run the compiled-code regression with `make check`.
DFORM owns its command source, XIOS backend and tests here. Boot-sector and
loader sources remain in `../dskmaint`; the Makefile builds their binaries
there and generates local includes. There is no duplicate loader source.

```
DFORM drive: { [options] ... }
```

| Option | CP/M format |
| --- | --- |
| 160 | Single-sided, 40 cylinders, 8 sectors/head |
| 320 | Double-sided, 40 cylinders, 8 sectors/head; default |
| 720 | Double-sided, 80 cylinders, 9 sectors/head |
| 1200 | Double-sided, 80 cylinders, 15 sectors/head |
| 1440 | Double-sided, 80 cylinders, 18 sectors/head |

`A:` or `B:` is required. Verification is enabled by default; `Q` skips it,
`V` explicitly enables it, and combining V/Q is rejected. Examples:
`DFORM B:[720]`, `DFORM A:[160Q]`. Closing brackets are optional.
Conflicting capacities are rejected. Historical 1/2 aliases remain accepted.

Formatting requires Y confirmation. N or Ctrl-C cancels. Read-back checks
cover every sector, including the boot track. Failures use bounded retries
and report the operation, cylinder and head. A partial-format warning follows
cancellation or failure after disk access.

CP/M-86 uses ROM BIOS. CCP/M-86 3.1 uses XIOS: the extended geometry
interface supports all five formats; older kernels retain 160K/320K and
refuse larger formats before confirmation. CDOS formatting is
not supported by this variant. No FAT filesystem is created.

The image uses E5 fill, boot code at offset 0, geometry bytes at 510/511,
and the shared loader at 900h. Copy CPM.SYS (or CCPM.SYS on supported media)
with PIP's [R] option to complete a bootable disk. BIOS buffers occupy two
16 KiB-aligned slots, each large enough for an 18-sector track.

`tests/check.py` executes the linked CMD with simulated BIOS/XIOS, checking
parsing, geometry, boot bytes, verification, error handling and lock cleanup.
Live new-format validation is tracked separately; simulated success alone
does not establish firmware compatibility.

## DFORM verification and completion

Verification is enabled by default (`[V]` remains accepted). `[Q]` explicitly
skips verification and prints an unverified-result warning; V and Q conflict.
Read-back comparison covers the entire boot track and the E5 fill on all
other formatted tracks. Failed comparisons use the bounded I/O retry loop.
Errors identify the operation, cylinder and head. Cancellation or failure
after a disk operation warns that the disk may be partially formatted.

BDOS 108 is called only after recognizing Concurrent DOS 4.1 (full version
1441h). CP/M-86 1.1 and CCP/M-86 3.1 do not implement it, so DFORM never calls
it there. DFORM still rejects CDOS formatting, but returns error status 2 on
that version. Status definitions are 0 success, 2 error and 3 cancellation;
older systems retain console diagnostics and their normal termination path.

The backend requires the extended discovery signature and version before
using variable-format and raw CHS services. Legacy eight-sector calls remain
unchanged. Extended requests carry the sector profile explicitly; formatting
uses logical tracks, while reads/writes use physical cylinder/head. The same
sources, build rules and tests are maintained in CP/M and CCP/M repositories.
