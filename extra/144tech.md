## The 1.44 MB Feature for CP/M-86

This software makes "CP/M-86 for the IBM PC and IBM PC XT  Version 1.1"
support diskettes with much higher capacities than the old, standard CP/M-86
160 KB and 320 KB formats. Now, you can store:

- up to 710 KB of data on a 3.5 inch, 720 KB diskette
- up to 1.18 MB of data on a 5.25 inch, 1.2 MB diskette
- up to 1.42 MB of data on a 3.5 inch, 1.44 MB diskette.


## Technical notes

Contents:

1. Layout of the higher-capacity diskettes
2. Boot sector details
3. CP/M-86 1.44 MB diskette
4. CP/M-86 720 KB diskette
5. CP/M-86 1.2 MB diskette
6. "Personal CP/M-86 Plus" 720 KB diskette
7. Diskette Parameter Table (DPT) for PC-ROM-BIOS
8. About the source code
9. The boot process for the 1.44 MB Feature

### 1. Diskette layout

```
; Layout of a 1.44 MB diskette (18 sectors per track) or a 1.2 MB diskette (15
; sectors per track) or a 720 KB diskette (9 sectors per track) after it has 
; been prepared ("formatted") by this 144PREP2 program, as "seen" by DOS, 
; by the standard CP/M-86 for IBM, and by the 1.44 MB Feature for CP/M-86 1.1:

; track 0
;-sector-  -------------DOS----------  ----standard CP/M-86---  --144 feature--
;    1     bootsector for 160 KB       bootsector, media byte   reserved
;    2     reserved                    system parameters        reserved
;    3     1st FAT                     not used?                reserved
;    4     2nd FAT                     not used?                reserved
;    5     DOS directory (16 entries)  boot code                reserved
;  6...8   data, bad sectors           boot code                reserved
;  9..18   not recognized              not recognized           reserved
;
; track 1
;-sector-  -------------DOS----------  ----standard CP/M-86---  --144 feature--
;  1...4   data, bad sectors           CP/M-86 directory        reserved
;  5...8   data, bad sectors           data, used sectors       reserved
;  9..18   not recognized              not recognized           reserved
;
; In the DOS FAT's, all clusters are marked as "bad clusters. This prevents DOS
; from writing to the diskette's data area (not to the DOS directory - but
; that wouldn't harm the CP/M-86 data).
;
; The DOS directory is empty, except for a volume label "CPM-86-DISK" with
; date and time stamps that indicate when the diskette was prepared.
;
; In the directory as seen by standard CP/M-86, is a single file called
; "CP/M-86.144" c.q. "CP/M-86.720" c.q. "CP/M-86.12M" that uses all available
; (i.e. 160 KB) diskette space. This prevents standard CP/M-86 from writing 
; to the diskette, which it is seeing as a 160 KB, 40 tracks, single sided
; diskette.
;
; CP/M-86 1.1 when enhanced with the 1.44 MB feature, has its 8 KB directory
; on track 2 and (for 720 KB and 1.2 MB) on the first sectors of track 3.
; It ignores tracks 0 and 1 on the diskette. This prevents the 1.44 MB feature
; from writing to the track 0 and 1 information that is used to "cheat" DOS and
; standard CP/M-86 1.1.
;
; Sectors 6 and higher on track 0, and sectors 5 and higher on track 1 could
; be used for storing code to boot CP/M-86 from a 1.44 MB, 720 KB or 1.2 MB
; diskette. Note that this would also require changing the code on sector 1 
; on track 0, as written by this 144PREP2 program. 
; However, generally speaking it would be better to put such code into a small
; "regular" CP/M-file on a diskette, and to have that file loaded by code on
; the single boot sector on track 0.
```

### 2. Boot sector details

The "1.44 MB Feature" uses the last 16 bytes of the bootsector (sector 1
on track 0, head 0) as described below.

If you ever want to write a program that should be able to recognize the
diskette type in a given drive, pay attention to the version and media bytes
as defined by the "1.44 MB Feature".

The last 16 bytes on a diskette bootsector:

```
DWORD	must be 0

DWORD	must be 0

DWORD	diskette volume number (a binary value based on the date and time the
	diskette was prepared by 144PREP2).

	This volume number might be used by a future release of the 1.44 MB
	Feature to detect a diskette media change, and prompt for the correct
        diskette.

BYTE	reserved; MS-DOS seems to expect this byte to be 0. Don't touch it.

BYTE	boot drive, can be used by a boot loader to determine the drive
        from where it was started.

	On a diskette, this byte should be 0.

	On a harddisk, this byte should be 128 = hex. 80h.

BYTE	version of 144PREP(2) that prepared this diskette. 

	Value is 1 for all current versions of the 1.44 MB Feature software. It
        might be used by a future release of the 1.44 MB Feature to support
        multiple formats for a given media type.

BYTE	The CP/M-86 media byte. This byte, the very last byte on the very first
        sector of a diskette, defines the type of diskette.

	In standard CP/M-86, only two values are recognized:

	1 = double-sided 40 tracks diskette, 8 sectors per track (320 KB)

	any other value = single-sided 40 tracks diskette, 
			  8 sectors per track (160 KB)

	Version 2 of the "1.44 MB feature" defines three additional specific,
	decimal values:

	144 = double-sided 80 tracks diskette, 18 sectors per track (1.44 MB)
	72  = double-sided 80 tracks diskette, 9 sectors per track (720 KB)
	12  = double-sided 80 tracks diskette, 15 sectors per track (1.2 MB)

	Finally. version 2 of the 1.44 MB feature supports this media byte:

	17  = double-sided 80 tracks diskette, 9 sectors per track (720 KB)
              as used by "Personal CP/M Plus 2.0". Note that the ordering of
	      data on the diskette for this format differs from the ordering
              on 720 Kb diskettes with media byte value 72.
```

## CP/M-86 1.44 MB diskette
---------------------------

```
;output from stat dsk: for a 1.44 MB CP/M-86 diskette:
;
;     X: Drive Characteristics
;11,360: 128 Byte Record Capacity
; 1,420: Kilobyte Drive  Capacity
;   256: 32 Byte  Directory Entries
;   256: Checked  Directory Entries
;   256: 128 Byte Records / Directory Entry
;    32: 128 Byte Records / Block
;    72: 128 Byte Records / Track
;     2: reserved  Tracks

;------ DPB for 1.44 MB

bls144		equ	4096		;block size is 32 sectors of 128 bytes

dpb144:					;DPB control block
spt144		dw	72		;number of 128-byte sectors per track
bsh144		db	5		;block shift count: bls144 = (2^5) *128
blm144		db	31		;block mask
exm144		db	1		;extent mask
dsm144		dw	354		;355 blocks of bls144 bytes on a floppy
drm144		dw	255		;256 dir entries of 32 bytes, total is
					;8 KB is 2 blocks of bls144 bytes
al0144		db	0c0h		;2 directory blocks of bls144 bytes
al1144		db	0
cks144		dw	64		;64 sectors of 128 bytes is 8 KB
off144		dw	2		;2 reserved tracks. BDOS adds this when
					;calling BIOS routine "settrk".
```

### 4. CP/M-86 720 KB diskette

```
;output from stat dsk: for a 720 KB CP/M-86 diskette:
;
;     A: Drive Characteristics
; 5,680: 128 Byte Record Capacity
;   710: Kilobyte Drive  Capacity
;   256: 32 Byte  Directory Entries
;   256: Checked  Directory Entries
;   128: 128 Byte Records / Directory Entry
;    16: 128 Byte Records / Block
;    36: 128 Byte Records / Track
;     2: reserved  Tracks

;------ DPB for 720 KB

bls720		equ	2048		;block size is 16 sectors of 128 bytes

dpb720:					;DPB control block
spt720		dw	36		;number of 128-byte sectors per track
bsh720		db	4		;block shift count: bls720 = (2^4) *128
blm720		db	15		;block mask
exm720		db	0		;extent mask
dsm720		dw	354		;355 blocks of bls720 bytes on a floppy
drm720		dw	255		;256 dir entries of 32 bytes, total is
					;8 KB is 4 blocks of bls720 bytes
al0720		db	0f0h		;4 directory blocks of bls720 bytes
al1720		db	0
cks720		dw	64		;64 sectors of 128 bytes is 8 KB
off720		dw	2		;2 reserved tracks. BDOS adds this when
					;calling BIOS routine "settrk".

```

### 5. CP/M-86 1.2 MB diskette

```
;output from STAT DSK: for a 1.2 MB CP/M-86 diskette:
;
;     X: Drive Characteristics
; 9,472: 128 Byte Record Capacity
; 1,184: Kilobyte Drive  Capacity
;   256: 32 Byte  Directory Entries
;   256: Checked  Directory Entries
;   256: 128 Byte Records / Directory Entry
;    32: 128 Byte Records / Block
;    60: 128 Byte Records / Track
;     2: reserved  Tracks

;------ DPB for 1.2 MB

bls12m		equ	4096		;block size is 16 sectors of 128 bytes

dpb12m:					;DPB control block
spt12m		dw	60		;number of 128-byte sectors per track
bsh12m		db	5		;block shift count: bls12m = (2^5) *128
blm12m		db	31		;block mask
exm12m		db	1		;extent mask
dsm12m		dw	295		;296 blocks of bls12m bytes on a floppy
drm12m		dw	255		;256 dir entries of 32 bytes, total is
					;8 KB is 4 blocks of bls12m bytes
al012m		db	0c0h		;2 directory blocks of bls12m bytes
al112m		db	0
cks12m		dw	64		;64 sectors of 128 bytes is 8 KB
off12m		dw	2		;2 reserved tracks. BDOS adds this when
					;calling BIOS routine "settrk".
```

### 6. "Personal CP/M-86 Plus" 720 KB diskette

```
;output from stat dsk: for a 720 KB "Personal CP/M-86 Plus" diskette:
;
;     A: Drive Characteristics
; 5,616: 128 Byte Record Capacity
;   702: Kilobyte Drive  Capacity
;   256: 32 Byte  Directory Entries
;   256: Checked  Directory Entries
;   128: 128 Byte Records / Directory Entry
;    16: 128 Byte Records / Block
;    36: 128 Byte Records / Track
;     4: reserved  Tracks

;------ DPB for 720 KB "Personal CP/M-86 Plus"

bls72p		equ	2048		;block size is 16 sectors of 128 bytes

dpb72p:					;DPB control block
spt72p		dw	36		;number of 128-byte sectors per track
bsh72p		db	4		;block shift count: bls72p = (2^4) *128
blm72p		db	15		;block mask
exm72p		db	0		;extent mask
dsm72p		dw	350		;350 blocks of bls72p bytes on a floppy
drm72p		dw	255		;256 dir entries of 32 bytes, total is
					;8 KB is 4 blocks of bls72p bytes
al072p		db	0f0h		;4 directory blocks of bls72p bytes
al172p		db	0
cks72p		dw	64		;64 sectors of 128 bytes is 8 KB
off72p		dw	4		;4 reserved tracks. BDOS adds this when
					;calling BIOS routine "settrk".

```


### 7. Diskette Parameter Table (DPT) for PC-ROM-BIOS

```
;Original CP/M-86 supplies its own single DPT for both 160 and 320 KB media
;by pointing INT 1Eh address to offset 3AC6 within the CP/M-86 segment. This
;standard CP/M table has the following values (descriptions taken from a Norton
;Guide called "Interrupts & Ports", which is based on Ralf Brown's interrupt
;list):
;
;offset 00: CFh = 4-bit step rate and 4-bit head unload times
;offset 01: 02h = 7-bit head load time and 1-bit DMA flag
;offset 02: 25h = motor off time in clock ticks (36 to 38 typical)
;offset 03: 02h = sector size in bytes (0->128, 1->256, 2->512, 3->1024)
;offset 04: 08h = last sector number (8 or 9 typical)
;offset 05: 2Ah = inter-sector gap size on read/write (42 typical)
;offset 06: FFh = data transfer length (255 typical)
;offset 07: 50h = inter-sector gap size on format (80 typical)
;offset 08: E5h = sector fill on format (F6h typical)
;offset 09: 00h = head settle time ms (typical 25, 1.10->0, 2.10->15, 3.10->1)
;offset 0A: 04h = motor start-up time (1/8 secs) (typical 4, 2.10 ->2)
;
;With the standard CP/M-86-supplied program SETUP.CMD you can set the step
;rate to 2,4,6...32 msecs, corresponding to the values FFh,EFh,DFh...0Fh for
;the first byte of this DPT.
;
;For 720 KB and 1.44 MB, 3.5 inch diskettes we will use a different DPT
;(source: MS-DOS 6.2):
;DF 02 25 02 12 1B FF 6C F6 0F 08.
;
;For 1.2 MB on 5.25 inch media we will use (source: C'T):
;DF 02 25 02 0F 1B FF 54 F6 0F 08.

```

### 8. About the source code

The assembler source code is for Microsoft MASM version 5.1. The supplied
DOS batchfile 144MAKE2.BAT will build the CP/M-86 CMD executables. 

A sample batch file to create a CP/M-86 executable with Microsoft MASM and
LINK:

```
	masm 144PAT2 144PAT2.OBJ;
	link /tiny 144PAT2.OBJ,144PAT2.COM;
	copy /b CPMHDR32.BIN + 144PAT2.COM 144PAT2.CMD
```

where the source code must be written using the segment structure, conventions
etc. for a DOS .COM file.

The linker option /tiny creates a DOS .COM file.

The copy /b puts a CP/M-86 CMD header in front of the DOS .COM file, making
a CP/M-86 .CMD executable program. Don't forget the /b option, to force a
binary copy.

This CMD header CPMHDR32.BIN tells the CP/M-86 loader that the program which
follows this header, is 32 KB in size. The loader apparently doesn't mind
that the actual program size is less than 32 KB (however, Jim Lopushinsky's
CP/M-86 emulator for DOS _does_ mind, and will not run such a CMD file).

Finally, use the utility of your choice to transfer the .CMD executable to 
a CP/M-86 diskette or harddisk.


### 9. The boot process for the 1.44 MB Feature

When you boot your system from a higher capacity diskette prepared by the
1.44 MB Feature:
- the boot sector code looks for the file 144BLDR2.CMD in the CP/M-86 directory
  and loads the first 4 KB of the file into high memory
- control is transferred to the code in 144BLDR2.CMD
- 144BLDR2.CMD looks for the file CPM.SYS in the CP/M-86 directory and
  loads the file according to the definition in the header of CPM.SYS
  (normally, at segment value 0051h). 
- 144BLDR2.CMD makes some changes to the memory image of CPM.SYS, adds
  routines for the support of higher capacity diskettes, allocates a large
  stack, and cold starts CP/M-86.

If you use a RAMDISK with standard CP/M-86, CP/M-86 allocates memory for 
this RAMDISK up to 640 KB (segment A000h). However, on some modern systems,
the top one or two KB's contain the "extended BIOS data area" which is reserved
for and used by the PC-ROM-BIOS. Code in 144BLDR2.CMD prevents CP/M-86 from
using and overwriting this data area.


### Last but not least

Thanks to Tim Olmstedt, John Elliott, Barry Watzman.
The test team: Kirk Lawrence, Steve Dubrovich, Stephen Hunt.

Questions? Remarks? Bugs? Share them in the newsgroup comp.os.cpm on the 
internet.

You may use, misuse and abuse this software any way you want - but at your own
risk. The author of the software does not accept any responsibility for the
consequences of such use, misuse or abuse.


- Version: 2.0
- Date   : 16Oct2000
- Author : Freek Heite
- Email  : fheite@knoware.nl

