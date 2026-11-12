# CHKCPMFS

`CHKCPMFS.CMD` is the same PL/M-86 checker for CP/M-86, CCP/M-86 and
Concurrent DOS 4.1. It checks CP/M directory allocation in user areas 0–15.
The default is read-only; F enables only the two confirmed metadata repairs
listed below. It does not repair file contents or choose between conflicting
allocation references. CHKDOSFS is a separate, CDOS-only FAT checker.

## Usage

```
CHKCPMFS drive: [FV]
  drive: A:..P:
  F      confirmed metadata repair
  V      verbose
```

Exactly one drive is required, followed by an optional F/V option group.
Options are case-insensitive; invalid arguments stop before drive access.
All user areas 0–15 are checked; there is no user-area parameter. The original
drive, user area and command DMA offset are restored on normal exits.

## Detection

The checker validates the DPB before interpreting directory allocation:
block shift/mask, extent mask and entry capacity must agree; directory blocks
must be reserved and fit within the disk. Directories exceeding 2048 slots
are refused. The error count saturates at 65535 rather than wrapping to zero.

It reports invalid record counts, reserved extent bits, references beyond the
DPB maximum, references to directory-reserved blocks, duplicate block
references and duplicate extent groups. Extent groups use the DPB EXM mask;
filename attribute bits do not change the file identity. System files are
checked like other files. Every nonzero allocation slot is checked, including
slots beyond the record count. Zero slots may be sparse holes and are not
errors by themselves.

Without F, ordinary entries are enumerated through BDOS. The checker
preserves an already read-only drive; otherwise it temporarily write-protects
and later resets it. Failure to establish protection stops the scan. Software
write protection is not an exclusive lock against raw I/O or another process
resetting the drive: always run on an idle drive.

## Confirmed metadata repairs

F takes a complete raw directory scan and presents one repair plan. Only an
explicit Y/y commits it; cancellation leaves the entire disk unchanged.

| Repair | Required evidence | Exact change |
|---|---|---|
| Reserved extent bits | Valid layout/name and no unresolved allocation or extent conflict | Clear EX bits 5–7 and S2 bits 6–7; preserve the effective extent number |
| Identical duplicate extent | Same user/name/extent group, all 32 entry bytes identical, matching associated timestamp tuples where present | Keep the first record; change only the duplicate's user byte to E5h |

Known volume labels and correctly positioned timestamp SFCBs are preserved.
Duplicate removal requires matching complete ten-byte timestamp tuples when
SFCBs are present. Different/missing tuples, password/XFCB or unrecognized
associated metadata prevent duplicate removal. F also refuses uncertain names,
conflicting duplicate extents, unrelated cross-links, invalid allocation
references and record-count problems. Any such blocker prevents the whole
repair plan, including otherwise repairable reserved bits.

Duplicates are removed before survivor normalization, so an interrupted
operation does not create two formerly identical entries with different
reserved bits. File data, allocation slots, record counts, names, attributes,
S1, labels and timestamp records are never rewritten by these repairs.

Each directory record is reread and compared immediately before writing.
The native adapter preserves and verifies the complete 512-byte physical
sector; CP/M BIOS uses checked 128-byte directory writes with deblocking.
A final full directory scan verifies the result. An I/O error stops further
writes and reports possible partial changes; no crash-atomic transaction or
rollback is claimed. Successfully completed prefixes are tested for safe retry.

## System interfaces and limits

| System | Repair I/O | Protection |
|---|---|---|
| CP/M-86 1.1 / BDOS 2.2 | Local IBM PC BIOS through BDOS 50, including sector translation/deblocking | Single-user execution; refuse an already read-only drive |
| CCP/M-86 3.1 | Native XIOS, 512-byte physical sectors | MXdisk held throughout planning, confirmation, writes and verification; refuse open files |
| CDOS 4.1 | Native XIOS, 512-byte physical sectors | Same locking/state restoration; DOS/FAT media refused |

CP/M BIOS DPB SPT counts 128-byte records; native XIOS DPB SPT counts physical
sectors. The adapter handles this distinction and treats XIOS status as AL,
not the whole AX register. No kernel extensions or kernel source changes are
required. Unknown OS interfaces and unsupported physical sector sizes are
refused for repair. MXdisk cannot protect against an independent raw-disk
writer that ignores that lock.

On concurrent systems, the prior P_KEEP bit and disk error mode are restored.
After any write attempt, the drive is reset to discard cached allocation and
directory state; its next access may require a re-login. If interrupted or
cleanup fails, check drive state with STAT on CP/M, or SHOW/SET on concurrent
systems. A previously read-only drive is never made writable for repair.

The default BDOS scan does not inspect deleted slots, validate all timestamp or
XFCB contents, read file data, or compare with the live allocation vector.
F reads raw directory slots to establish repair evidence; this does not add
undelete or general metadata repair. CP/M reconstructs its allocation vector
from directory references at login: there is no persistent FAT-style list of
allocated-but-unreferenced blocks to recover.

## Build and verification

`make` uses the existing Intel PL/M/ASM/LINK/LOC and GENCMD build pattern.
`make check` runs the compiled command against synthetic BDOS/DPB/DMA cases,
parameter tests, a compiled counter-overflow test, and exact-byte repair tests
across all three OS versions. Repair tests cover cancellation, ambiguous
metadata, timestamp matching, every selected read/write failure position,
committed prefixes and retry after interruption.

`make check-live` uses disposable images and the local source-built kernel.
It checks ordinary multi-user/multi-extent scans, write-protection restoration,
FAT refusal on CDOS, and actual metadata repairs/cancellation/refusal with
whole-image comparisons. No user disks are used. Native repair fixtures put
the duplicate in a later physical sector and preserve labels, timestamp
records, unrelated directory entries, reserved tracks and all file data.

| File | Purpose |
|---|---|
| `chkcpmfs.plm` | Shared detection, conservative repair planning and confirmations |
| `rawio.a86` | Guarded local BIOS/XIOS directory I/O and lock/state lifecycle |
| `scd.a86` | Existing PL/M startup and BDOS interface |
| `tests/` | Compiled command tests and disposable native verification |

## Native planning-read cache

While MXdisk is held, the repair planning scan reuses its 512-byte physical
sector buffer for adjacent 128-byte directory records. No additional sector
storage is allocated. Reopening or closing invalidates the cache; a failed
read is never cached. Arming a confirmed repair disables caching for the rest
of that session, including execution reads and the final verification scan.
The CP/M BIOS path retains its existing 128-byte deblocking behavior.

`make check` also executes the linked native adapter against synthetic XIOS
for CCP/M and CDOS: eight adjacent records require two physical reads, while
armed reads, before-image checking and write verification remain fresh.
