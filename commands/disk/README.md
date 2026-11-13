# DCOPY and DCOMP

One source set and one binary per command supports CP/M-86 1.1 (BIOS), IBM PC
CCP/M-86 3.1 (native XIOS), and Concurrent DOS 4.1/4.11 (native XIOS).
These are maintained ports of the PC DOS 1.10 utilities. Each repository owns
its complete sources, build and tests; no sibling directory is used at build time.

## Syntax and media

```
DCOPY source: [target:] [1] [8|9]
DCOMP first:  [second:] [1] [8|9]
```

Options use separate brackets: `DCOPY A: B: [9]`, `DCOMP A: A: [1] [8]`.
The closing bracket is optional. Drives are installed A:/B:; the second
argument defaults to the current drive. Same-drive operations prompt for swaps.
[1] restricts operation to head zero. Conflicting [8]/[9] options are rejected.

Both commands operate on raw physical sectors, independent of CP/M or FAT.
They support 40 cylinders, 512-byte sectors, one/two heads and eight/nine
sectors per head: 160/320K and 180/360K geometries. They do not convert filesystems.

Detection reads the boot sector and validates a small-disk FAT12 BPB, then
probes sector nine where the backend supports it. Successful ninth-sector I/O
proves nine sectors; a failed probe is retried and never by itself proves eight.
A valid eight-sector BPB can identify eight-sector media; unknown media needs
an explicit [8]. [9] still requires sector nine to be readable. A known BPB
contradicting the selection is rejected. DCOMP checks both media and rejects
conflicting geometries. Each new pair is detected afresh.

On the extended CDOS kernel, valid BPBs also select 80-cylinder DOS FAT12
720K (9 sectors/head), 1.2M (15) and 1.44M (18). The FAT/root/cluster fields
must agree with the selected profile. These capacities are detected without
new command-line options; `[8]`/`[9]` remain legacy sector-count overrides.
Both cylinder and sector counts must match for comparison. These larger
profiles are rejected on the CP/M/CCP/M backends.

DCOPY formats the target to the selected source geometry before writing its
tracks, then reads them back and compares every sector byte with the source. This also removes a leftover ninth sector when
copying an eight-sector disk over a nine-sector target. All target contents
are overwritten. DCOMP is read-only. Neither command installs a new system;
copying a bootable disk copies its existing bootstrap unchanged.

An unrecoverable source read aborts the copy before the affected memory batch
is written. Earlier completed batches remain on the target; there is no salvage
mode that writes unread or partially read source data.

Native head-one failures remain ambiguous and stop the operation; use [1]
for known single-sided media. A failed read is not evidence that a head is absent.

## Backends and memory

CP/M-86 uses BIOS and a private INT 1Eh parameter table. The table supplies
the actual eight/nine ID count for BIOS formatting, then returns to eighteen
for geometry probes. Concurrent versions
use SYSDAT:28h, the caller UDA and stack IOPBs under MXdisk, P_KEEP and console
NOSWITCH. CDOS uses physical raw read/write 35/36 and variable format 29.
Its INT 1Eh table supplies sector size/end-of-track to the raw services.

Original CCP/M kernels support the legacy eight-sector XIOS path. Nine-sector
access requires this project's XIOS extension: function 14, CX=0, DX=444Bh,
SI=534Bh returns AX=4B44h, DX=0101h. Old kernels safely ignore those extra
registers; no unknown entry is called without a successful handshake. Updated
kernels provide physical read/write 35/36 and variable format 29. This extends
maintenance access; it does not add FAT filesystem mounting to CCP/M.

Bulk storage starts on a physical 16 KiB boundary. Each head uses the smallest
power-of-two slot that fits its sector data:

| Sectors/head | Data | Slot |
| --- | --- | --- |
| 8 | 4 KiB | 4 KiB |
| 9 | 4.5 KiB | 8 KiB |
| 15 | 7.5 KiB | 8 KiB |
| 18 | 9 KiB | 16 KiB |

Slot size and batch capacity are recalculated for each disk pair. Transfers
stay within physical 64 KiB DMA boundaries. Only sector data is cleared and
compared; padding is excluded. Smaller slots reduce single-drive swaps, not
the amount of disk I/O. With 256 KiB of usable bulk memory, a 360K copy needs
three batches instead of five. Format CHRN DMA and verification retain separate
aligned resident scratch, preserving source data across retries.
The private stack remains resident. Trailing DMA buffers are uninitialized
storage: CMD MIN reserves them, while LEN omits their zero bytes from disk.

Native prompt input blocks through raw function 6/FDh so the priority-150 tool
does not starve the lower-priority PIN keyboard process. Ctrl-C polling during
transfers remains explicit. Cleanup restores the exact INT 1Eh vector, UDA
error mode, queue, console, priority and P_KEEP state, invalidates accessed
floppy login records and resets BDOS outside the disk lock.

## Checks

`make check` executes the linked CMDs with synthetic BDOS/BIOS/XIOS under emu2.
The local harness validates DMA/IOPBs, data including sector nine, small buffers,
one-drive swaps, geometry, mismatch reporting, formatting, retries, cancellation,
register preservation and partial-lock cleanup. BIOS calls are forbidden on
native paths. Real-kernel tests use only disposable PCE images.

From the project root, `make check-disk` runs these regression cases;
`make check-disk-live` builds the project and copies/compares disposable disks
under PCE using the actual local kernel.

## Return status

On Concurrent DOS 4.1 (full version 1441h), the commands set BDOS 108 after
cleanup: 0 success, 1 comparison differences, 2 command/I/O/geometry error,
3 cancellation. Errors and differences remain recorded across repeated disk
pairs; cancellation returns 3. Corrected transient retries do not mark failure.
CP/M-86 1.1 and CCP/M-86 3.1 do not implement function 108; it is never called
on those versions, including the extended CCP/M XIOS backend. Unknown versions
are rejected without probing function 108.
