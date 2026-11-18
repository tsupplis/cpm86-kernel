# Fixed interfaces and external address dependencies

Source audit: 16 November 2026. This is a compatibility inventory, not a new
public API. It records confirmed source dependencies; it does **not** certify
that all imported binaries or external programs have been audited.
See [mapping.md](mapping.md) for allocation, overlays and available space.

`K:` means an offset within the loaded kernel segment, not a physical address.
`S` means the system-data pointer returned in ES:BX by BDOS function 49 (31h).
For the PC kernel, S is K:24A0h. Hardware addresses name their segment explicitly.

**What “fixed” means here:** changing the address or layout can break a named
consumer. Keep it unchanged unless that consumer is updated and tested too.
A pointer slot and the table it points to are different: the slot may need to
stay at the same address even when the table can move.

The tables below identify the addresses, their consumers and what must stay unchanged.

## Kernel and command contracts

PC means both maintained `pcbios.a86` and experimental `pcbioexp.a86`, unless
otherwise stated. Shared BDOS/CCP contracts also affect the MBC and AD8088 builds;
PC BIOS configuration and clock contracts must not be assumed on those machines.

| Address | What is stored there | Who uses it | What must stay unchanged |
| --- | --- | --- | --- |
| INT E0h; vector at `0000:0380h` | Address of the BDOS interrupt handler | Commands call it; each BIOS installs it | Interrupt number, four-byte vector and calling convention |
| `K:0B06h` | BDOS handler entry | PC, MBC and AD8088 BIOSes | Entry address and calling convention |
| `K:0000h`, `0003h`, `0006h` | CCP cold, abort and hot entry jumps | BIOS startup and warm boot | Entry addresses and jump meanings |
| `K:0009h` | CCP command buffer | BDOS, through `COMBUF` | Buffer address and layout |
| `K:0805h` | CCP submit flag | BDOS, through `MDSUBE` | Address and one-byte flag meaning |
| `K:2500h`–`253Ch` | BIOS entry jumps, three bytes apart | BDOS; direct BIOS calls; PRINT uses `2506h` and `2509h` | Entry addresses, order and calling conventions |
| `K:2200h` / `2202h` | BDOS's BIOS-call offset and segment | PRINT replaces and restores this pointer | Both word addresses and the far-call convention |
| `K:2310h` (`INPARB`) | BDOS parameter byte | PRINT saves and restores it | Address, byte size and meaning |
| `K:2313h` (`FLOMOD`) | BDOS file-operation state | PRINT saves and restores it | Address, byte size and meaning |
| `K:2321h` (`FCBOFF`) | BDOS FCB offset | PRINT saves and restores it | Address, word size and meaning |
| `K:2327h` (`AFWFCB`) | BDOS working-FCB state | PRINT saves and restores it | Address, byte size and meaning |
| `K:2393h` (`CNUMCB`) | BDOS memory-control state | PRINT reads it | Address, byte size and meaning |
| `K:24A5h` | Current user number | PC BIOS status line | Address and byte size |
| `K:24AFh` | BDOS abort-mode flag | PC BIOS reads it; PRINT reads/writes it | Address, byte size and flag meanings |
| `K:24B7h` | Default drive | PC BIOS | Address and byte size |
| `K:24BDh`–`24BFh` | Numeric hour, minute and second | PC BIOS timer; storage belongs to the BDOS data area | Three-byte allocation at these addresses |
| `S+20h` = `K:24C0h` | 17-byte `mm/dd/yy,hh:mm:ss` clock | TOD, shipped ATINIT and PC BIOS timer | Start address, separators and field sizes; do not insert century bytes |
| `K:24D2h` | 14-byte status message | PC BIOS copies it to the status line; external writer not found | Address and 14-byte allocation |
| `S+40h` = `K:24E0h` | Console width | CCP reads it directly; DDT86 reads `S+64` decimal; PC BIOS writes it | Address and byte size |
| `K:254Eh` | Pointer to function-key definitions | FUNCTION and HDMAINT access definitions; SETUP copies them | Pointer slot stays here; definitions remain two sets of ten 20-byte entries. Their address is read from the slot |
| `K:2550h` | Pointer to current/required disk byte (`DISK`) | Slot exported by PC BIOS; no external reader found in the local source scan | Preserve the exported pointer slot and one-byte disk value |
| `K:2552h` | Pointer to serial settings | CONFIG accesses settings; SETUP copies them | Pointer slot stays here; preserve the two-byte settings layout |
| `K:2554h` | Pointer to logical I/O assignments | ASSIGN accesses assignments; SETUP copies them | Pointer slot stays here; preserve the five-word table layout |
| `K:2556h` | Pointer to FIDD storage description | PC BIOS and FIDD clients | Pointer slot stays here; preserve size and segment words |
| `K:2558h` | Pointer to current screen-mode byte (`CRTMOD`) | Slot exported by PC BIOS; no external reader found in the local source scan | Preserve the exported pointer slot and one-byte screen-mode value |

For the six pointer slots, “the slot stays here” does **not** mean the pointed-to
data must stay at its current address. Moving that data is safe only if every
consumer follows the pointer rather than also using a hardcoded data address.

Evidence: [BDOS shared definitions](bdos.a86), [PC BIOS aliases and vectors](pcbios.a86),
[CCP patch](ccp.a86), [PRINT](commands/print/print.a86),
[TOD](commands/tod/tod.a86), [SETUP](commands/setup/setup.a86),
[FUNCTION](commands/function/function.a86), [CONFIG](commands/config/config.a86),
[ASSIGN](commands/assign/assign.a86), [HDMAINT](commands/hdmaint/hdmaint.a86),
[DDT86](commands/ddt86/ddt86.a86), [MBC](mbcv20.a86),
[mixed-mode MBC](mbc816.a86), and [AD8088](ad88bios.a86).
The corresponding EXP sources retain these shared contracts. The
[CP/M-816 configuration](patching/pc816.txt) adds 8080 CP/M-80 2.2 execution
on V20/V30 through the BIOS; it adds no BDOS function or Z80 support.
SETUP copies the key, serial and assignment tables through their pointers;
its other saved options come from a configuration sector, not from `2550h`.
DDT86 reads console width at `S+64` decimal after `GETDATAPAGEADDR`.
The status-message read is in the PC BIOS timer routine `TIMINT10`.

## Native floppy implementation

Both BIOSes retain the existing BIOS entry points, 160K/320K DPB slots and
4K disk buffer. The reset and geometry hooks delegate to `pcfloppy.lib`;
`pcdisks.def` supplies all four DPBs through GENDEF. New-format tables and
resident code are appended. Hard-disk geometry handling is unchanged.

The old runtime patch package is retired. Its instruction-replacement layout
is not an API supported by the native BIOS. `tools/bioschk.py` verifies the
native hook targets, preserved unrelated instructions and module boundaries.

## Raw disk and hardware contracts

These bypass some OS services but are not all private kernel addresses.
Distinguish ROM BIOS interfaces from the CP/M BIOS jump table.

| Address / interface | Owner | Who uses it | What must stay unchanged |
| --- | --- | --- | --- |
| `0000:004Ch`, far pointer (INT 13h) | ROM BIOS / IVT | HDMAINT saves and calls gateway | Interrupt-style flags and return convention |
| `0000:0476h`, byte | PC BIOS data area | HDMAINT saves, masks low three bits, restores | Byte address and controller-option bit meanings |
| `0000:0078h`, far pointer (INT 1Eh) | ROM BIOS diskette parameter table | PC BIOS; DFORM and floppy-maintenance paths install/restore tables | Pointer restoration, table layout and lifetime |
| INT 13h, CHS and DMA buffer | ROM BIOS | DCOPY/DCOMP, DFORM/DSKMAINT and HDMAINT raw operations | CHS geometry, DMA boundaries, error reporting and cache invalidation |
| BDOS 50 BIOS packet; selected DPH/DPB | CP/M BIOS | CHKCPMFS raw backend | DPH/DPB layouts returned by BIOS; 128-byte logical-record units |
| BDOS 49 plus XIOS structures/gateways | Concurrent OS, not CP/M-86 | Shared disk/checker Concurrent branches | OS-specific structure offsets, gateway calling conventions and disk locking |
| MBR `01BEh`, four 16-byte entries; signature `01FEh` | On-disk format | HDMAINT, MBR/bootstrap loaders | Entry layout and signature; preserve slots/bootstrap according to chosen policy |
| DR partition label, DPB and allocation limits | On-disk format and kernel | HDMAINT/loader write; BIOS reads; checker interprets selected DPB | Label fields, checksum, DPB layout and allocation limits |
| IVT `0000:0388h`/`038Ch` (INT E2h/E3h) | PRINT resident installation | PRINT reads/writes vectors | Vector addresses and installation/removal convention; separate from INT E0h |
| IVT `0000:0000h`, `006Ch`, `0070h`, `0398h` | CPU/PC interrupt conventions | PC BIOS divide, break, timer and unknown-disk handlers | Vector addresses, segments, installation and restoration |

Evidence: [disk tools](commands/disk/), [DFORM](commands/dform/dform.a86),
[CHKCPMFS raw backend](commands/chkcpmfs/rawio.a86),
[HDMAINT gateway](commands/hdmaint/hdmaint.a86), [loaders](commands/hdmaint/).
An identical numeric address in a loader's own segment is **not** automatically
a kernel dependency (for example `ldlarge.a86` allocation storage at `2200h`).
Likewise command-local dispatch tables and PRINT's own resident slots are not
kernel fields.

## Date extension constraints

The existing display already holds century plus year (`BCENT` + `BYEAR`).
`BCENT` is BIOS-owned state, initialized from RTC when supported and incremented
on century rollover. No external source consumer of its absolute address was
identified in this pass; do not invent a new hardcoded TOD dependency on it.

Keep `S+20h` and its 17-byte format unchanged. Inserting two year bytes would
shift the time fields and corrupt existing consumers. A full-year setter needs
an explicitly discoverable extension and a defined policy for legacy YY writes.
The RTC helper at `4400h` is cold-only overlay storage; it cannot hold a
resident setter or century variable.

The maintained PC BIOS renders the century using a fixed 80 cutoff:
`00–79` displays as 20xx; `80–99` as 19xx. This changes display only;
`BCENT`, the 17-byte clock and all existing addresses remain unchanged.
See [the display patch](patching/century.txt).

## EXP buffered console input

Function 10 retains its buffer layout and caller-supplied maximum. EXP delegates
PC-console input to `lineedit.lib`; other console routing retains the original
editor. Recall stores at most 127 characters. This is an EXP enhancement,
not an additional BDOS function or a CP/M Plus API claim.

Private gateways at `K:53B0h` (editor), `53B3h` (abort cleanup), and `53B6h`
(keyboard mapping) serve the EXP build only. Existing public addresses stay
fixed. Dynamic BIOS allocation starts at `END_EDIT`, after editor storage.
