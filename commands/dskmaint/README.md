# DSKMAINT and DFORM

`make` builds the DSKMAINT reconstruction, its reference configuration,
and the command-line formatter DFORM. Both programs include the same
`bootsect.inc` and `loader.inc`, generated from `bootsect.a86` and
`loader.a86`. The existing DSKMAINT sources remain unchanged.

## DFORM

```
DFORM drive: { [options] ... }
```

A target A: or B: is required. Option 1 selects 160K single-sided media;
option 2 selects 320K double-sided media (the default). V requests a full
BIOS verification pass after formatting and writing the boot track.
Without V, there is no verification pass. Geometry is fixed at 40 cylinders,
eight 512-byte sectors per head, just as in DSKMAINT.

Options may be combined, split into groups, and written without closing
brackets: `DFORM A:[1V]`, `DFORM A: [1] [V`, and `DFORM A: [1V` are equivalent.
Lowercase is accepted. Unknown options, conflicting 1/2 selections and
malformed or empty command lines display usage without a disk operation.

DFORM displays the drive, capacity and verification setting and requires
Y confirmation. N or Ctrl-C cancels. It formats once and exits; failures
are retried five times before reporting the final BIOS status. Raw BDOS
console I/O routes Ctrl-C through cleanup rather than terminating with the
BIOS diskette parameter vector still patched. The original vector is
restored before resetting the affected CP/M drive's login state.

The formatted disk contains exactly DSKMAINT's boot track: E5 fill,
shared boot code at offset 0, sides byte at 1FFh and shared loader at 900h.
Copy CPM.SYS using PIP's [R] option to complete a bootable disk.

This is a single-user CP/M-86 1.1 / BDOS 2.2 IBM PC command. It rejects
other OS versions before disk access; Concurrent CP/M/XIOS is not implemented.
A private 512-byte stack and an 8 KiB resident reservation provide room for
a 4 KiB track buffer aligned at a physical 4 KiB boundary for BIOS DMA.

## Validation

`make check` retains the original DSKMAINT byte comparison and runs
`make check-dform`. The latter executes the linked DFORM CMD under emu2
using a NASM test harness with simulated BDOS/BIOS services, without host
disk access. It checks option parsing, confirmation/cancellation, track
order and all CHRN fields, the full 4096-byte boot image, optional verify,
BIOS failures and cleanup. BDOS deliberately corrupts ES and working
registers. Actual kernel/floppy testing is still required.
