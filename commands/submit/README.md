# submit

Reconstruction of `base/submit.cmd` — the classic CP/M-86 1.1 SUBMIT.

The CCP/M-86 SUBMIT 1.3 source that used to live here was abandoned: it contains no `$$$`
handling at all and spawns commands through fn 150 (`mpm_clicmd`), so it is a different program
rather than a port candidate. What builds here instead is DRI's CP/M 2.2 `submit.plm`, ported to
PL/M-86, plus `scd.a86` for the CP/M-86 entry/exit.

## Why we believe this is the original source

`base/submit.cmd` was disassembled in full and its data segment matches the CP/M 2.2 source
declaration for declaration:

| declaration | address in `base/submit.cmd` |
| --- | --- |
| `ln(5) byte initial('001 $')` | `0134h` |
| `dfcb(33) initial(0,'$$$     SUB',...)` | `0139h` |
| `dcnt` | `015Ah` |
| `sstring(128)` | `015Bh` |
| `rbuff(2048)` | `01DDh` |
| `copyright(*)` | `09F0h`, byte-identical string |

That is not a coincidental layout. The CP/M-86 build is the 2.2 program recompiled, so the source
here is a transformation of DRI's, not a reimplementation.

## The two modules

`scd.a86` is the entry/exit stub — the only part with no 2.2 counterpart. It saves `SS:SP` into the
code segment, switches the stack to `DS:0130h`, calls `plm`, and on return sets the CCP's
submit-mode flag `MDSUBE` at `0805h` (see `../../mapping.md`) before BDOS fn 0. It assembles
**byte-identical** to the original's first `70h` bytes, including the five `nop`s and the vestigial
`mov cl,al` that computes a drive/user byte for `SUBFCB` and never stores it.

`submit.plm` is the 2.2 source with the PL/M-80 module-entry `jmp` trick dropped, `buff`/`sfcb`
taken as externals instead of `at()` overlays, `submit` renamed `plm: procedure public`, and
`call boot` removed so the stub performs the exit.

## Three things the 86 binary corrected in the 2.2 source

Each was found by diffing our build against the original, not by guesswork:

1. **`error` ends with `call mon1(0,0)`** — a direct BDOS reset — not 2.2's `stackptr = oldsp`.
   This matters: on error there is no usable `$$$.SUB`, so it must reset *without* setting
   `MDSUBE`, while the normal path returns through the stub and *does* set it.
2. **`declare oldsp address` survives** as a vestigial word at `0130h`, even though the stub now
   owns the stack save.
3. **`^X` upcases with `- 'A'`** (`sub al,41h`), not 2.2's `- 'a'`. Since `getsource` already
   upcases, the 2.2 form would reject every control character.

## Why the build is not byte-identical

The data segment **is** exact — 2768 bytes, every variable at the original's offset. The code
segment is 1020 bytes against the original's 1040. That 20-byte delta is fully accounted for:

- **8 bytes are not code.** The original's real code ends at `0407h` with `5D C3` (`pop bp / ret`,
  end of `getrbuff`); `0408h`–`040Fh` are zero fill to the paragraph boundary. The honest
  comparison is 1032 vs 1020.
- **12 bytes are codegen.** Aligning both instruction streams shows every differing instruction
  falls into one of these, with no behavioural difference anywhere:

| category | original | ours |
| --- | --- | --- |
| procedure entry alignment | 6 procedures at odd addresses | word-aligned, +1 pad byte each |
| jump islands | chained short `jmp`s to a shared continuation | direct near jumps |
| BYTE-boolean idiom | `mov al,[x]` / `rcr al,1` / `jc`, via `AL`+stack | `test byte [x],1` / `jnz`, via `CL`/`DL` |
| constant zero | `mov al,0` / `mov ah,0` | `xor ax,ax` / `cbw` |
| displacement folding | `buff(i+1)`, `buff(i+2)` folded into `[bx+81h]`, `[bx+82h]` | recomputes `bx` |

Note that two of those make *our* code larger; the differences partly cancel.

The clearest single example is the last instruction of `getrbuff`, where the two builds are
otherwise byte-identical:

```
original   89 C3     mov bx,ax
ours       8B D8     mov bx,ax
```

Same instruction, same length, two valid encodings. No source change can influence that, which is
why there is no byte-parity `check` target in the Makefile — full equality is unreachable with
PL/M-86 X304. The source is correct; the compiler is a different build from DRI's.

## Verification

Compiles with 0 warnings and 0 errors. All 20 procedures present in the same order as the
original. Confirmed on real hardware (PCE IBM PC, CP/M-86 1.1): `submit test` read `TEST.SUB`,
wrote `$$$.SUB`, and the CCP consumed and executed the submitted commands.

`make cpmtest.img` builds a test floppy with `submit.cmd` and `test.sub` for this purpose.
