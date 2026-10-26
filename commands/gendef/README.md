# GENDEF — analysis and deferred reconstruction

This directory records the investigation of `../../base/gendef.cmd`.
Reconstruction is deferred: there is no source build or Makefile here yet.
Distribution images continue to use the existing `base/gendef.cmd` binary.

## Purpose

GENDEF is a BIOS disk-table generator. It reads a disk-format description
from a `.DEF` file and emits assembly definitions in a `.LIB` file for use
when assembling a BIOS:

```text
Disk-format description (.DEF)
             |
           GENDEF
             |
Assembly definitions (.LIB)
             |
        BIOS assembler
```

The `.LIB` output is assembly source, not a binary linker library. GENDEF
does not format disks or generate CMD executables; GENCMD is the separate
executable-generation utility.

Input parameters describe the disk number, first/last sectors, sector skew,
allocation-block size, disk size, directory-entry count, directory-checking
size and reserved tracks. The historical source also has compatibility and
permanent-drive parameters.

The generated definitions include:

- Disk parameter headers and blocks, including block shift/mask, extent
  mask, disk/directory limits, allocation bits and reserved-track offset.
- Sector translation tables for skewed layouts.
- Directory-buffer, allocation-vector and checksum-vector storage and sizes.
- Optional comments explaining the calculated parameters.

## Command line

The help embedded in the shipped binary identifies it as
`DISKDEF Table Generator, Vers 1.0` and documents:

```text
GENDEF name $<parameters>
```

It reads `name.DEF` and creates `name.LIB`. The angle brackets denote the
optional parameter list in the help text, rather than a literal filename.
The documented option letters are:

| Option | Meaning |
| --- | --- |
| C | Include disk-definition comments |
| O | Generate offset-relative labels |
| Z | Generate Z80/8080/8085 definitions instead of the default 8086/8088 output |

These details were read from the binary and historical source. No sample
input has yet been run, and the complete accepted input grammar has not
been validated against this particular executable.

## Historical sources available locally

The sibling archive directory `../ossrc/mpm862sr/D8/`, relative to the
repository root, contains:

| File | Role |
| --- | --- |
| `gendef.plm` | Main DISKDEF parser and disk-parameter calculations |
| `gscan.plm` | Scanner and input handling |
| `gtoken.plm` | Token support |
| `gemit.plm` | Assembly-output support |
| `glit.plb`, `gpas.plb`, `copyrt.lit` | Supporting declarations/includes |
| `scd.a86` | Startup/support assembly used by the historical build |
| `gendef.cpm` | Historical compile, link, locate and H86 build procedure |

The build procedure explicitly links `scd.obj`, `gendef.obj`, `gtoken.obj`,
`gscan.obj` and `gemit.obj`. The introductory comments in `gendef.plm` use
older names (`token.plm` and `emit.plm`) for two modules; the supplied build
procedure gives the names actually present in this archive.

This is an MP/M-86 source archive. Its presence does not establish that it
exactly matches the CP/M-86 binary in this repository. The repository README
records Digital Research patch 03 as applied to GENDEF; that patch and any
other version differences still need investigation.

## Relationship to this project

Current image recipes package GENDEF among the assembler tools but do not
invoke it to build the kernel or images. Existing BIOS assembly already
contains disk definitions. Comments in `mbc816.a86` and `mbcv20.a86` also
refer to storage areas created by GENDEF.

GENDEF remains potentially useful when defining new disk formats or
rebuilding historical BIOS configurations. It is not a prerequisite for
continuing the present kernel build.

## Proposed future approach

Prefer investigating a source rebuild before committing to disassembly:

1. Inventory the historical modules and their include dependencies.
2. Identify the shipped binary's revision and Digital Research patch 03.
3. Adapt the historical build to the available PL/M-86 toolchain.
4. Compare representative generated `.LIB` files against the shipped tool;
   compare complete CMD bytes if the source revision permits exact recovery.
5. If substantial differences remain, use the source to guide a labelled,
   commented disassembly and preserve a frozen original, as with other tools.

No reverse engineering, source adaptation, build integration or binary
changes are performed as part of these notes.
