# CP/M-86 Kernel and Base Tools

## Synopsis

The goal of this project is to provide an out-of-the-box CP/M-86 1.1 kernel (BIOS, BDOS and CCP) that incorporates all existing patches plus the capacity to run on modern hardware and virtualization. A distribution of the CP/M-86 OS is also provided fully patched.

The distribution also packages digital research assembler tools and various basic environments.

- visual y2k support and tod replacement (https://github.com/tsupplis/cpm86-hacking). The code is available in this project.
- AT support
- resilience to bios limits for video display

This is a raw dump right now with a way to compile the kernel starting from dissassembled sources.
The compilation requires the (cross-development environment for CP/M-86)[https://github.com/tsupplis/cpm86-crossdev]

The CP/M-86 kernels (8088 and V20 Mixed 8080/8088 with CP/M-80 compatibility) for the V20 MBC are also produced. The sources of the bioses used are available at:
- https://hackaday.io/project/170924-v20-mbc-a-v20-8088-8080-cpu-homebrew-computer

The 3 kernels use the same BDOS and CCP components.

## Playing with CP/M-86

To test, the PCE emulator and cpmtools are needed. PCE can be found at http://www.hampa.ch/pce/. the floppy images released also work with qemu.

Alternatively, you can use the excellent V20 MBC available at:
- https://hackaday.io/project/170924-v20-mbc-a-v20-8088-8080-cpu-homebrew-computer
- https://shop.mcjohn.it/en/diy-kit

<p align="center">
<img src="./images/v20mbc.png" width="75%">
</p>

- Patched CP/M-86 running in the PCE Emulator
<p align="center">
<img src="./images/cpm86.png" width="75%">
</p>

- CP/M-86 BIOS Setup 1.2
<p align="center">
<img src="./images/setup.png" width="75%">
</p>

- CP/M-86 Disk Maintenance 1.2
<p align="center">
<img src="./images/dskmaint.png" width="75%">
</p>

## Distributions

The repository holds three separate bodies of work:

| | What | Where |
| --- | --- | --- |
| 1 | Three parallel source sets of the PC CP/M-86 1.1 kernel | repository root |
| 2 | The original tool binaries, patched and updated | `base/`, `dev/`, `extra/` |
| 3 | Reconstruction of the tools from source | `commands/` |

### 1. Kernel source sets

The kernel was recovered by disassembly, so the sources are kept in three
parallel sets that can be diffed and rebuilt against each other. `ccp` and
`bdos` are shared by all PC and V20 kernels; only the BIOS differs.

| Set | Sources | Kernel | Intent |
| --- | --- | --- | --- |
| `*org.*` | `ccporg.a86` `bdosorg.a86` `pcbioorg.a86` | `cpmorg.sys` | Original patched release. Frozen reference, never edited. |
| `*.*` | `ccp.a86` `bdos.a86` `pcbios.a86` | `cpm.sys` | Byte-identical to `*org.*`; labelling, commenting and documentation in progress. |
| `*exp.*` | `ccpexp.a86` `bdosexp.a86` `pcbioexp.a86` | `cpmexp.sys` | Experimental cleaned-up and optimised variant. |

`make check` asserts that `cpm.sys` and `cpmorg.sys` are binary-identical, so
the annotation work cannot silently change behaviour.

Two further BIOSes target the V20 MBC:

| Kernel | Target |
| --- | --- |
| `cpmv20.sys` | MBC V20, 8088 mode (`mbcv20.a86`) |
| `cpm816.sys` | MBC V20, mixed 8080/8088 mode with CP/M-80 compatibility (`mbc816.a86`) |

### Disk images

Four sets are produced. The 160K set is the reference layout; the others repack
the same material to fit the media, except the experimental set which swaps in
the `commands/` reconstruction.

**160K single sided — 4 disks**

| Image | Contents |
| --- | --- |
| `cpm86-160-1.img` | Bootable core CP/M-86 |
| `cpm86-160-1-at.img` | Bootable core, AT-compatible clock |
| `cpm86-160-2.img` | Assembler CP/M-86 tools |
| `cpm86-160-3.img` | Digital Research dev tools |
| `cpm86-160-4.img` | BASIC development |

**320K double sided — 3 disks**

| Image | Contents |
| --- | --- |
| `cpm86-320.img` | Bootable core + assembler tools |
| `cpm86-320-at.img` | Bootable core + assembler tools, AT-compatible clock |
| `cpm86-320-dev.img` | Digital Research dev tools + BASIC development |

**1.44M high density — 1 disk**

| Image | Contents |
| --- | --- |
| `cpm86-1440-at.img` | Everything above, AT-compatible clock (uses 144FEAT2 from Freek Heite) |

**Experimental — 2 disks**

| Image | Contents |
| --- | --- |
| `cpm86-exp-160-1.img` | Experimental kernel with the `commands/` reconstruction in place of `base/` |
| `cpm86-exp-160-1-at.img` | Same, AT-compatible clock |

The experimental images boot `cpmexp.sys` and carry the rebuilt `ed`, `help`,
`pip`, `stat`, `submit` and `tod` rather than the `base/` binaries, so a single
boot exercises both halves of the reconstruction. `make test-exp` runs the
`cpm86-exp-160-1-at.img` set under PCE.

Images built from the blank image carry a boot loader terminating with `55AA`,
which lets qemu load CP/M-86 properly. Beware: formatting with `dskmaint.cmd`
does not add the signature.

### 2. Tool binaries

`base/` holds the CP/M-86 command set. Some tools ship untouched, others are
patched or replaced.

| State | Tools |
| --- | --- |
| Original | `asm86` `assign` `config` `ddt86` `function` `gencmd` `help` `print` `stat` |
| Updated release | `dskmaint` (1.0 → 1.2), `setup` (1.0 → 1.2), `hdmaint` (1.0 → 1.1), `help.hlp` (fuller content) |
| Patched per DR recommendation | `ed` `gendef` `pip` `submit` |
| Locally patched | `mform` (interactive prompt removed) |
| Added | `atinit` (RTC sync), from [cpm86-hacking](https://github.com/tsupplis/cpm86-hacking) |

`tod` is deliberately absent from `base/`: the original is superseded by the
CP/M-86-native rewrite, so every image takes it from `commands/tod`.

`extra/` holds the 1.44M support utilities. `dev/` holds the Digital Research
and Microsoft toolchains, as shipped and unmodified:

| Tool | Product | Version | Date | Vendor |
| --- | --- | --- | --- | --- |
| `rasm86.cmd` | RASM-86 Relocating Assembler | 1.2 | 1982-1983 | Digital Research |
| `link86.cmd` | LINK86 Linkage Editor | 2.02 | 02/Feb/87 | Digital Research |
| `lib86.cmd` | LIB-86 Library Manager (CDOS 86) | 1.3 | 2/23/86 | Digital Research |
| `xref86.cmd` | XREF-86 Cross Reference | 1.1 | 1982-1983 | Digital Research |
| `sid86.cmd` | SID-86 with 286 Disassembler | 2.4 | 07 May 1985 | Digital Research |
| `cbas86.cmd` | CBAS86 CBASIC Compiler | 1.4 | 1981-1983 | Digital Research |
| `crun86.cmd` | CRUN86 CBASIC Runtime | 1.4 | 1981-1983 | Digital Research |
| `pbasic.cmd` | Personal BASIC | 1.2 | 1983-1985 | Digital Research |
| `mbasic86.cmd` | BASIC-86 (CP/M-86 patched) | Rev. 5.22 | 5-Mar-82 | Microsoft |

### 3. Tool reconstruction from source

`commands/` rebuilds the tools from the surviving PL/M and ASM86 sources. Those
sources are Concurrent CP/M-86 3.1 vintage and assume BDOS 3.x, while this
kernel reports BDOS 2.2 with `BH=0`. Each tool was therefore audited for version
guards and for calls into BDOS functions this kernel does not implement.

| Tool | Outcome |
| --- | --- |
| `asm86` `gencmd` | CCP/M-86 3.1 sources. Compatible with CP/M-86 |
| `ddt86` `ed` `help` | CCP/M-86 3.1 sources. Compatible with CP/M-86 |
| `pip` | Reconstructed from CCP/M-86 3.1 sources |
| `stat` | Reconstructed from CP/M-80 2.2 sources |
| `submit` | Reconstructed from CP/M-80 2.2 sources |
| `tod` | Superseded by the CP/M-86-native rewrite; the only tool with no `base/` binary |

`make commands` builds the whole set. The root build depends on it, since `tod`
is needed by every image and the rest by the experimental ones.

## cpmtools formats 

cpmtools 2.23 with libdsk is used.

cpmtools can be deployed with homebrew on mac of fetched at https://www.moria.de/~michael/cpmtools/.

the definitions used are:

```
# IBM CP/M-86
# setfdprm /dev/fd1 sect=8 dtr=1 hd ssize=512 tpi=48 head=1
diskdef ibmpc-514ss
   seclen 512
   tracks 40
   sectrk 8
   blocksize 1024
   maxdir 64
   skew 1
   boottrk 1
   os 2.2
   libdsk:format ibm160
end

# CP/M 86 on 1.44MB floppies
diskdef cpm86-144feat
  seclen 512
  tracks 160
  sectrk 18
  blocksize 4096
  maxdir 256
  skew 1
  boottrk 2
  os 3
  libdsk:format ibm1440
end
```

and, for 320K double sided disks, this project's own definition from the
`diskdefs` file at the root of the repository (see below):

```
diskdef cpm86-320
  seclen 512
  tracks 80
  sectrk 8
  blocksize 2048
  maxdir 64
  skew 1
  boottrk 1
  os 2.2
end
```

### The 320K format (solved)

The stock `ibmpc-514ds` definition shipped with cpmtools corrupts 320K raw
images. The cause is in the BIOS, not in cpmtools.

`SETUP_INTREG` in `pcbios.a86` maps a CP/M track to a physical cylinder/head
like this:

```asm
mov	ch,al        ; cylinder = CP/M track
cmp	ch,28h       ; below 40 ?
jb	SETUP_INTREG_FIN
mov	ch,4Fh       ; 79
sub	ch,al        ; cylinder = 79 - track
mov	dh,01h       ; head 1
```

So CP/M tracks 0-39 are cylinders 0-39 on head 0, and CP/M tracks 40-79 are
cylinders **39 down to 0** on head 1. Side 1 is laid down in reverse cylinder
order. A raw image is a plain CHS dump (cyl0/h0, cyl0/h1, cyl1/h0, ...), so the
CP/M track order and the image order do not match. cpmtools has no diskdef
syntax to express that, and `ibmpc-514ds` assumes a linear layout.

`ibmpc-514ds` also disagrees with the BIOS disk parameter block `DPBK2`
(SPT=32, BSH=4/BLM=15/EXM=1, DSM=157, DRM=63, **OFF=1**): `boottrk 2` on a
linear image yields 156 blocks instead of 158.

The reason the corruption looks so odd is that the directory survives. With
OFF=1 the directory is block 0 at CP/M track 1, which is cylinder 1 head 0, at
byte 8192 of the image. `ibmpc-514ds` with `boottrk 2` also lands on byte 8192.
Block 1 coincides too. Everything from block 2 onward does not, so `cpmls`
prints a perfect directory while every file reads back as garbage.

The 160K format is unaffected because it is single sided, so the reverse-order
branch never runs.

The fix is a corrected definition in the `diskdefs` file at the root of this
repository (cpmtools reads `./diskdefs` before the system-wide one, so run the
`cpm*` tools from the repo root), plus `tools/cpm86twist.py` to convert between
physical CHS order and CP/M logical track order:

```
python3 tools/cpm86twist.py untwist disk.img work.img
cpmcp -f cpm86-320 work.img base/pip.cmd 0:PIP.CMD
python3 tools/cpm86twist.py twist work.img disk.img
```

The `Makefile` targets for `cpm86-320.img`, `cpm86-320-at.img` and
`cpm86-320-dev.img` do this automatically.

## Pedigree

The main source for it is: http://www.cpm.z80.de

- Baseline: http://www.cpm.z80.de/download/cpm86src.zip
- Baseline: http://www.cpm.z80.de/download/cpmdev.zip
- Patching Source: http://www.cpm.z80.de/download/cpm86ann.zip
- Patching Source: http://www.cpm.z80.de/download/cpm86bug.zip
- 144FEAT2 from Freek Heite

To be continued...
