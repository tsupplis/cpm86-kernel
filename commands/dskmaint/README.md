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
verification pass after formatting and writing the boot track.
Without V, there is no verification pass. Geometry is fixed at 40 cylinders,
eight 512-byte sectors per head, just as in DSKMAINT.

Options may be combined, split into groups, and written without closing
brackets: `DFORM A:[1V]`, `DFORM A: [1] [V`, and `DFORM A: [1V` are equivalent.
Lowercase is accepted. Unknown options, conflicting 1/2 selections and
malformed or empty command lines display usage without a disk operation.

DFORM displays the drive, capacity and verification setting and requires
Y confirmation. N or Ctrl-C cancels. It formats once and exits; failures
are retried five times before reporting the final BIOS/XIOS status. Raw BDOS
console I/O routes Ctrl-C through cleanup rather than terminating with the
BIOS diskette parameter vector still patched or CCP/M locks still held.
The CP/M path restores the vector before resetting the drive login state.
The CCP/M path releases MXdisk and restores console/P_KEEP/priority state.

The formatted disk uses DSKMAINT's boot-track layout: E5 fill,
shared boot code at offset 0, sides byte at 1FFh and shared loader at 900h.
DFORM selects the loader retry byte for the detected OS; copy CPM.SYS or
CCPM.SYS using PIP's [R] option to complete a bootable disk.

The same DFORM sources are used in the CCP/M repository. One binary
supports CP/M-86 1.1 / BDOS 2.2 through IBM PC ROM BIOS and CCP/M-86 3.1
(OS version 1431h) through native XIOS in `ccpmio.a86`. Other versions
are rejected before disk access. The historical DSKMAINT, boot and loader
sources remain specific to this CP/M repository.
A private 512-byte stack and an 8 KiB resident reservation provide room for
a 4 KiB track buffer aligned at a physical 4 KiB boundary for BIOS DMA.

## Validation

`make check` retains the original DSKMAINT byte comparison and runs
`make check-dform`. The latter executes the linked DFORM CMD under emu2
using a NASM test harness with simulated BDOS/BIOS/XIOS services, without host
disk access. It checks option parsing, confirmation/cancellation, track
order and all CHRN fields, the full 4096-byte boot image, optional verify,
BIOS/XIOS failures, queue/console exclusion and cleanup. BDOS deliberately
corrupts ES and working registers. Actual kernel/floppy testing is still required.
