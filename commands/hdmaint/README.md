# HDMAINT 1.1N / frozen 1.1 reconstruction

`hdmaint.a86` is the maintained 1.1N source. `hdmtorg.a86` is now frozen:
its build must continue to reproduce the original 25,088-byte executable.
Build and verify from the repository root:

```sh
make -C commands/hdmaint check
```

This binary supports **both CP/M-86 2.2 and Concurrent CP/M-86 3.1**. At CODE
0042h/0047h it accepts BDOS version words 1431h and 0022h, then selects separate
initialization paths. The identical original also exists in `ccpm86-kernel`.
The Concurrent path requires a local, dynamic console and claims the console
and disk mutex queues; the CP/M path uses fixed XIOS locations. This preserves
the original compatibility and hardware assumptions, without extending them.

## Source layout

The source follows the FUNCTION/BATCH reconstruction pattern: meaningful
routine labels, comments explaining control flow and layouts, symbolic menu
callbacks and data pointers, and real mnemonics for the utility's instructions.
The main sections cover OS setup, disk discovery, partition editing, volume
creation, verification, CP/M options, cleanup, the display interpreter, input,
and BIOS/XIOS disk access. Unused helpers and original behavior are retained.

The DATA group contains these **serialized disk payloads**, grouped and labelled:

| DATA offsets | Contents |
| --- | --- |
| 0EFEh–10FDh | Default MBR/bootstrap and partition sector |
| 10FEh–12FDh | First secondary boot sector |
| 12FEh–14FDh | Duplicate secondary boot sector |
| 14FEh–16FDh | Default setup sector |
| 16FEh–18FDh | Default CP/M label sector |
| 18FEh–30FDh | Tertiary system loader and its reserved storage |

The executable stages are maintained as real, labelled assembly sources:

- `mbr.a86`: relocates the MBR, validates the active partition, reads its boot
  sector and checks the AA55h signature.
- `bootsect.a86`: reads the disk label and system loader into 3000:0000h, then
  enters the loader at 3020:0000h. Both on-disk copies use the same source.
- `loader.a86`: opens CPM.SYS or CCPM.SYS, validates its CMD header, loads it
  and transfers control. It includes the reduced CP/M BDOS, console services,
  hard-disk BIOS, label validation, block cache and bad-block remapping.

Following DSKMAINT, ASM86 assembles each stage, H862BIN creates its flat image,
and BIN2ASM generates includes consumed directly by the main sources (ASM86
does not allow nested includes). Only actual data,
reserved storage and padding use DB. The setup and label sectors remain data
in `hdboot.inc`. Normal builds never extract bytes from the reference CMD.

CODE/DATA origins preserve the boot stages' shared offset space. Runtime-only
buffers beyond the serialized loader use EQU addresses. A SEGFIX macro keeps
short indexed CS overrides from widening under ASM86. `bootcheck.py` removes
only the exact declaration-only AUX records for the MBR/boot-sector far-jump
targets before H862BIN; unexpected declarations stop the build.

Display streams contain literal text/escape bytes, NUL terminators and FFh
followed by near CODE callbacks. Callback arguments that address DATA are also
symbolic. Menu action vectors contain ten near CODE pointers, indexed by the
installed F1–F10 definitions. Disabled entries are preserved.

## Build and verification

The frozen build preserves the original groups: CODE 159h paragraphs (5,520 bytes),
DATA 4BDh paragraphs (19,408 bytes), and EXTRA with zero file bytes and an
800h-paragraph (32 KB) minimum allocation. The private 256-byte stack is in
DATA. Startup aligns the EXTRA DMA segment to a 16 KB boundary.

The BIOS reset target is declared in an absolute FFFFh code segment so JMPF
can use a proper symbolic operand. ASM86 emits a declaration-only H86 record
for it. The Makefile removes that exact record before GENCMD; otherwise GENCMD
adds an unwanted AUX descriptor. No executable bytes are patched. A SEGFIX-only
CODEMACRO retains the original redundant CS prefix on the display callback
CALL, also without raw opcode declarations.

`make check` compares all three boot images and the frozen `hdmtorg.cmd`
against the reference. The maintained build is checked separately for its
1.1N banner, CMD group layout, and unchanged embedded boot images. The frozen
source digest is also checked. These checks do not run disk writes in a guest.

## 1.1N correction

The CP/M initialization path never assigned the floppy-drive value. Its zero
initial value made the first hard disk appear as B: even with two floppies.
Concurrent CP/M already obtains the **highest floppy index** (count minus one)
from XIOS function 20h. The shared display calculation adds one to this index.

The CP/M path now reads ROM BIOS INT 11h equipment bits 7:6 into
`floppy_max_index`, using the same representation. Thus one floppy gives B:,
two give C:, three give D:, and four give E: for the first hard disk; the next
hard disk receives the following letter. Concurrent initialization is unchanged.
This fixes display lettering; physical BIOS drive numbers remain 80h/81h.
The existing IBM PC assumption of at least one floppy is retained.

The maintained CODE and DATA may move as instructions/text are added; their
symbolic references are rebuilt. Embedded disk-stage bytes stay unchanged.

## Historical reference

The later Digital Research `cdos-41-oem/D10/h70.a86` and its libraries were used
to identify terminology and structures, particularly `hdxtdefs.lib` and
`hdiskio.lib`. H70's revision history records the December 1983 CCP/M 3.1
adaptation as version 1.1; its April 1984 version 2.0 was a major rewrite with
PC-DOS support, a different menu interpreter and a newer loader. The later
sources help explain this program, but their additions are not substituted
for the version 1.1 binary being reconstructed here.

The OEM D11/pcboot1.a86 and D10/cpmboot2.a86/cpmboot3.a86 provide boot-stage
terminology. Their later memory-relocation changes are not applied. Matching
routines in the repository BDOS source supply the loader's `bd_` routine names.
