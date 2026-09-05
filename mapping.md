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
| `0000h` | CCP image | `ccpnew.a86` | Loaded separately; label `CCP` defined here in `pcbionew.a86` for WBOOT jump |
| `0000h` | TOP | `ccpnew.a86` | Jump table: `CCPCLD` / `CCPABE` / `CCPHOT` |
| `0009h` | CMBUFF | `ccpnew.a86` | 127-byte command input buffer |
| `~0050h` | CCP code body | `ccpnew.a86` | Parser, built-in commands |
| `0800h` | CCP data (DSEG) | `ccpnew.a86` | Variables, FCBs, stack, tables |
| `00DAh` | CCP helper | `ccpnew.a86` | `SUBMITSELDRV`, falls through to `SELDRV` |
| `051Fh` | CCP inline code | `ccpnew.a86` | `DIRPAT` (TS patch), falls through to `DIROUP` |
| `09C0h` | CCP patch area | `ccpnew.a86` | Reserved for future patches |
| `0A00h` | BDOS patch area | `bdosnew.a86` | `PATCH13`, packed `MLOADQ`/`MLOADK`, `BDOSBC`, `PATCH15` (`0A00h`–`0A7Fh`) |
| `0A80h` | IXMAIN | `bdosnew.a86` | BDOS function dispatch table |
| `0B00h` | BDOS image | `bdosnew.a86` | User ID bytes + official BDOS entry |
| `0B06h` | BDOSEN | `bdosnew.a86` | Interrupt handler / BDOS dispatcher |
| `~0B20h` | BDOS code body | `bdosnew.a86` | All 60 BDOS functions |
| `2200h` | BDOS data (DSEG) | `bdosnew.a86` | Variables, buffers, system stack |
| `24FFh` | End of BDOS | `bdosnew.a86` | — |
| `2500h` | BIOS jump vector | `pcbionew.a86` | 20 × JMP + config data + copyright |
| `~2560h` | BIOS code body | `pcbionew.a86` | Char I/O, disk I/O, interrupts |
| `????h` | BIOS data (DSEG) | `pcbionew.a86` | I/O vectors, drive tables, DPHs, disk parameters, stacks, buffers (`data_offset`) |
| `????h` | INIT / once-only | `pcbionew.a86` | Cold-start code + data overlaid on the disk sector buffer; freed after first boot (CSEG + DSEG at DSKBUF) (`DSKBUF` / `data_offst2`) |
| `4980h` | HDDBUF | `pcbionew.a86` | HDD sector buffer (512 bytes) |
| `4BE2h` | DIRBUF | `pcbionew.a86` | Directory scratch buffer (128 bytes) |
| `4C62h` | CSV14+ | `pcbionew.a86` | Allocation vectors, grow upward |

---

## ccpnew.a86 — ORG / segment detail

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
0803h  DDMASG     base-page segment
0805h  MDSUBE     submit mode flag       ← referenced by BDOS as MDSUBE EQU 0805h
0806h  SUBFCB     submit file FCB (36 bytes)
082Ah  WKFCB      work FCB (36 bytes)
084Eh  RWBUFF     128-byte sector read buffer + 2 spare bytes
08D0h  BSDIRC     directory bias
08D1h  USRCOD     user code
08D2h  TRCMOD     transient command mode
        RS 96
0935h  STACK      CCP system stack
0936h  WKBIOS     BIOS direct-call work block (9 bytes)
093Fh  PNTCMD     command buffer pointer
0941h  TPNCMD     temporary command buffer pointer
0943h  CURDRV     current drive
0944h  TDRVNU     temporary drive mode
        indexed data, error strings, user-ID bytes …
        MODIRE, MODDIR
        IXRSRT     resident command routine index
```

---

## bdosnew.a86 — ORG / segment detail

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
         WKFCB (36B) + RS 164
         STACK                         BDOS system stack
         INSTSG/INSTOF/FLINSD          entry stack save
         INPARA/OTPARA/INDSEG          call parameters
         DMAADD/DMASEG/CURDSK …       system data area
         CONWID/PRNWID/CONCOL/PRNCOL  console/printer widths
```

---

## pcbionew.a86 — ORG / segment detail

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
| `24A5h` | `BDOSUSER` | Current user number |
| `24AFh` | `BDOSMODABT` | BDOS abort mode flag |
| `24B7h` | `BDOSCURDRV` | Current default drive |
| `24BDh` | `DHOUR` … `BDOSCONWID` | Clock, ASCII time, system message buffer |

### BIOS load-segment ORGs (CSEG / DSEG, load segment)

| ORG value | Segment | First symbol | Description |
|-----------|---------|--------------|-------------|
| `0000h` (CCP_OFFSET) | CSEG | `CCP` | Label-only forward ref; no code emitted |
| `2500h` (BIOS_CODE) | CSEG | *(jmp INIT)* | BIOS jump vector + code start |
| `data_offset` ($) | DSEG | `BIOS_DATA_RSV` | Main BIOS data area, contiguous with code |
| `DSKBUF` ($) | CSEG | `INIT` | Once-only cold-start code, overlays disk buffer |
| `data_offst2` ($) | DSEG | `SIGNON` | INIT data area, also overlays disk buffer |
| `4980h` | DSEG | `HDDBUF` | HDD sector buffer (512 bytes, fixed address) |
| `4BE2h` | DSEG | `DIRBUF` | Directory scratch buffer (128 bytes) |
| `4C62h` | DSEG | `CSV14` | Allocation vector for drive 4 (grows upward) |

---

## Gap analysis — free bytes between ORG slots

*All addresses and sizes verified from the `.lst` assembler listing files.*
*All free holes confirmed unused — no jump targets, data pointers, or references land in any gap.*

### ccpnew.a86 — code and data boundaries

| Region | Start | Last byte | Next ORG | Slot (dec) | Used (dec) | Free (dec) | Hole range | Last symbol |
|--------|-------|-----------|----------|------------|------------|------------|------------|-------------|
| CCP code (CSEG) | `0000h` | `07DAh` | `0800h` | 2048 | 2010 | 37 | `07DBh`–`07FFh` | `CMDPTR` DW 0,0 @ `07D7h` |
| CCP data (DSEG) | `0800h` | `09B9h` | `09C0h` | 448 | 442 | 6 | `09BAh`–`09BFh` | `MODDIR` DB @ `09B9h` |

### Packed patch areas — `09C0h`–`0A7Fh`

`SUBMITSELDRV` is part of the main CCP code at `00DAh` and falls through to `SELDRV`.
`DIRPAT` is inlined in the main CCP code at `051Fh` and falls through to `DIROUP`. The upper CCP patch area begins at `09C0h` and is currently free through `09FFh`.
The BDOS patch area begins at `0A00h` and ends before `IXMAIN` at `0A80h`.

| Slot | File | Start | Last byte | Next ORG | Avail (dec) | Used (dec) | Free (dec) | Hole range |
|------|------|-------|-----------|----------|-------------|------------|------------|------------|
| `CCP patch area` | ccpnew | `09C0h` | `09FFh` | `0A00h` | 64 | 0 | 64 | `09C0h`–`09FFh` |
| `PATCH13` | bdosnew | `0A00h` | `0A1Fh` | `0A20h` | 32 | 32 | 0 | — ⚠ full |
| `MLOADQ + MLOADK + BDOSBC` | bdosnew | `0A20h` | `0A3Fh` | `0A40h` | 32 | 32 | 0 | — |
| `PATCH15` | bdosnew | `0A40h` | `0A53h` | `0A80h` | 64 | 20 | 44 | `0A54h`–`0A7Fh` |
| `IXMAIN`+stubs | bdosnew | `0A80h` | `0AF6h` | `0B00h` | 128 | 119 | 9 | `0AF7h`–`0AFFh` |

Notes:
- **`SUBMITSELDRV`** is a 3-byte helper at `00DAh` that falls through to `SELDRV` at `00DDh`; its two callers resolve to `00DAh`.
- **`DIRPAT`** is now inlined at `051Fh`–`0526h` and falls through to `DIROUP`; its former separate jump and upper-code placement are gone.
- The upper CCP patch area begins at `09C0h` and currently has 64 bytes free through `09FFh`.
- **`PATCH13`** and the packed `MLOADQ`/`MLOADK`/`BDOSBC` block are full. `PATCH15` occupies `0A40h`–`0A53h`, leaving 44 bytes free at `0A54h`–`0A7Fh`.
- **`IXMAIN`** contains 54 DW dispatch entries (`0A80h`–`0AEBh`, 108 bytes) + `MRTVNO` (5 bytes @ `0AECh`) + `MGTSAD` (6 bytes @ `0AF1h`) = 119 bytes used.
- All free holes verified against both `.lst` files — **no code, data, or references land in any hole.**

### pcbionew.a86 — fixed-address buffer gaps

| Symbol | Start | End+1 | Next ORG | Gap (dec) | Gap (hex) | Hole range | Notes |
|--------|-------|-------|----------|-----------|-----------|------------|-------|
| `CFG_PFKTBL` | `47F0h` | `4980h` | `4980h` | 0 | — | — | RS 400, ends exactly at `HDDBUF` |
| `HDDBUF` | `4980h` | `4B80h` | `4BE2h` | 98 | `62h` | `4B80h`–`4BE1h` | Reserved padding — original DRI layout |
| `DIRBUF` | `4BE2h` | `4C62h` | `4C62h` | 0 | — | — | RS 128, ends exactly at `CSV14` |

- The **98-byte gap** (`4B80h`–`4BE1h`) is present in the original Digital Research binary, confirmed unreferenced in all `.lst` files, and must not be used.
- `DSKBUF`/`INIT` overlay: INIT code+data spans `3BE2h`–`4062h` (**481 bytes**), placed in the disk-buffer area and reclaimed after first boot.

