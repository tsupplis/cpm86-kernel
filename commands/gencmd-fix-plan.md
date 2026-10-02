# Plan: Fix gencmd regression

## Root Cause

Two changes in `gencmd.plm` vs `genref.plm` (the working reference) cause the bugs:

### Bug 1 — `READBYTE` evaluation order (primary bug)

**Old (working):**
```plm
READBYTE: PROCEDURE BYTE;
    DECLARE B BYTE;
    B = READHEX; RETURN SHL(b,4) OR READHEX;
    END READBYTE;
```

**New (broken):**
```plm
READBYTE: PROCEDURE BYTE;
    RETURN SHL(READHEX,4) OR READHEX;
    END READBYTE;
```

PL/M-86 does **not guarantee left-to-right evaluation order** of function
arguments in an expression. The compiler may call the second `READHEX` before
the first, swapping the two nibbles of every byte read from the hex file.

With swapped nibbles:
- Hex bytes are decoded incorrectly → `INVALID HEX DIGIT` crash in self-rebuild
- Segment names read from the command tail are wrong → `get$segmt` never matches
  `'8080 '` → `comline$error` → empty `hellob.cmd`

### Bug 2 — `OUTPUT$CREATED` declared before `segmts` (secondary)

`DECLARE OUTPUT$CREATED BYTE` is inserted before `segmts` in source order.
In PL/M-86, module-level variables are allocated in DATA in source order.
This shifts `segmts` and `header` each by 1 byte relative to the reference
build — meaning the rebuilt `gencmd.cmd` has a different data layout than
`genref.cmd`, so `make check` (`cmp gencmd.cmd test.cmd`) will fail even
after Bug 1 is fixed.

**Fix**: move `DECLARE OUTPUT$CREATED BYTE` to after the `header` declaration.

---

## Sub-Tasks

### Sub-Task 1 — Restore `READBYTE` intermediate variable

**Intent**: Restore guaranteed left-to-right nibble reading order.

**Fix** — revert `READBYTE` to use the intermediate variable:
```plm
READBYTE: PROCEDURE BYTE;
    /* READ TWO HEX DIGITS */
    DECLARE B BYTE;
    B = READHEX; RETURN SHL(B,4) OR READHEX;
    END READBYTE;
```

**File**: [`gencmd/gencmd.plm`](gencmd/gencmd.plm) — the `READBYTE` procedure
(currently around line 441).

**Expected outcome**: `gencmd hellob 8080` correctly sets `t8080 = true`,
`get$segmt` matches `'8080 '`, output matches `hellob.ref`.

**Status**: `[ ] pending`

---

### Sub-Task 2 — Move `OUTPUT$CREATED` after `header`

**Intent**: Restore `segmts` and `header` to their original DATA addresses
so the rebuilt `gencmd.cmd` is byte-identical to the reference.

**Fix** — move `DECLARE OUTPUT$CREATED BYTE` from before `segmts` (line 65)
to after the `header` declaration (after line 79):

```plm
/* Remove from here (line 65): */
DECLARE OUTPUT$CREATED BYTE;

declare segmts(11) structure ...

declare header (15) structure ...
    initial (...);

/* Add here (after header): */
DECLARE OUTPUT$CREATED BYTE;
```

**File**: [`gencmd/gencmd.plm`](gencmd/gencmd.plm) lines 65 and 79.

**Expected outcome**: `segmts` and `header` addresses in the compiled binary
match the reference; `make check` passes (`cmp gencmd.cmd test.cmd`).

**Status**: `[ ] pending`

---

## Verification

After both fixes, rebuild and run:
```sh
cd gencmd
make clean && make
make check
```

`make check` runs:
1. `cmp gencmd.cmd test.cmd` — self-rebuild byte-identical
2. `cmp hellob.cmd hellob.ref` — 8080 mode byte-identical
