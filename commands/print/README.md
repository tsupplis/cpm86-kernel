# PRINT V1.1 reconstruction

`print.a86` is the maintained disassembly of `../../base/print.cmd`.
`printorg.a86` is the frozen original source. Both currently reproduce the
entire 5,120-byte CMD exactly, using ASM86 and GENCMD:

```sh
make -C commands/print check
```

The file contains a 128-byte CMD header, 3,024 bytes of CODE, 1,952 bytes of
DATA and 16 trailing bytes of record padding. CODE and DATA each start at
zero. All 1,092 instructions are mnemonics. DB/DW declarations represent
actual configuration, strings, saved state, reserved space and padding;
`code_patch_area` is explicitly zero-filled DB storage.

## What PRINT does

This is a resident printer/spooler, rather than a simple foreground file
copy. The startup code parses filenames from the command tail, saves the
submitting user number, installs INT E2h/E3h handlers and terminates with
DX=1 to retain its memory. Later invocations locate that resident through
the E2 vector and append filenames to its command-tail queue. `PRINT OFF`
requests removal. The queue must have room, and its owner must be the same
CP/M user.

The background worker saves the foreground BDOS disk/DMA context, switches
to its own stack and user, reads up to four 128-byte records, and emits a
bounded number of characters per slice. It expands tabs to eight-column
boundaries and resumes pending characters when the printer becomes ready.
Ctrl-Z and end of file advance to the next job. Separate configuration bytes
control scheduling, printer status checks and an optional console BIOS hook.

The retained directory-spool mode searches for files with a configurable
extension (SPL by default) and includes completed-file deletion. This mode
is disabled in the shipped option block. Original debug traps, unused
helpers and mode-specific behavior are preserved.

## Compatibility and fixed addresses

The banner identifies CP/M-86 V1.1 and startup requires BDOS version 0022h.
This reconstruction is not a Concurrent CP/M port. PRINT relies on CP/M
internal state returned by BDOS 49 plus fixed kernel offsets, including the
BIOS gateway at 2200h, console entries at 2506h/2509h and abort state at
24AFh. Uncertain internal fields retain address-based names.

CODE offsets 0BB1h (resident DATA segment) and 0BC5h (reentrancy lock) are
also used to access a previously loaded copy. Keep those interfaces in mind
before modifying the resident layout or mixing different PRINT versions.

`make check` compares headers, code, data and padding against the original,
proving that no original addresses, displacements or encodings changed.
It does not run the resident interrupt handlers or exercise a printer.
The distribution Makefile uses `commands/print/print.cmd` for every image
that includes PRINT.
