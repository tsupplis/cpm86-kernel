# CP/M-86 Memory Map

All of CP/M-86 assembles into **one single load segment** (CS = DS = SS at
runtime).  The three source files are assembled at fixed offsets within that
segment; no relocation takes place.

## Segment model

| Directive | Argument | Runtime segment | Purpose |
|-----------|----------|-----------------|---------|
| `DSEG 0` | `0` | Segment 0000h | Address aliases into the 8086 interrupt vector table (IVT). No data emitted — read/written at runtime with `DS=0`. |
| `DSEG 40H` | `40H` | Segment 0040h | Address alias for the ROM BIOS data area (equipment byte etc.). Accessed at runtime with `ES=0040h`. |
| `DSEG` | *(none)* | CP/M load segment | Re-opens the single load segment so `ORG` can name fixed offsets within it. No data emitted unless `DB`/`DW`/`RS` etc. follow. |
| `CSEG` | *(none)* | CP/M load segment | Code section of the load segment. |

`DSEG` (no argument) and `CSEG` are the **same segment** at runtime; the
distinction is purely an assembler convention for separating code from data.

---

## Load-segment address map

| Offset | Region | File | Notes |
|---|---|---|---|
| `0000h` | CCP image | `ccpexp.a86` | Loaded separately; label `CCP` defined here in `pcbioexp.a86` for WBOOT jump |
| `0000h` | TOP | `ccpexp.a86` | Jump table: `CCPCLD` / `CCPABE` / `CCPHOT` |
| `0009h` | CMBUFF | `ccpexp.a86` | 127-byte command input buffer |
| `008Bh` | CCP code body (`ENBDOS`) | `ccpexp.a86` | Parser, built-in commands |
| `0800h` | CCP data (DSEG) | `ccpexp.a86` | Variables, FCBs, stack, tables |
| `00DAh` | CCP helper | `ccpexp.a86` | `SUBMITSELDRV`, falls through to `SELDRV` |
| `051Fh` | CCP inline code | `ccpexp.a86` | `DIRPAT` (TS patch), falls through to `DIROUP` |
| `09C0h` | CCP patch area | `ccpexp.a86` | Reserved for future patches |
| `0A00h` | BDOS patch area | `bdosexp.a86` | `PATCH13`, packed `MLOADQ`/`MLOADK`, `BDOSBC`, `PATCH15` (used `0A00h`–`0A53h`) |
| `0A80h` | IXMAIN | `bdosexp.a86` | BDOS function dispatch table |
| `0B00h` | BDOS image | `bdosexp.a86` | User ID bytes + official BDOS entry |
| `0B06h` | BDOSEN | `bdosexp.a86` | Interrupt handler / BDOS dispatcher |
| `2200h` | BDOS data (DSEG) | `bdosexp.a86` | Variables, buffers, system stack |
| `24F4h` | End of BDOS data | `bdosexp.a86` | Final `db 0`; `24F5h`–`24FFh` unused |
| `2500h` | BIOS jump vector | `pcbioexp.a86` | 21 × JMP (`2500h`–`253Ch`), `rs 15` reserved, 6 config pointers (`254Eh`–`2559h`), copyright (`255Ah`–`257Dh`) |
| `257Eh` | BIOS code body (`WBOOT`) | `pcbioexp.a86` | Char I/O, disk I/O, interrupts |
| `32C5h` | BIOS data (DSEG) | `pcbioexp.a86` | I/O vectors, drive tables, DPHs, disk parameters, stacks, buffers (`data_offset` / `BIOS_DATA_RSV`) |
| `3BE2h` | INIT / once-only | `pcbioexp.a86` | Cold-start code (`3BE2h`–`4062h`) overlaid on the disk sector buffer; freed after first boot (`DSKBUF` / `data_offst2`) |
| `4980h` | HDDBUF | `pcbioexp.a86` | HDD sector buffer (512 bytes) |
| `4BE2h` | DIRBUF | `pcbioexp.a86` | Directory scratch buffer (128 bytes) |
| `4C62h` | CSV14+ | `pcbioexp.a86` | Allocation vectors, grow upward |

---

## ccpexp.a86 — ORG / segment detail

| ORG value | Segment | First symbol | Description |
|-----------|---------|--------------|-------------|
| `0000h` | CSEG | `TOP` | CCP jump table (cold / abort / hot start) |
| `0800h` | DSEG | `CODCMD` | CCP data area: variables, FCBs, stack, tables |
| `00DAh` | CSEG | `SUBMITSELDRV` | CCP helper; falls through directly to `SELDRV` at `00DDh` |
| `051Fh` | CSEG | `DIRPAT` | Inline CCP TS patch before `DIROUP` |
| `09C0h` | CSEG | — | Reserved upper CCP patch area |

### CCP data area layout (DSEG, from 0800h)

```
0800h  CODCMD     'CMD' transient-type tag (3 bytes)
0803h  DDMASG     base-page segment (dw)
0805h  MDSUBE     submit mode flag       ← referenced by BDOS as MDSUBE EQU 0805h
0806h  SUBFCB     submit file FCB (1 byte, then SUBNAM)
0807h  SUBNAM     '$$$     SUB' + 4 zero bytes
0816h  (zero fill, to 0827h)
0827h  WKFCB      work FCB (36 bytes, to 084Ah)
084Bh  RWBUFF     one-sector read buffer (128 bytes, to 08CAh)
08CBh  (2 bytes, unused)
08CDh  BSDIRC     bias of directory
08CEh  USRCOD     user code
08CFh  TRCMOD     transient command mode
08D0h  (rs 96, to 092Fh)
0930h  STACK      CCP system stack; WKBIOS at 0930h (9 = select disk, then dw 0, dw 1)
0935h  PNTCMD     command buffer pointer (dw)
0937h  TPNCMD     temporary command buffer pointer (dw)
0939h  CURDRV     current drive
093Ah  TDRVNU     temporary drive mode
093Bh  IXTERM     index label (used by the CCP dispatch code)
...    indexed data, error strings, user-ID bytes
09AAh  IXRSRT    resident command routine index
09B8h  MODIRE    other-side file exist mode
09B9h  MODDIR    directory mode (0 non-system, 1 system file)
```


---

## bdosexp.a86 — ORG / segment detail

| ORG value | Segment | First symbol | Description |
|-----------|---------|--------------|-------------|
| `0000h` | CSEG | `TOP` | Dummy anchor at segment base (never executed) |
| `0A00h` | CSEG | `PATCH13` | TS patch 13 — BDOS internal call fix |
| `0A20h` | CSEG | `MLOADQ` | Load-program error exit stub |
| `0A2Fh` | CSEG | `MLOADK` | Load-program OK exit stub, sequential after `MLOADQ` |
| `0A34h` | CSEG | `BDOSBC` | Function-code range check helper, sequential after `MLOADK` |
| `0A40h` | CSEG | `PATCH15` | TS patch 15 — data-group base fix, packed after `BDOSBC` |
| `0A80h` | CSEG | `IXMAIN` | BDOS function dispatch table (54 × DW = 6Ch bytes) + MRTVNO + MGTSAD |
| `0B00h` | CSEG | `BDOSEN` | Official BDOS entry point (user ID bytes + interrupt handler) |
| `2200h` | DSEG | `JPBIOS` | BDOS data area (variables, buffers, system stack) |

### BDOS data area layout (DSEG, from 2200h)

```
2200h  JPBIOS / SGBIOS    BIOS call routine vector
2204h  VBADSC … VROFIL    error routine vectors (4 × DW)
220Ch  BFGRDC             group descriptor buffer (36 words = 48h bytes)
         BFLDPR           program loading buffer (128 bytes)
         DGBASE           data group base
         MODE80           8080 model flag
         SYSMCB           memory control block work (5 bytes)
         UFCBOF/LPSTOF/LPSTSG/FMODEL
         ECHKIL/PPROMP/PCARIG/BFCONC   console I/O work
         DLTFCB/RODSKV/LGDSKV          disk I/O work
         PNDRCK/PNTRAK/PNSCTR          disk parameter work
         DIRBUF/PNTDPB/PNCHSM/PNALMP  DPH copy
         SPT … PNXTBL                  DPB copy
         EXTMOD … FLOMOD               disk work parameters
         CNTREG/SIZREG/TBLREG (64B)    memory region table
         TBUMCB (40B)                  used MCB buffer
         CNUMCB/PNUMCB/SYSMOD …       MCB management
         CERROR … CRODSK               error message strings
         WKFCB (36B) at 23C6h          working FCB or mcb (`org 23C6h`)
         STACK                         BDOS system stack
         INSTSG/INSTOF/FLINSD          entry stack save
         INPARA/OTPARA/INDSEG          call parameters
         DMAADD/DMASEG/CURDSK …       system data area
         CONWID/PRNWID/CONCOL/PRNCOL  console/printer widths (24E0h–24E3h)
         rs 16, final db 0 at 24F4h
```

### BDOS error-message area

| Symbol | Start | End | Size | Contents |
|--------|-------|-----|------|----------|
| `CERROR`–`CRODSK` | `239Bh` | `23BAh` | 32 bytes | Compact BDOS error text: `E/`, drive marker, `BADSECTOR`, `SELECT`, `FILE`, and `R/O` |

---

## pcbioexp.a86 — ORG / segment detail

### Interrupt vector table aliases (DSEG 0, segment 0000h)

| ORG expression | = byte offset | Symbols defined |
|----------------|---------------|-----------------|
| `ORG 0` | `0000h` | `ZEROOFF` / `ZEROSEG` — INT 0 (divide-by-zero) |
| `4*01BH` | `006Ch` | `BREAKOFF` / `BREAKSEG` — INT 1Bh (Ctrl-Break) |
| *(sequential)* | `0070h` | `TIMEROFF` / `TIMERSEG` — INT 1Ch (timer tick) |
| `4*01EH` | `0078h` | `I1EOFF` / `I1ESEG` — INT 1Eh (diskette parameters) |
| `4*0E0H` | `0380h` | `BDOSOFF` / `BDOSSEG` — INT E0h (BDOS entry) |
| `4*0E6H` | `0398h` | `UNDSKOFF` / `UNDSKSEG` — INT E6h (unknown disk) |

### ROM BIOS data area alias (DSEG 40H, segment 0040h)

| ORG value | Symbol | Description |
|-----------|--------|-------------|
| `10H` | `BIOSHDW` | Equipment byte (video mode bits 5–4) |

### BDOS internal variable aliases (DSEG, load segment)

| ORG value | Symbol | Description |
|-----------|--------|-------------|
| `24A5h` | `USRCOD` | Current user number |
| `24AFh` | `MODABT` | BDOS abort mode flag |
| `24B7h` | `CURDRV` | Current default drive |
| `24BDh` | `DHOUR` / `DMINUTE` / `DSECOND` | Clock block (hours, minutes, seconds) |
| `24E0h` | `CONWID` … `PRNCOL` | Console/printer widths and cursor positions (`24E0h`–`24E3h`) |

### BIOS load-segment ORGs (CSEG / DSEG, load segment)

| ORG value | Segment | First symbol | Description |
|-----------|---------|--------------|-------------|
| `0000h` (CCP_OFFSET) | CSEG | `CCP` | Label-only forward ref; no code emitted |
| `2500h` (BIOS_CODE) | CSEG | `INIT` jmp (`2500h`) | BIOS jump vector; code body starts at `WBOOT` `257Eh` |
| `32C5h` (data_offset) | DSEG | `BIOS_DATA_RSV` | Main BIOS data area, contiguous with code (`rs 75` reserved first) |
| `3BE2h` (DSKBUF) | CSEG | `INIT` | Once-only cold-start code, overlays disk buffer |
| `4063h` (data_offst2) | DSEG | `SIGNON` | INIT data area, also overlays disk buffer |
| `4980h` | DSEG | `HDDBUF` | HDD sector buffer (512 bytes, fixed address) |
| `4BE2h` | DSEG | `DIRBUF` | Directory scratch buffer (128 bytes) |
| `4C62h` | DSEG | `CSV14` | Allocation vector for drive 4 (grows upward) |

---

## Gap analysis — free bytes between ORG slots

*All addresses and sizes verified from the `.lst` assembler listing files.*
*All free holes confirmed unused — no jump targets, data pointers, or references land in any gap.*

### ccpexp.a86 — code and data boundaries

| Region | Start | Last byte | Next ORG | Slot (dec) | Used (dec) | Free (dec) | Hole range | Last symbol |
|--------|-------|-----------|----------|------------|------------|------------|------------|-------------|
| CCP code (CSEG) | `0000h` | `07DAh` | `0800h` | 2048 | 2010 | 37 | `07DBh`–`07FFh` | `CMDPTR` DW 0,0 @ `07D7h` |
| CCP data (DSEG) | `0800h` | `09B9h` | `09C0h` | 448 | 442 | 6 | `09BAh`–`09BFh` | `MODDIR` DB @ `09B9h` |

### bdosexp.a86 — code and data boundaries

| Region | Start | Last byte | Next ORG | Slot (dec) | Used (dec) | Free (dec) | Hole range | Last symbol |
|--------|-------|-----------|----------|------------|------------|------------|------------|-------------|
| BDOS code (CSEG) | `0B00h` | `21F8h` | `2200h` | 5888 | 5881 | 7 | `21F9h`–`21FFh` | `MFLUSH` `RET` @ `21F8h` |
| BDOS data (DSEG) | `2200h` | `24F4h` | `2500h` | 768 | 757 | 11 | `24F5h`–`24FFh` | final `DB 0` @ `24F4h` |
| BDOS data hole (before `WKFCB`) | `23BBh` | `23C5h` | `23C6h` | 11 | 0 | 11 | `23BBh`–`23C5h` | `CRODSK` `R/O$` @ `23B7h` |

### Packed patch areas — `09C0h`–`0A7Fh`

`SUBMITSELDRV` is part of the main CCP code at `00DAh` and falls through to `SELDRV`.
`DIRPAT` is inlined in the main CCP code at `051Fh` and falls through to `DIROUP`. The upper CCP patch area begins at `09C0h` and is currently free through `09FFh`.
The BDOS patch area begins at `0A00h` and ends before `IXMAIN` at `0A80h`.

| Slot | File | Start | Last byte | Next ORG | Avail (dec) | Used (dec) | Free (dec) | Hole range |
|------|------|-------|-----------|----------|-------------|------------|------------|------------|
| `CCP patch area` | ccpexp | `09C0h` | `09FFh` | `0A00h` | 64 | 0 | 64 | `09C0h`–`09FFh` |
| `PATCH13` | bdosexp | `0A00h` | `0A1Fh` | `0A20h` | 32 | 32 | 0 | — ⚠ full |
| `MLOADQ + MLOADK + BDOSBC` | bdosexp | `0A20h` | `0A3Fh` | `0A40h` | 32 | 32 | 0 | — |
| `PATCH15` | bdosexp | `0A40h` | `0A53h` | `0A80h` | 64 | 20 | 44 | `0A54h`–`0A7Fh` |
| `IXMAIN`+stubs | bdosexp | `0A80h` | `0AF6h` | `0B00h` | 128 | 119 | 9 | `0AF7h`–`0AFFh` |

Notes:
- **`SUBMITSELDRV`** is a 3-byte helper at `00DAh` that falls through to `SELDRV` at `00DDh`; its two callers resolve to `00DAh`.
- **`DIRPAT`** is inlined at `051Fh`–`0527h` and falls through to `DIROUP` at `0528h`.
- The upper CCP patch area begins at `09C0h` and currently has 64 bytes free through `09FFh`.
- **`PATCH13`** and the packed `MLOADQ`/`MLOADK`/`BDOSBC` block are full. `PATCH15` occupies `0A40h`–`0A53h`, leaving 44 bytes free at `0A54h`–`0A7Fh`.
- **`IXMAIN`** contains 54 DW dispatch entries (`0A80h`–`0AEBh`, 108 bytes) + `MRTVNO` (5 bytes @ `0AECh`) + `MGTSAD` (6 bytes @ `0AF1h`) = 119 bytes used.
- All free holes verified against both `.lst` files — **no code, data, or references land in any hole.**

### pcbioexp.a86 — fixed-address buffer gaps

| Symbol | Start | End+1 | Next ORG | Gap (dec) | Gap (hex) | Hole range | Notes |
|--------|-------|-------|----------|-----------|-----------|------------|-------|
| `CFGPFKTBL` | `47F0h` | `4980h` | `4980h` | 0 | — | — | RS 400, ends exactly at `HDDBUF` |
| `HDDBUF` | `4980h` | `4B80h` | `4BE2h` | 98 | `62h` | `4B80h`–`4BE1h` | Reserved padding — original DRI layout |
| `DIRBUF` | `4BE2h` | `4C62h` | `4C62h` | 0 | — | — | RS 128, ends exactly at `CSV14` |

- The **98-byte gap** (`4B80h`–`4BE1h`) is present in the original Digital Research binary, confirmed unreferenced in all `.lst` files, and must not be used.
- `DSKBUF`/`INIT` overlay: INIT code+data spans `3BE2h`–`4062h` (**1153 bytes**, `481h`), placed in the disk-buffer area and reclaimed after first boot.

