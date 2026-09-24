# CP/M-86 Compatibility Report — CCP/M-86 3.1 Command Sources

Scope: the command sources under `commands/` that overlap with the compiled tools already
shipped in `base/`. All recommendations below are **tool-source-only** — nothing here proposes
changing the kernel (`bdos.a86`, `pcbios.a86`, etc.).

## Kernel facts used throughout this report
- BDOS function 12 (get version) returns **AL=0x22** (v2.2), **BH=0** ("simple CP/M" — never
  MP/M-86 or Concurrent CP/M-86).
- Dispatch table (`bdos.a86`, `IXMAIN`) implements functions **0–40 and 47–59** only. The entry
  code (`bdos.a86` ~L290) handles 41–46 by doing `CL := CL-6` and reusing the 0–40/47–59 table —
  so calling fn *N* in that gap actually invokes the handler at table slot *N-6*, **not a no-op**.
  Confirmed per-function effects: fn 44 → slot 38 → `NOPROC` (bare `RET`, harmless). fn 45 → slot 39
  → `NOPROC` (harmless). fn 46 → slot 40 → `MWRITZ` (**write random with zero fill** — a real hazard,
  not benign).
- **Verified on real hardware** (IBM PC under PCE, CP/M-86 1.1 / BDOS 2.2) with the throwaway probe
  `commands/pip/bptest.a86`: fn 12 returns `AX=0022` (AH=00 OS type, AL=22 version); fn 44 and fn 45
  both return `AX=0000` with no side effect, empirically confirming the `CL-6` gap analysis above.
- Base page word at offset **0006** holds the **last valid offset of the program's data segment**.
  Verified by loading PIP under DDT86 (`Epip.cmd`, `D0,F`): the word read `8009`, exactly matching the
  `DS ...:8009` segment end DDT86 reported; the words at 0000 and 000C likewise matched the CS and ES
  ends. This matters because `scd1.a86` exposes that word as `MAXB` with a misleading CP/M-**80**
  comment ("ADDR FIELD OF JMP BDOS"), and PIP sizes its copy buffers from it.

## Resolution strategies
- **A — Patch guard + kernel-native substitute**: relax the tool's version check to accept BDOS
  2.2/BH=0, and replace an extended BDOS call with an existing kernel-exposed equivalent. No
  feature lost.
- **B — Simplify**: patch the guard and drop the specific feature that depends on a missing
  extended call, keeping the rest of the tool. Some feature loss, tool stays useful.
- **C — Abandon**: no in-kernel substitute exists and simplification would gut the tool's purpose;
  always paired with a concrete alternative.

## Verdicts

| Status | Tool | Guard found | Real API gap | Verdict | Strategy | Suggested change |
|---|---|---|---|---|---|---|
| n/a | **asm86** | — | — | — | — | Excluded from evaluation (already known-good). |
| n/a | **gencmd** | — | — | — | — | Excluded from evaluation (already known-good). |
| **DONE** | **ddt86** | Soft — skips enabling extended error mode if BDOS<0x30 ([ddt86.a86](ddt86/ddt86.a86#L184)) | fn 45 only called when the (never-true) soft check passes | **LOW** | none | Works as-is; no source change needed. |
| **DONE** | **ed** | Soft — 5 checks all gated behind one `has$bdos3` flag that stays false on this kernel ([ed.plm](ed/ed.plm#L2044)) | fns 102/103 (xfcb) only reachable when `has$bdos3` is true | **LOW** | none | Works as-is; CP/M-3-only password/xfcb features silently stay off, core editing/file I/O unaffected. |
| **DONE** | **help** | Dead — the only hard "Requires CP/M Version 3" block is commented out ([help.plm](help/help.plm#L1018)); one live check is purely informational (sets system drive) | none active | **LOW** | none | Works as-is; already has a hardcoded page-length fallback in place of the disabled CP/M-3 path. |
| **DONE** | **pip** | Root cause was **not** the version test itself but the `$set (mpm)` compiler directive at the top of the file, which forced the MP/M build variant (`VERSION`=0x31) so the guard always fired | fn 45 (set BDOS error mode) called ungated at startup; fns 44/48 reachable only from MP/M-gated call sites; fns 109/161 compiled out | **MEDIUM** | B | **Resolved** — see [Resolved: pip](#resolved-pip). |
| **DONE** | **submit** | Hard — strict `cmp bh,11h`/`cmp bh,14h` (MP/M-86 or CCP/M-86 only) (the former `submit/submit.a86`) | Deep use of MP/M-only process-descriptor/console-attach API (fns 143,145,146,147,150,152,153,156,160,164) — no single-tasking equivalent | **HIGH** | C | **Resolved** — the CCP/M-86 source was abandoned as predicted and replaced by a reconstruction of [base/submit.cmd](../base/submit.cmd) from the CP/M 2.2 PL/M source. See [Resolved: submit](#resolved-submit). |
| **DONE** | **tod** | Hard — `tod.plm` requires BDOS≥0x30 and a nonzero OS-type flag ([tod.plm](tod/tod.plm#L433)) | `get$sysdat`/fn 154 (shared MP/M clock structure) doesn't exist here | **LOW** | Replace | Adopt `/Users/thierry/Projects/CPM86/cpm86-hacking/tod.a86` in place of `tod.plm` — it's already CP/M-86-native (checks version ≤0x22, no shared-clock dependency) and confirmed working. Treat `tod.plm` as superseded rather than patched. |
| **DONE** | **stat** | Hard-equivalent — exact-match `if low(ver) <> cpmversion` (0x30) skips all real logic then always reboots ([scom.plm](stat/scom.plm#L1322)) | Unconditional `mon1(46,...)` (get free space) in `getfreesp()` ([scom.plm](stat/scom.plm#L271)) — **confirmed** fn 46 misdispatches to `MWRITZ` (write random with zero fill), a real data hazard, not benign | **MEDIUM** | A/B | **Resolved** — see [Resolved: stat](#resolved-stat). |

## Notes
- The 41–46 dispatch gap is handled by `bdos.a86`'s entry code reusing the 0–40/47–59 table via
  `CL := CL-6`, so each gap function silently misdispatches to a *different, real* handler rather
  than no-op'ing. Confirmed: fn 45 → `NOPROC` (harmless), fn 46 → `MWRITZ` (write random with zero
  fill — hazardous). Any other gap function number (41–44) would need the same per-number check
  before being called from a tool source.
- `tod.plm` was found to have **no fallback path at all** for BDOS<0x30 — its guard-failure branch
  terminates immediately, and its only data-access mechanism (fn 154, shared MP/M clock struct) has
  no in-kernel substitute. That's why it was replaced outright rather than patched (see below).
- General rule applied throughout: prefer importing a proven CP/M-86-native source (as with `tod`)
  over patching a CCP/M-86 source in place, since patching only fixes the guard you can see, not
  hidden CCP/M-only assumptions deeper in the file.

## Resolved: tod
`commands/tod` has been replaced with the CP/M-86-native `tod.a86` implementation (imported from
the sibling `cpm86-hacking` project, MIT-licensed) plus its `baselib.a86`/`tinylib.a86` support code.
The old `tod.plm`/CCP/M-86 source and its `scd.a86` BDOS-wrapper glue were removed entirely, and the
Makefile was updated to build the new source. Verdict: **LOW**, resolved.

## Resolved: pip
`commands/pip` was patched in place (strategy B) rather than replaced. Sequence:

1. **`$set (mpm)` → `$reset (mpm)`.** This was the actual cause of the "REQUIRES CONCURRENT CP/M-86"
   failure — it forced `VERSION = 0031H` instead of `0022H`. Flipping it selects DRI's intended
   single-sector CP/M-86 path (`tdest + 128` rather than multi-sector transfers).
2. **Repaired that path**, which DRI had evidently never compiled: un-gated the pure-logic
   declarations read by ungated code, added the two `$if mpm` guards DRI omitted, and fixed a
   corrupted source line (`call 17,.dest);` → `call xerror(11,.dest);`).
3. **Removed the out-of-range BDOS calls.** `multsect` (fn 44) and the startup `mon1(45,255)` are
   gone, along with `flushbuf` (fn 48 — implemented by the kernel, but dead code here). PIP now
   issues no BDOS call outside the kernel's 0–40/47–59 set.
4. **Removed the MP/M error-return machinery** that fn 45 existed to enable. With error mode
   unavailable the BDOS never returns an extended code, so `exten` was permanently 0, every test on
   `sexten` was constant-false, and `eretry` was written in five places and read in none. All of it
   deleted; `xerror`'s `dcnt`-driven reporting (including the random-record codes 1–6, which *are*
   reachable under CP/M 2.2) is untouched.
5. **Corrected the branding** to match the shipped [base/pip.cmd](../base/pip.cmd) exactly: the version
   stamp, the guard message and the interactive banner now read `(1/8/82) CP/M-86 PIP VERS 1.1`,
   `REQUIRES CP/M-86$` and `CP/M-86 PIP VERSION 1.1$`. The guard itself was kept as a
   minimum-version floor — `low(CVERSION) < 0022H` can never fire here but fails safe elsewhere.

**Verification.** Builds clean; 7936 → 7680 bytes. Runs on real hardware: interactive mode (`*`
prompt, fn 10), single and chained file copies all confirmed. A PL/M-86 `xref` sweep shows no
remaining unreferenced symbols other than documentation literals. `MAXB` buffer sizing confirmed
correct via DDT86 (see kernel facts above) — the CP/M-80-style comment in `scd1.a86` is stale wording,
not a porting bug. No date/timestamp handling anywhere, so no Y2K exposure.

**Lineage.** `pip.plm` was confirmed to be the direct ancestor of the shipped [base/pip.cmd](../base/pip.cmd),
so the CP/M 2.2 PIP is *not* the right starting point here (unlike submit). Three independent checks:
the shipped binary is stamped `(1/8/82)` while `pip.plm`'s revision log records
`18 Dec 81 ... (CP/M-86 1.1)` three weeks earlier; the code segments are 6064 vs 6096 bytes, 0.5%
apart; and the shipped binary contains `INVALID FORMAT WITH SPARCE FILE$`, a string (DRI's typo and
all) that appears five times in `pip.plm` and **nowhere** in the 2.2 source. The remaining 224-byte
data difference is the `special$msg` table — the random-record result codes 1–6, named rather than
numeric — which 3.1 added and which is worth keeping.

`scd1.a86` was left alone: its unused declarations (`bdisk`, the `org 50h` CP/M-3 password fields,
`fcb16`/`cr`/`rr`/`ro`) are pure address reservations that emit no code and describe the base page and
FCB layout. Note that `buff` lands at 80h only by accumulation from `org 5ch` — deleting any of the
intervening reservations without adding an explicit `org 80h` would silently move the command-tail
and DMA buffer. Verdict: **MEDIUM**, resolved.

## Resolved: submit
The CCP/M-86 SUBMIT 1.3 source was abandoned (strategy C) — it contains zero `$$$` references and
spawns commands through fn 150 (`mpm_clicmd`), so it is a structurally different program, not a
port candidate. In its place `commands/submit` now builds a reconstruction of [base/submit.cmd](../base/submit.cmd)
from the CP/M 2.2 PL/M source plus a small CP/M-86 interface module.

**Provenance.** `base/submit.cmd` was disassembled in full and its data segment matched, declaration
for declaration, against DRI's CP/M 2.2 `submit.plm` — `ln(5)` at `0134h`, `dfcb(33)` at `0139h`,
`dcnt` at `015Ah`, `sstring(128)` at `015Bh`, `rbuff(2048)` at `01DDh`, and a byte-identical copyright
string. The CP/M-86 build is that same program recompiled, so the 2.2 source was transformed rather
than rewritten.

**The two modules.**
- `scd.a86` — the entry/exit stub, which is the only part with no 2.2 counterpart. It saves `SS:SP`
  into the code segment, switches the stack to `DS:0130h`, calls `plm`, and on return sets the CCP's
  submit-mode flag `MDSUBE` at `0805h` (see [mapping.md](../mapping.md)) before BDOS fn 0. It
  assembles **byte-identical** to the original's first `0x70` bytes, including the five `nop`s and
  the vestigial `mov cl,al` that computes a drive/user byte for `SUBFCB` and never stores it.
- `submit.plm` — the 2.2 source with four changes: the PL/M-80 module-entry `jmp` trick dropped;
  `buff`/`sfcb` taken as externals instead of `at()` overlays; `submit` renamed `plm: procedure public`;
  and `call boot` removed so the stub performs the exit.

**Three things the binary corrected in the 2.2 source**, each found by diffing our build against it:
1. `error` ends with `call mon1(0,0)` — a direct BDOS reset — not a stack restore. This matters: on
   error there is no usable `$$$.SUB`, so it must reset *without* setting `MDSUBE`, while the normal
   path returns through the stub and *does* set it.
2. `declare oldsp address` survives as a vestigial word at `0130h`, even though the stub now owns the
   stack save.
3. `^X` handling upcases with `- 'A'` (`sub al,41h`), not 2.2's `- 'a'`. Since `getsource` already
   upcases, the 2.2 form would reject every control character — an 86-era bug fix.

**Verification.** Compiles with 0 warnings / 0 errors. The **data segment is byte-exact at 2768
bytes** with every variable at the original's offset, and all 20 procedures are present in the same
order. Confirmed on real hardware: `submit test` read `TEST.SUB`, wrote `$$$.SUB`, and the CCP
consumed and executed the submitted commands.

The code segment is 1020 bytes against the original's 1040. The gap is entirely compiler codegen:
PL/M-86 X304 word-aligns procedure entries (DRI's build placed six at odd addresses) and emits direct
near jumps where the original chained short jumps through a jump island. The instruction streams are
otherwise identical — `sub al,41h`, the `mov ax,0a8ah`/`call error` sequences and the `putrbuff` calls
all match. No source change can close it, so `make check` cannot reach full byte parity; header
geometry and the data segment do match. Verdict: **HIGH**, resolved.

## Resolved: stat

**Lineage.** `commands/stat/` is **MP/M-86 2.0** source, not CP/M-86 3.1 — `stat.plm` carries
`$title ('STATUS - MP/M-86 2.0')` and `scom.plm` opens `/* common stat module for MP/M-80 2.0 and
MP/M-86 2.0 */` with a revision log ending `02 Sept 81 (for MP/M-86)`. Both files are byte-identical
(modulo line endings) to `ossrc/mpm862sr/D8/scom.plm` and `stat86.plm`.

**Why not rebuild from CP/M 2.2 as with submit.** Measured, not assumed: of 42 distinct strings
recovered from the shipped [base/stat.cmd](../base/stat.cmd), **15 appear in both** sources,
**15 appear only in ours**, and **2 only in the 2.2 source**. The only-in-ours strings are the
substance of STAT's output — `Read Only (RO)`, `Read Write (RW)`, `System (Sys)`, `Directory (Dir)`,
`[ro] [rw] [sys] or [dir]`, `Use: STAT`, `32 Byte`, `s / Directory Entry`. The only-in-2.2 strings
are both IOBYTE-related (`Invalid Assignment`, `Iobyte Assign:`). The MP/M-86 source is far closer to
the shipped binary, so 2.2 is a **donor, not a base**. Unlike pip there is no `$set(mpm)` switch to
flip — `scom.plm` has no conditional compilation at all; MP/M-80 vs MP/M-86 commonality was handled
by swapping the `dpb80`/`dpb86` interface module.

**Three defects fixed.**

1. **The build could never link.** `scom.plm` declares `base$dpb`, `dpb$word` and `dpb$byte`
   `external`, but no module provided them — `dpb86.plm` was missing from the extraction. Restored
   from `ossrc/mpm862sr/D8/` and added to the `link86` line.

2. **The data-group minimum was fatally wrong.** The Makefile asked for `m80`, yielding a header with
   `MIN(2048) < LEN(3392)`. `scom.plm` sets `fcbmax literally '512'` and `fcbs literally 'memory'`,
   so STAT builds its 512-entry FCB table in memory *past the end of the data segment*; the loader
   must be told to reserve it. `stat.plm`'s own build comment gives DRI's figure — `m352` paragraphs,
   "enough for 512 directory entries" — now recorded as a named `STATMIN` constant with a comment
   explaining what it covers.

3. **fn 46 — the real data hazard.** `getfreesp()` was `call mon1(46,d)` with `d` a *drive number*.
   Function 46 falls in the 41–46 dispatch gap and lands on `MWRITZ` (write random with zero fill),
   which expects DX to be an *FCB address* — so the call would write to disk through garbage. It is
   replaced by a computation from the allocation vector, using fn 27 (get allocation vector address),
   which is inside the 0–40 set this BDOS implements:

   ```plm
   allocp = mon4(27,0);
   nfree = 0;
   do i = 0 to dpb$word(blkmax$w);   /* a zero bit is a free block */
       if (rol(alloc(shr(i,3)),(i and 111b)+1) and 1) = 0 then
           nfree = nfree + 1;
       end;
   ```

   This is the same idiom CP/M 2.2's own STAT used (`getalloca`/`getalloc`). Note `mon4` — fn 27
   returns an address *in another segment*, so the pointer-returning wrapper is required, not `mon3`.
   `getfreesp` leaves a free **block** count in `buff`; the blocks→records conversion is done by the
   caller, `prcount`, via the existing `call shl3byte(buffa)` — it cannot live in `getfreesp` itself
   because `shl3byte` is defined later in the file and PL/M forbids the forward reference. `d` is now
   unreferenced: fn 27 and the DPB both describe the *currently selected* drive, which the caller has
   already selected through `select$disk` → `set$kpb` → `base$dpb`.

4. **The version guard, relaxed last.** `cpmversion literally '30h'` with an exact-match
   `if low(ver) <> cpmversion` made the entire program a no-op on this kernel. It is now a floor —
   `'22h'` and `if low(ver) < cpmversion` — the fail-safe form CP/M 2.2's STAT and pip both use.
   **Order matters:** the guard was fixed *after* the fn 46 replacement, because relaxing it first
   would have un-gated the destructive call.

**Verification.** Compiles 0 errors; the 2 remaining warnings are pre-existing narrowing warnings
(`d = v / prec`) in the untouched decimal-print routines. A full audit of every BDOS call in
`scom.plm`, `stat.plm` and `dpb86.plm` now resolves to fns 0, 1, 2, 11, 12, 14, 15, 17, 18, 24–32 and
35 — all within the implemented 0–40 range, with nothing left in the 41–46 gap. Header geometry:

| | CODE | DATA MIN | DATA LEN |
|---|---|---|---|
| ours | 4896 | 13600 | 3408 |
| shipped | 5760 | 13568 | 3456 |

`MIN` now exceeds `LEN` as it must, and lands within two paragraphs of the shipped figure. Verdict:
**MEDIUM**, resolved. Runtime comparison of `Bytes Remaining On` against the shipped
[base/stat.cmd](../base/stat.cmd) is checkable arithmetic and remains the outstanding on-target test.

