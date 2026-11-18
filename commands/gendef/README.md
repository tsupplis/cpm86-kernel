# GENDEF source rebuild

GENDEF reads `name.DEF` and emits assembler disk tables in `name.LIB`.
Usage: `GENDEF name $BCOZ` (options are optional and combinable).
B emits only DPBs and DPB aliases; C includes comments, O uses offset-relative
labels, Z selects Z80/8080/8085 output instead of 8086/8088.

For example, `GENDEF PCDISKS $BC` generates commented DPBs without disk
parameter headers, sector translation tables, buffer-size symbols or scratch
storage. The caller supplies those structures and controls table placement.
Omitting B preserves the historical output.

`ORG symbol` may precede a `DISKDEF` in the input. It emits an assembler
`org` directive without changing segments. Define the symbol as a numeric
address in the including source. Numeric operands, expressions and extra
operands are rejected; existing definitions without ORG are unchanged.

The PC BIOS defines `FD160`, `FD320` and `FDTABLES`, then includes
`pcdisks.lib` directly. No intermediate extraction or format copies are used.

Run `make` to build and `make check` to compare generated LIB files with
the shipped tool under emu2. Build with the same Intel PL/M-86 / ASM86 / LINK86 / LOC86 / OH86
and GENCMD tools used by `commands/ed`. The Makefile derives the DATA
base and minimum allocation from the locator map. Sources originate in
`ossrc/mpm862sr/D8`; module order follows `gendef.cpm`.

Two source adaptations are explicit:

- `scd.a86`: add `NAME SCD`, required by the available Intel assembler.
- `gemit.plm`: restore Ctrl-Z padding of the final partial output record.
  The archived MP/M source comments this loop out, causing truncation under
  CP/M-86. No MP/M-only unfilled-byte FCB field is written.

The scanner accesses options through `fcb16(1)` (base-page 006Dh), matching
the intention of Digital Research patch 03. No binary-address patch is
applied to the rebuilt layout.

Validation: all four PL/M modules compile without errors. The compiler
reports 14 offset-truncation warnings in legacy byte arithmetic. Link/locate
reports group enlargement and no explicit start address; GENCMD starts CODE
at zero through the startup jump. These diagnostics are retained in listings.
The rebuilt CMD differs from the shipped binary in compiler output/layout.

Under emu2, `make check` passes 50 checks across the PC and Apple
format definitions and a skewed format with a DPB alias. Default, $C, $O,
$Z and $COZ output remains byte-identical to the shipped tool, including
CP/M record padding. Adding B retains exactly the corresponding DPB
assembler statements and aliases, with no other emitted structures.
Ten checks cover symbolic placement in full and DPB-only modes; ten reject
malformed ORG operands. `pcold.def` retains the pre-ORG PC definition for
comparison with the original generator.
This does not establish correctness for every geometry or error case.

Distribution recipes and `tools/gendef.sh` use the rebuilt
`commands/gendef/gendef.cmd`. The original `base/gendef.cmd` remains the
reference used by `make check`.
