# CHKCPMFS

`CHKCPMFS.CMD` is the same read-only CP/M filesystem checker for CP/M-86,
CCP/M-86 and Concurrent DOS 4.1. It scans ordinary file entries in user areas
0–15 on the specified drive through BDOS. It does not modify the disk.

## Usage

```
CHKCPMFS drive: [FV]
```

Exactly one drive (A:..P:) is required, followed by an optional F/V option
group. V lists checked entries. F (repair) remains a reserved placeholder and stops
before scanning. Options are case-insensitive. Invalid
arguments display usage and stop. All user areas 0–15 are always checked;
there is no user-area parameter. The original drive and user area are restored.

Before scanning, it checks the drive's BDOS read-only state. If the drive is
writable, CHKCPMFS temporarily sets it read-only and resets the drive afterward
to restore write access. A drive that was already read-only remains so. If
write protection cannot be established, the scan stops. CCP/M and CDOS may
refuse protection when another process has files open on the drive.

If write access cannot be restored, or if the command is interrupted, check
the drive's status. On CP/M-86, use `STAT` and enter Ctrl-C at the command
prompt to restore write access. On CCP/M and CDOS, use `SHOW` and, if needed,
`SET d: [RW]`. The normal cleanup resets a drive that the checker protected;
its next access may require a re-login.

The checker uses the selected drive's DPB and scans every directory extent.
It reports record counts beyond 128, extent reserved bits, allocation
references beyond the DPB's maximum block, references to directory-reserved
blocks, duplicate block references, and duplicate extent groups. Extent
groups are compared using the DPB's EXM mask. Every nonzero allocation slot is
checked, including slots beyond the record count; zero slots are allowed for
sparse files. System files are checked like any other file. The checker
refuses directories with more than 2048 slots. On CDOS it also refuses
DOS/FAT media identified by the CDOS pseudo-label.

Run it only when the drive is idle. BDOS read-only protection is software-level,
not an exclusive lock against raw disk I/O or another process resetting the
drive, so concurrent activity can make results inconsistent. This version
does not inspect deleted directory slots, validate timestamp/XFCB metadata,
read data sectors, identify lost blocks, or repair anything. Its results are
limited to the directory entries BDOS exposes. CP/M rebuilds its allocation
vector from the directory when a disk is logged in; there is no on-disk list
of allocated-but-unreferenced data blocks. The checker does not compare the
directory with the live in-memory vector.

Run `make check` for synthetic BDOS and DMA tests covering all three system
versions. `make check-live` builds the local test images and checks disposable
disks under PCE, including multi-user and multi-extent files, read-only
preservation, and cross-links. CDOS also tests FAT refusal. The live tests
verify that the disk images remain unchanged.
