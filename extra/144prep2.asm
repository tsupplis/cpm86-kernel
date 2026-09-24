; 144PREP2.ASM  - version 1, initial release (DOS only)
; 144PREP2.ASM - version 2, dual CP/M-86 and DOS source; added 1.2 MB support;
;		 added boot capability.

; Date   : 16Oct2000
; Author : Freek Heite
; Email  : fheite@knoware.nl

;------

; The 1.44 MB Feature Program for CP/M-86.
; Makes CP/M-86 support 720 KB, 1.2 MB and 1.44 MB diskettes, at (nearly)
; these capacities.

; Thanks to Tim Olmstedt, John Elliott, Barry Watzman.
; The test team: Kirk Lawrence, Steve Dubrovich, Stephen Hunt.

; In this program, "CP/M-86" is used as a shorthand notation for 
; "CP/M-86 for the IBM PC and IBM PC XT  Version 1.1",
; which is "Copyright (C) 1983, Digital Research".

;------

; This program will prepare a standard, 720 KB or 1.44 MB, 3.5 inch diskette or
; a standard, 1.2 MB, 5.25 inch diskette for use with "CP/M-86 for the IBM PC
; and IBM PC XT Version 1.1".
; To actually USE the full 720 KB, 1.2 MB or 1.44 MB capacity under CP/M-86,
; you also need the "1.44 MB Feature" program for CP/M-86, 144PAT2.CMD.

; NOTE: the diskette must already have been formatted, as a 720 KB, 1.2 MB or
; 1.44 MB diskette, with any standard DOS, Windows or OS/2 FORMAT program, or 
; the diskette must have been pre-formatted by the diskette's manufacturer.
;
; Technically: this program does NOT perform a low-level format of the
; diskette media, it just writes some data that CP/M-86 is expecting to find
; on a diskette.

; The source code is written for Microsoft MASM 5.1.

;------

; Layout of a 1.44 MB diskette (18 sectors per track) or a 1.2 MB diskette (15
; sectors per track) or a 720 KB diskette (9 sectors per track) after it has 
; been prepared ("formatted") by this 144PREP program, as "seen" by DOS, 
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
; on track 0, as written by this 144PREP program. 
; However, generally speaking it would be better to put such code into a small
; "regular" CP/M-file on a diskette, and to have that file loaded by code on
; the single boot sector on track 0.

;-------------- define target operating system ------------------------

DOS	equ	0		;0 = assemble for CP/M-86 executable .CMD file
				;1 = assemble for DOS executable .COM file

CPM	equ	DOS - 1		;don't change this line

;The DOS version of the executable will not write the secondary boot loader
;program 144BLDR2.CMD to the diskette, as DOS doesn't know who to put a file
;onto a CP/M-86 file system.

;-------------- MASM 5.1 prolog for a .COM file -----------------------

prep2	segment	para public 'code'
	assume	cs:prep2
	assume	ds:prep2
	assume	es:nothing
	org	100h
$fbegin:

	jmp	r0000		;jump past the data area

;============== data areas ============================================

w_buf	dw	?		;segment of full track buffer for INT 13h

w_track	db	?		;track counter 0...79		
w_error	db	?		;PC-ROM-BIOS INT 13h error code 0...255

w_drive	db	?		;1 or 2, meaning drive A: or drive B:

w_quick	db	0		;0 or 1, meaning no/yes quick prepare
w_720	db	0		;0 or 1, meaning 1.44 MB / 720 KB capacity
w_12m	db	0		;0 or 1, meaning 1.44 MB / 1.2 MB capacity
w_verb	db	0		;0 or 1, meaning no/yes verbose output
w_3inch	db	0		;0 or 1, meaning no/yes always use 3.5 inch DPT

n_sect	db	18		;sectors per track (9 if 720 KB, 18 if 1.44 MB,
				;                   15 if 1.2 MB)

w_sect	db	?		;# sectors read/written by INT 13h 0...18

kbackup	db	'PVBACKUP'
k44tag	db	'BLDR'

;------

IF CPM

kfeat	db	8 dup(0)	;ASCII text '41F4AE02'

fcbldr	db	0,'144BLDR2CMD'
	db	24 dup(0)

fcbxxx	dw	?		;address of fcb being processed (fcbldr/fcbsys)

cpmseg	dw	?		;the CP/M-86 code and data segment

curdsk	db	0		;current drive
curuser	db	0		;current user number

save1b	dd	0		;save interrupt 1Bh (control-break handler)
save1e	dd	0		;save interrupt 1Eh (pointer to DPT)

;local stack stuff

STAKSIZ	equ	128		;size of local stack in words
endstak	equ	$
	db	STAKSIZ dup('fh')	;local stack
mystack	equ	$

;offsets within CP/M-86 system parameter area (normally located at 51h:24A0h)

sysklok	equ	20h		;ASCII date & time as "mo/dd/yy,hh:mm:ss"
sysmo	equ	sysklok		;month
sysdd	equ	sysklok+3	;day
sysyy	equ	sysklok+6	;year (two digits)
syshh	equ	sysklok+9	;hours
sysmm	equ	sysklok+12	;minutes
sysss	equ	sysklok+15	;seconds

;memory control stuff

mcb18k	equ	$		;memory control block for 18 KB getmain
mcbase	dw	0
mcblen	dw	18 * 32 * 2	;request 18 * 32 * 2 = 1152 paragraphs
				;= sectors/track * paragraphs/sector * 2
				;= 18 KB
mcbext	db	0

ENDIF

;------ DPT's for 3.5 inch diskettes (values taken from MS-DOS 6.2)
;       and for 1.2 MB capacity on 5.25 inch diskette (values taken from 
;	the magazine C'T, 02/1990)

IF CPM
	db	'DPT12>>>'
dpt12:	db	0dfh,002h,025h,002h,00fh,01bh,0ffh,054h,0f6h,00fh,008h
	db	'<<<DPT12'

	db	'DPT35>>>'
dpt35:	db	0dfh,002h,025h,002h,012h,01bh,0ffh,06ch,0f6h,00fh,008h
	db	'<<<DPT35'
ENDIF

;-------------- messages ----------------------------------------------

m000	db	'The 1.44 MB Feature for CP/M-86 - by Freek Heite - '
	db	'version 2 - '
	db	'16Oct2000'
	db	0dh,0ah
	db	'$'

m00A	db	0dh,0ah
	db	'This program will prepare a standard,'
	db	' 720 KB or 1.44 MB, 3.5 inch diskette or'
	db	0dh,0ah
	db	'a standard, 1.2 MB, 5.25 inch diskette for '
	db	'use with "CP/M-86 for the IBM PC'
	db	0dh,0ah
	db	'and IBM PC XT Version 1.1".'
	db	0dh,0ah
	db	'To actually USE the full 720 KB, 1.2 MB or 1.44 MB capacity '
	db	'under CP/M-86,'
	db	0dh,0ah
	db	'you also '
	db	'need the "1.44 MB Feature" program for CP/M-86, 144PAT2.CMD.'

	db	0dh,0ah
	db	0dh,0ah

	db	'NOTE: the diskette must already have been'
	db	' formatted, as a 720 KB, 1.2 MB or'
	db	0dh,0ah
	db	'1.44 MB diskette, with any standard DOS, Windows or OS/2'
	db	' FORMAT program, or'
	db	0dh,0ah
	db	'the diskette must have been pre-formatted '
	db	'by the diskette''s manufacturer.'
	db	0dh,0ah
	db	'Technically: this program does NOT perform a low-level format'
	db	' of the'
	db	0dh,0ah
	db	'diskette media, it just writes some data that CP/M-86 '
	db	'is expecting to find'
	db	0dh,0ah
	db	'on a diskette.'

	db	0dh,0ah
	db	0dh,0ah

IF DOS
	db	'NOTE: DOS will treat a 720 KB, 1.2 MB or 1.44 MB '
	db	'CP/M-86-diskette as a DOS '
	db	0dh,0ah
	db	'160 KB diskette with no free space available, '
	db	'and all clusters marked as "bad".'

	db	0dh,0ah
	db	0dh,0ah
ENDIF
	db	'$'

m001	db	'M001 - Insert new '
m001a	db	'1.44 M'
	db	'B diskette in drive '
m001b	db	'x: and press ENTER when ready...'
	db	0dh,0ah
	db	'       or press control-C to stop.'
	db	0dh,0ah
	db	'       WARNING: all existing data on the diskette '
	db	'will be lost!'
	db	0dh,0ah,'$'

IF DOS
m002	db	0dh,0ah
	db	'M002 - Sorry, this program requires DOS'
	db	' version 3.3 or higher.'
	db	'$'
ENDIF

m003	db	0dh,0ah
	db	'M003 - Sorry, this program can prepare a CP/M-86 diskette'
	db	0dh,0ah
	db	'       only in diskette-drives A: or B: (if present).'
	db	'$'

m004	db	0dh,0ah
	db	'M004 - Sorry, your system does not seem to have'
	db	' any diskette drives.'
	db	'$'

m005	db	0dh,0ah
	db	'M005 - Sorry, drive B: does not seem to be '
	db	'a real diskette drive.'
	db	'$'

m006	db	0dh,0ah
	db	'M006 - Sorry, a request for 18 KB of memory failed (RC='
m006a	db	'xxxxh).'
	db	'$'

m007	db	'M007 - Using the '
m007a	db	'xxx data buffer, at '
m007b	db	'xxxx0h - '
m007c	db	'xxxxFh.'
	db	0dh,0ah,'$'

m008	db	'M008 - Sorry, missing parameter: specify a valid diskette '
	db	'drive (A: or B:).'
	db	'$'

m009	db	'M009 - Diskette preparation was successful.'
	db	0dh,0ah
	db	'       Volume Serial Number '
m009a	db	'XXXX-'
m009b	db	'XXXXh'

IF DOS
	db	'.',0dh,0ah
	db	'       To make this diskette bootable, '
	db	'you must run PIP under CP/M-86'
	db	0dh,0ah
	db	'       to put the files 144BLDR2.CMD and CPM.SYS '
	db	'onto the diskette.'
	db	0dh,0ah,'$'
ELSE
	db	' created on (dmy) '
m009dd	db	'00/'
m009mo	db	'00/'
m009cc	db	'00'
m009yy	db	'00 at '
m009hh	db	'00:'
m009mm	db	'00:'
m009ss	db	'00'
	db	'.'
	db	0dh,0ah,0dh,0ah
	db	'       To make this diskette bootable, you must pip '
	db	'a CPM.SYS file to it.'
	db	0dh,0ah,0dh,0ah
	db	'       P.S. Don''t forget to press control-C after '
	db	'changing diskettes!'
	db	0dh,0ah,'$'
ENDIF

m010	db	'M010 - Sorry, diskette preparation has failed.'
	db	'$'

m011	db	'>','$'			;progress indicator

m012	db	'M012 - Sorry, invalid program option '
m012a	db	'X ignored. Valid options: 1 3 7 Q V.'
	db	0dh,0ah
	db	'$'

m013	db	'M013 - Sorry, using both options 1 and 7 '
	db	'is not allowed; option '
m013a	db	'X ignored.'
	db	0dh,0ah
	db	'$'

m014	db	'M014 - CP/M-86 MCB before requesting 18 KB of memory:'
	db	0dh,0ah
	db	'$'

m015	db	'M015 - CP/M-86 MCB after requesting 18 KB of memory:'
	db	0dh,0ah
	db	'$'

m016	db	'       M-Base='
m016a	db	'xxxxh M-Length='
m016b	db	'xxxxh M-Ext='
m016c	db	'xxh.'
	db	0dh,0ah
	db	'$'

m017	db	'M017 - This program has used '
m017a	db	'xxxxh bytes on the stack.'
	db	0dh,0ah
	db	'$'

m018	db	'M018 - CP/M-86 MCB before freeing 18 KB of memory:'
	db	0dh,0ah
	db	'$'

m019	db	'M019 - CP/M-86 MCB after freeing 18 KB of memory:'
	db	0dh,0ah
	db	'$'

m020	db	'M020 - The current code segment register CS is '
m020a	db	'xxxxh,'
	db	0dh,0ah
	db	'       the CP/M-86 code and data segment is '
m020b	db	'xxxxh.'
	db	0dh,0ah
	db	'$'

m021	db	'M021 - Track 0 has been verified.'
	db	0dh,0ah
	db	'$'

m022	db	'M022 - Sorry, boot sector image not found '
	db	'within 144PREP program.'
	db	'$'

m023	db	'M023 - Sorry, secondary boot loader image not found '
	db	'within 144PREP program.'
	db	'$'

	db	0dh,0ah,'$'

m024	db	'M024 - Sorry, this program requires that '
	db	'the "1.44 MB Feature" support for'
	db	0dh,0ah
	db	'       higher capacity diskettes, '
	db	'program 144PAT2.CMD, has been loaded.'
	db	'$'

m025	db	'M025 - Sorry, cannot create file 144BLDR2.CMD on drive '
m025a	db	'@:.'
	db	0dh,0ah
	db	'$'

m026	db	'M026 - Sorry, cannot write to file 144BLDR2.CMD on drive '
m026a	db	'@:.'
	db	0dh,0ah
	db	'$'

m027	db	'M027 - Sorry, cannot close file 144BLDR2.CMD on drive '
m027a	db	'@:.'
	db	0dh,0ah
	db	'$'

m028	db	'M028 - Diskette successfully cleared.'
	db	0dh,0ah
	db	'$'

m029	db	'M029 - Boot sector written successfully.'
	db	0dh,0ah
	db	'$'

m030	db	'M030 - Dummy directories, FAT  etc. written successfully.'
	db	0dh,0ah
	db	'$'

m031	db	'M031 - File 144BLDR2.CMD made/opened successfully.'
	db	0dh,0ah
	db	'$'

m032	db	'M032 - Sorry, cannot set file 144BLDR2.CMD on drive '
m032a	db	'@: to read-only.'
	db	0dh,0ah
	db	'$'

m101	db	0dh,0ah
	db	'M10'
m101x	db	'1 - Error '
m101y	db	'writing diskette in drive '
m101z	db	'x:'
	db	' cyl='
m101a	db	'xxh head='
m101b	db	'xxh sector='
m101c	db	'xxh',0dh,0ah,'       Returncode='
m101d	db	'xxh: $'

m201	db	'Invalid command.',0dh,0ah,'$'
m202	db	'Address mark not found.',0dh,0ah,'$'
m203	db	'Attempt to write on write-protected disk.',0dh,0ah,'$'
m204	db	'Sector not found.',0dh,0ah,'$'
m205	db	'Reset failed (fixed).',0dh,0ah,'$'
m206	db	'Diskette change line active (floppy).',0dh,0ah,'$'
m207	db	'Drive parameter activity failed (fixed).',0dh,0ah,'$'
m208	db	'DMA overrun.',0dh,0ah,'$'
m209	db	'Attempt to DMA across a 64K boundary.',0dh,0ah,'$'
m20a	db	'Bad sector flag detected (fixed).',0dh,0ah,'$'
m20b	db	'Bad cylinder found (fixed).',0dh,0ah,'$'
m20c	db	'Media type not found (floppy).',0dh,0ah,'$'
m20d	db	'Invalid number sectors on format (fixed).',0dh,0ah,'$'
m20e	db	'Control data address mark detected (fixed).',0dh,0ah,'$'
m20f	db	'DMA arbitration level out of range (fixed).',0dh,0ah,'$'
m210	db	'CRC or ECC data error.',0dh,0ah,'$'
m211	db	'ECC corrected data error (fixed).',0dh,0ah,'$'
m220	db	'Controller failure.',0dh,0ah,'$'
m240	db	'Seek failure.',0dh,0ah,'$'
m280	db	'Drive not ready.',0dh,0ah,'$'
m2bb	db	'Undefined error (fixed).',0dh,0ah,'$'
m2cc	db	'Write fault (fixed).',0dh,0ah,'$'
m2e0	db	'Status error (fixed).',0dh,0ah,'$'
m2ff	db	'Sense operation failed (fixed).',0dh,0ah,'$'

m2zz	db	'*** Unknown error code ***.',0dh,0ah,'$'

;============== real start of code ====================================
r0000:

	mov	dx,offset m000		;intro
IF DOS
	mov	ah,9			;display text
	int	21h
ELSE
	mov	cl,9			;display text
	int	0e0h

	cli
	push	cs
	pop	ss			;switch to
	mov	sp,offset mystack	; local stack
	sti
ENDIF

;-------------- check for images at end of this program ---------------

	push	cs
	pop	es

	mov	si,offset kbackup	;text PVBACKUP in boot sector image
	mov	di,offset pvbackup
	mov	cx,8
	cld
	rep	cmpsb
	jz	r0005			;OK, found

	mov	dx,offset m022		;not found
IF DOS
	mov	ah,9			;display text
	int	21h
	mov	ax,4c22h		;stop run
	int	21h
ELSE
	mov	cl,9			;display text
	int	0e0h
	jmp	stoprun
ENDIF

r0005:
	mov	si,offset k44tag	;text BLDR in secondary boot image
	mov	di,offset x44tag
	mov	cx,4
	cld
	rep	cmpsb
	jz	r0010			;OK, found

	mov	dx,offset m023		;not found
IF DOS
	mov	ah,9			;display text
	int	21h
	mov	ax,4c23h		;stop run
	int	21h
ELSE
	mov	cl,9			;display text
	int	0e0h
	jmp	stoprun
ENDIF

;-------------- Is the 1.44 MB Feature active? -----------------------

r0010:

IF CPM
	mov	word ptr [kfeat+0],'14'
	mov	word ptr [kfeat+2],'4F'
	mov	word ptr [kfeat+4],'EA'
	mov	word ptr [kfeat+6],'20'

	mov	ax,050h			;start looking for signature at 0051h
r0015:
	inc	ax
	mov	es,ax
	mov	si,offset kfeat
	mov	di,03BE2h		;offset of signature in CP/M-86 segment
	mov	cx,8
	cld
	rep	cmpsb			;scan for signature
	jz	r0020			;jump if found

	cmp	ax,9000h		;do not scan above segment 9000h
	jb	r0015

	mov	dx,offset m024		;driver for 1.44 MB Feature not active
	mov	cl,9			;display text
	int	0e0h
	jmp	stoprun

r0020:
	mov	[cpmseg],ax

ENDIF

;-------------- DOS version must be >= 3.0 ----------------------------


IF DOS
	mov	ah,30h		;get DOS version
	int	21h

	cmp	al,3		;major versiom >= 3?
	jge	r0025		;yes, OK

	mov	ah,9		;display text
	mov	dx,offset m002
	int	21h
	mov	ax,4c02h	;stop run
	int	21h
r0025:

ELSE
;	nop			;don't check CP/M-86 version
ENDIF

;-------------- show some additional info -----------------------------

	mov	dx,offset m00A
IF DOS
	mov	ah,9			;display text
	int	21h
ELSE
	mov	cl,9			;display text
	int	0e0h
ENDIF

;-------------- check command line options ----------------------------

;Options must follow the diskette drive letter and its colon. Don't put any
;blanks, tabs etc. between the options - otherwise they might not be found
;within the first or second FCB's.
;
;The options are:
; Q for a quick prepare (writes only to both sides of tracks 0...3)
; 1 for a 1.2 MB diskette (default is 1.44 MB)
; 7 for a 720 KB diskette (default is 1.44 MB)
; V for verbose (debugging) output
; 3 for testing 1.2 Mb format on 3.5 inch media

;Invalid options are reported and ignored.

	mov	bx,0			;index into file name part in FCB's
r0030:
	mov	al,DS:[05dh+bx]		;get option character from FCB 1
	call	chkopt

	mov	al,DS:[06dh+bx]		;get option character from FCB 2
	call	chkopt

	inc	bx			;prepare for next option character
	cmp	bx,7			;all eight positions 0...7 scanned?
	jle	r0030			;no, not yet

;------
	cmp	w_720,0			;preparing a 720 KB diskette?
	jz	r0035			;no
	mov	n_sect,9		;yes, 9 sectors per track, 720 KB
	mov	byte ptr cpmedia,72	;CP/M-86 "media byte"
					; for 720 KB diskette

	mov	word ptr m001a+0,'7 '
	mov	word ptr m001a+2,'02'
	mov	word ptr m001a+4,'K '

	mov	byte ptr FT+0,'7' + 80h	;set write protect bit
	mov	byte ptr FT+1,'2'
	mov	byte ptr FT+2,'0'
	jmp	r0045

;------
r0035:
	cmp	w_12m,0			;preparing a 1.2 MB diskette?
	jz	r0045			;no
	mov	n_sect,15		;yes, 15 sectors per track, 1.2 MB
	mov	byte ptr cpmedia,12	;CP/M-86 "media byte"
					; for 1.2 MB diskette

	mov	word ptr m001a+0,'1 '
	mov	word ptr m001a+2,'2.'
	mov	word ptr m001a+4,'M '

	mov	byte ptr FT+0,'1' + 80h	;set write protect bit
	mov	byte ptr FT+1,'2'
	mov	byte ptr FT+2,'M'
r0045:

;-------------- show current CS and CP/M-segment ----------------------

IF CPM
	cmp	w_verb,0		;verbose?
	jz	r0055			;no

	mov	ax,cs			;show CS in hex
	mov	si,offset m020a		
	call	w2hex

	mov	ax,[cpmseg]		;show the CP/M segment
	mov	si,offset m020b
	call	w2hex

	mov	dx,offset m020
	mov	cl,9			;display text
	int	0e0h
ENDIF

r0055:

;-------------- check drive parameter ---------------------------------

r0100:
	mov	al,DS:05ch	;1=A 2=B
	mov	w_drive,al

IF CPM
	mov	fcbldr,al
;	mov	fcbsys,al
ENDIF

	add	m025a,al	;make
	add	m026a,al	; ASCII
	add	m027a,al	;  digit
	add	m032a,al

	cmp	al,0		;any drive given in first FCB?
	jne	r0105		;yes, OK

	mov	dx,offset m008	;no
IF DOS
	mov	ah,9		;display text
	int	21h
	mov	ax,4c08h	;stop run
	int	21h
ELSE
	mov	cl,9		;display text
	int	0e0h
	jmp	stoprun
ENDIF

r0105:
	cmp	w_drive,1	;A:?
	je	r0110		;yes, OK
	cmp	w_drive,2	;B:?
	je	r0110		;yes, OK

	mov	dx,offset m003	;invalid drive letter
IF DOS
	mov	ah,9		;display text
	int	21h
	mov	ax,4c03h	;stop run
	int	21h
ELSE
	mov	cl,9
	int	0e0h
	jmp	stoprun
ENDIF

r0110:
	mov	al,w_drive	;drive as 1 or 2
	add	al,40h		;make 'A' or 'B'
	mov	m001b,al
	mov	m101z,al

;-------------- is drive a real diskette drive? -----------------------

	int	11h		;get equipment bits

	test	al,1		;any diskette drives present?
	jnz	r0205		;yes

	mov	dx,offset m004	;no diskette drives in system
IF DOS
	mov	ah,9		;display text
	int	21h
	mov	ax,4c04h	;stop run
	int	21h
ELSE
	mov	cl,9		;display text
	int	0e0h
	jmp	stoprun
ENDIF

r0205:
	cmp	w_drive,1	;drive A: ?
	je	r0210		;yes: as we have at least one diskette drive,
				;A: should be a valid drive

	and	al,0c0h		;mask equipment bits 7...6 
	mov	cl,6		;put number of diskette drives
	shr	al,cl		; in bits 1...0 (0=1 drive, 1=2 drives etc.)

	cmp	al,1		;do we have at least 2 diskette drives?
	jae	r0210		;yes, so B: should be a valid drive

	mov	dx,offset m005	;no; so B: is not a real diskette drive
IF DOS
	mov	ah,9		;display text
	int	21h
	mov	ax,4c05h	;stop run
	int	21h
ELSE
	mov	cl,9		;display text
	int	0e0h
	jmp	stoprun
ENDIF
	
r0210:

;-------------- insert diskette, press ENTER to continue --------------

	mov	dx,offset m001
IF DOS
	mov	ah,9			;display text
	int	21h
ELSE
	mov	cl,9			;display text
	int	0e0h
ENDIF

	call	getenter

;-------------- freemain all unneeded memory --------------------------

IF DOS

;don't shrink below 64 KB, as our stack is at the top of our 64 KB
;code segment

	push	cs
	pop	es		;segment of block to reduce

	mov	ah,4ah		;SETBLOCK
	mov	bx,4096+1	;new block size, 64+ KB in 16 byte paragraphs
	int	21h
ENDIF

;-------------- getmain two track buffers -----------------------------

;It is said, that data buffers for PC-ROM-BIOS disk interrupt INT 13h cannot
;cross a 64 KB DMA boundary. So we allocate storage for 2 buffers (each 9 KB,
;the size of a full 18-sector track). 
;If the first buffer happens to cross a 64 KB boundary, we will use the second
;buffer.

r0305:

IF DOS
	mov	ah,48h		;allocate memory
	mov	bx,18 * 32 * 2	;request 18 * 32 * 2 = 1152 paragraphs
				;= sectors/track * paragraphs/sector * 2
				;= 18 KB
	int	21h

	mov	w_buf,ax	;INT 21h returns segment in AX
	jnc	r0399		;jump if OK
ELSE
	cmp	w_verb,0	;verbose?
	jz	r0310		;no

	call	fmtmcb

	mov	cl,9
	mov	dx,offset m014	;MCB before getmain
	int	0e0h

	mov	cl,9
	mov	dx,offset m016	;show MCB contents
	int	0e0h

r0310:
	mov	cl,55		;getmain 18 KB double track buffer
	mov	dx,offset mcb18k
	int	0e0h

	push	ax		;save return code

	cmp	w_verb,0	;verbose?
	jz	r0315		;no

	call	fmtmcb

	mov	cl,9
	mov	dx,offset m015	;MCB after getmain
	int	0e0h

	mov	cl,9
	mov	dx,offset m016	;show MCB contents
	int	0e0h

r0315:
	mov	bx,mcbase	;INT 0E0h returns segment in MCB-field mcbase
	mov	w_buf,bx	

	pop	ax		;restore return code

	cmp	al,0		;OK?
	je	r0399		;yes
	mov	ah,0		;let AH:=0; CP/M-86 error code is only in AL
ENDIF

	mov	si,offset m006a	;error code
	call	w2hex

	mov	dx,offset m006	;getmain error
IF DOS
	mov	ah,9		;display text
	int	21h
	mov	ax,4c06h	;stop run
	int	21h
ELSE
	mov	cl,9		;display text
	int	0e0h
	jmp	stoprun
ENDIF

r0399:

;-------------- check for 1st buffer crossing a 64 KB DMA boundary ----

	mov	cx,w_buf	;CX := buffer start segment (paragraphs)
	and	cx,0F000h	;mask buffer start to a 64 KB boundary

	mov	bx,w_buf	;BX := buffer start segment (paragraphs)
	add	bx,18 * 32	;BX := buffer end + 1 (paragraphs)
	and	bx,0F000h	;mask buffer end +1 to a 64 KB boundary

	mov	word ptr m007a,'s1'	;text '1st '
	mov	word ptr m007a+2,' t'

	cmp	bx,cx		;start & end in same 64 KB page?
	je	r0405		;yes, use first buffer

	add	w_buf,18 * 32	;no, use second buffer

	mov	word ptr m007a,'n2'	;text '2nd '
	mov	word ptr m007a+2,' d'
r0405:
	mov	ax,w_buf
	mov	si,offset m007b
	call	w2hex		;display buffer-start in hex

	mov	ax,w_buf
	add	ax,18 * 32
	dec	ax

	mov	si,offset m007c
	call	w2hex		;display buffer-end in hex

	mov	dx,offset m007

	cmp	w_verb,0	;verbose?
	jz	r0499		;no

IF DOS
	mov	ah,9		;display buffer usage
	int	21h
ELSE
	mov	cl,9
	int	0e0h
ENDIF

r0499:

;-------------- fill buffer with 0E5h ---------------------------------

	mov	es,w_buf
	mov	di,0
	mov	cx,18 * 512	;18 sectors, 512 bytes each
	mov	al,0E5h

	cld
	rep	stosb

	push	ds
	pop	es		;restore ES

;------ Disable the control-break key combination; if the user were to abort
;	this program, we would not be able to restore DPT interrupt 1Eh.

IF CPM
	xor	ax,ax
	mov	es,ax				;ES := 0

	mov	ax,es:01bh+01bh+01bh+01bh	;save original
	mov	word ptr save1b,ax		;int 1Bh

	mov	ax,es:01bh+01bh+01bh+01bh+2
	mov	word ptr save1b+2,ax

	mov	es:01bh+01bh+01bh+01bh,offset int1b	;setup new
	mov	es:01bh+01bh+01bh+01bh+2,cs		;int 1Bh handler

	push	cs
	pop	es
ENDIF

;-------------- reset disks, flush buffers  ---------------------------

IF DOS
	mov	ah,0dh			;disk reset
	int	21h
ELSE
	mov	dl,255			;get it
	mov	cl,32			;set/get user code
	int	0e0h
	mov	curuser,al

	mov	cl,25			;return current disk
	int	0e0h
	mov	curdsk,al		;save it

	mov	cl,13			;reset disk system; the boot disk(ette)
	int	0e0h			;will now be made the current disk

ENDIF

;-------------- let interrupt 1Eh point to a DPT for 3.5 inch diskettes

IF CPM
	mov	ax,0
	mov	es,ax				;ES := 0

	mov	ax,es:01eh+01eh+01eh+01eh	;save original
	mov	word ptr save1e,ax		;int 1Eh

	mov	ax,es:01eh+01eh+01eh+01eh+2
	mov	word ptr save1e+2,ax

	mov	es:01eh+01eh+01eh+01eh,offset dpt35	;setup new
	mov	es:01eh+01eh+01eh+01eh+2,cs		;int 1Eh table

	cmp	w_3inch,0			;always use 3.5 inch DPT?
	jnz	r0505				;yes

	cmp	w_12m,0					;preparing 1.2 MB?
	jz	r0505					;no
	mov	es:01eh+01eh+01eh+01eh,offset dpt12	;yes, DPT for 1.2 MB
r0505:

	push	cs
	pop	es
ENDIF

;-------------- verify track 0, to clear the drive's change line indicator

	call	drvreset	;PC-ROM-BIOS reset diskette drive

	mov	ah,4		;verify
	mov	al,n_sect	;# sectors per track

	mov	ch,0		;track
	mov	cl,1		;starting sector

	mov	dh,0		;head
	mov	dl,w_drive	;drive 1 or 2 from FCB
	dec	dl		;make drive 0 or 1 for INT 13h

	int	13h		;ignore error, if any

	cmp	w_verb,0	;verbose
	jz	r0555		;no

	mov	dx,offset m021	;track 0 verified
IF DOS
	mov	ah,9		;display text
	int	21h
ELSE
	mov	cl,9		;display text
	int	0e0h
ENDIF

r0555:

;-------------- write 80 tracks ---------------------------------------

;Note: a "quick" prepare writes 0E5h only to both sides of tracks 0...3, i.e.
;the boot sector plus the directory area's.

	mov	w_track,0	;track counter 0...79 (0...3 if "quick")

	mov	ah,3		;write
	mov	al,n_sect	;# sectors per track

	mov	cl,1		;starting sector

	mov	dl,w_drive	;drive 1 or 2 from FCB
	dec	dl		;make drive 0 or 1 for INT 13h

	mov	es,w_buf	;segment address of buffer
	mov	bx,0		;offset of buffer
r0605:

; write a single track (= 9 or 15 or 18 sectors) head 0

	mov	ch,w_track	;track 0...79
	mov	dh,0		;head 0

	push	ax
	push	bx
	push	cx
	push	dx
	push	es

	int	13h
	jnc	r0609
	jmp	r0700		;jump if error
r0609:

; write a single track (= 9 or 15 or 18 sectors) head 1

	pop	es
	pop	dx
	pop	cx
	pop	bx
	pop	ax

	mov	ch,w_track	;track 0...79
	mov	dh,1		;head 1

	push	ax
	push	bx
	push	cx
	push	dx
	push	es

	int	13h
	jnc	r0611
	jmp	r0700		;jump if error

r0611:
	cmp	w_quick,1	;quick prepare requested?
	jz	r0612		;yes, skip progress indicator

	mov	dx,offset m011	;show progress
IF DOS
	mov	ah,9
	int	21h
ELSE
	mov	cl,9
	int	0e0h
ENDIF

r0612:
	pop	es
	pop	dx
	pop	cx
	pop	bx
	pop	ax
	
	inc	w_track		;next track

	cmp	w_quick,0	;prepare all 80 tracks?
	je	r0613		;yes

	cmp	w_track,4	;tracks 0...3 processed?
	jl	r0605		;no, go for next track
	jmp	r0614		;yes, done

r0613:
	cmp	w_track,80	;tracks 0...79 processed?
	jl	r0605		;no, go for next track

;-------------- diskette successfully filled with 0E5h ----------------

r0614:
	push	ds
	pop	es		;restore ES

	cmp	w_verb,0
	jz	r0615

	mov	dx,offset m028	;diskette filled with 0E5h
IF DOS
	mov	ah,9			;display text
	int	21h
ELSE
	mov	cl,9			;display text
	int	0e0h
ENDIF

r0615:

;-------------- write boot sector code --------------------------------

	call	stamp		;build time stamps

	mov	cx,512		;512 bytes per sector
	mov	si,offset bootstart
	mov	di,0

	mov	es,w_buf

	cld
	rep	movsb		;move boot sector data to 64KB-DMA-safe buffer

	mov	ah,3		;write
	mov	al,1		;1 sector

	mov	ch,0		;track 0
	mov	cl,1		;starting at sector 1

	mov	dh,0		;head 0
	mov	dl,w_drive	;drive 1 or 2 from FCB
	dec	dl		;make drive 0 or 1 for INT 13h

	mov	bx,0		;offset of buffer (segment is in ES)

	push	ax
	push	bx
	push	cx
	push	dx
	push	es

	int	13h
	jnc	r0616
	jmp	r0700		;jump if error
r0616:

	cmp	w_verb,0
	jz	r0617

	mov	dx,offset m029		;boot sector has been written
IF DOS
	mov	ah,9			;display text
	int	21h
ELSE
	mov	cl,9			;display text
	int	0e0h
ENDIF

r0617:

;-------------- is the boot sector readable? --------------------------

	pop	es
	pop	dx
	pop	cx
	pop	bx
	pop	ax

	mov	ah,1		;read

	int	13h
	jnc	r0619
	jmp	r0700		;jump if error
r0619:

;-------------- write 2 DOS FAT's -------------------------------------

	mov	cx,512		;512 bytes per sector
	mov	si,offset fat12start
	mov	di,0

	mov	es,w_buf

	cld
	rep	movsb		;move FAT data to 64KB-DMA-safe buffer

	mov	ah,3		;write
	mov	al,1		;1 sector

	mov	ch,0		;track 0
	mov	cl,3		;starting at sector 3

	mov	dh,0		;head 0
	mov	dl,w_drive	;drive 1 or 2 from FCB
	dec	dl		;make drive 0 or 1 for INT 13h

	mov	bx,0		;offset of buffer (segment is in ES)

	push	ax
	push	bx
	push	cx
	push	dx
	push	es

	int	13h		;write first FAT
	jnc	r0623
	jmp	r0700		;jump if error
r0623:

	pop	es
	pop	dx
	pop	cx
	pop	bx
	pop	ax

	push	ax
	push	bx
	push	cx
	push	dx
	push	es

	mov	cl,4		;starting at sector 4

	int	13h		;write second FAT
	jnc	r0627
	jmp	r0700		;jump if error
r0627:

	pop	es
	pop	dx
	pop	cx
	pop	bx
	pop	ax

;-------------- write small dummy DOS directory -----------------------

	mov	cx,512		;512 bytes per sector
	mov	si,offset dosdirstart
	mov	di,0

	mov	es,w_buf

	cld
	rep	movsb		;move directory data to 64KB-DMA-safe buffer

	mov	ah,3		;write
	mov	al,1		;1 sector

	mov	ch,0		;track 0
	mov	cl,5		;starting at sector 5

	mov	dh,0		;head 0
	mov	dl,w_drive	;drive 1 or 2 from FCB
	dec	dl		;make drive 0 or 1 for INT 13h

	mov	bx,0		;offset of buffer (segment is in ES)

	push	ax
	push	bx
	push	cx
	push	dx
	push	es

	int	13h
	jnc	r0635
	jmp	r0700		;jump if error
r0635:

	pop	es
	pop	dx
	pop	cx
	pop	bx
	pop	ax


;-------------- build CP/M-86 160 KB dummy directory ------------------

	mov	EX,0		;extent counter (0...9)
	
	mov	es,w_buf
	mov	di,0

r0650:
	mov	si,offset cpmdirstart
	mov	cx,32		;the size of a directory extent is 32 bytes

	cld
	rep	movsb		;move directory extent to 64KB-DMA-safe buffer

	mov	bx,offset ALL
r0660:
	add	byte ptr [bx],16	;add 16 to all 16 numbers in
	inc	bx			;the AL directory field
	cmp	bx,offset ALL + 16	;all 16 AL bytes processed?
	jne	r0660			;no

	inc	EX			;prepare for next extent
	cmp	EX,9			;at extent #9 (= the 10th extent)?
	jl	r0650			;no, at #1...#8, continue
	jg	r0670			;no, at #10, done

	mov	RC,50h			;record count for last extent, #9
	mov	word ptr ALL+10,0	;the last six
	mov	word ptr ALL+12,0	; bytes of AL
	mov	word ptr ALL+14,0	;  are empty (= zeroes)

	jmp	r0650			;continue

r0670:
	mov	cx,512-320	;fill the rest of the sector buffer with 0E5h,
	mov	al,0e5h		; i.e. everything after 10 32-byte dir entries.
	cld
	rep	stosb

;-------------- write dummy CP/M-86 160 KB directory ------------------

	mov	ah,3		;write
	mov	al,1		;1 sector

	mov	ch,1		;track 1
	mov	cl,1		;starting at sector 1

	mov	dh,0		;head 0
	mov	dl,w_drive	;drive 1 or 2 from FCB
	dec	dl		;make drive 0 or 1 for INT 13h

	mov	es,w_buf	;segment of buffer
	mov	bx,0		;offset of buffer 

	push	ax
	push	bx
	push	cx
	push	dx
	push	es

	int	13h
	jnc	r0680
	jmp	r0700		;jump if error
r0680:

	pop	es
	pop	dx
	pop	cx
	pop	bx
	pop	ax

	cmp	w_verb,0
	jz	r0685

	mov	dx,offset m030		;dummy directories, FAT etc. written
IF DOS
	mov	ah,9			;display text
	int	21h
ELSE
	mov	cl,9			;display text
	int	0e0h
ENDIF

r0685:

;-------------- write 144BLDR2.CMD file to diskette -------------------

;This is done only under CP/M-86, as we will use standard CP/M functions
;for creating, writing etc. of the secondary boot loader file.

r0800:

IF CPM

	call	rest1e			;restore diskette parameter table

	push	cs
	pop	es

;------ reset the diskette drive to re-login the freshly prepared diskette.
;       CP/M-86 should now recognize a higher capacity diskette, and set
;	the appropriate diskette parameter table at interrupt 1Eh.

	mov	cl,13			;reset disk system
	int	0e0h

	mov	dl,[w_drive]		;1/2
	dec	dl			;0/1 for function 14
	mov	cl,14			;select disk
	int	0e0h

	mov	ax,offset fcbldr
	mov	fcbxxx,ax

;------ go to user number 0

	mov	dl,0			;set it to 0
	mov	cl,32			;set/get user code
	int	0e0h
	
;------ open fcb for secondary boot loader

	mov	dx,fcbxxx
	mov	cl,22			;make file
	int	0e0h

	cmp	al,3			;return code 0...3?
	jbe	r0810			;OK

	mov	dx,offset m025		;file create error
	mov	cl,9			;display text
	int	0e0h

	mov	dl,curuser		;restore original user number
	mov	cl,32			;set/get user code
	int	0e0h

	jmp	stoprun2

r0810:
	cmp	w_verb,0
	jz	r0815

	mov	dx,offset m031		;file created OK
	mov	cl,9			;display text
	int	0e0h
r0815:

;------ set DMA address (offset only, using default segment)

	mov	dx,offset x44bldr2
	mov	cl,26			;set DMA address (offset)
	int	0e0h

;------ calculate record count for the secondary boot loader program image

	mov	ax,word ptr ds:[x44size];size of secondary boot loader (bytes)
	add	ax,128			;add size of CMD header
	add	ax,256			;add size of zero page (PSP)

	mov	cl,7			;convert AX from bytes
	shr	ax,cl			; to 128-byte records
	mov	cx,ax			;  into CX
	
	test	word ptr ds:[x44size],07fh
	jz	r0820
	inc	cx			;add 1 for partially filled record
r0820:

;------ write one 128-byte record

	push	cx			;record count
	push	dx			;DMA address

	mov	dx,fcbxxx
	mov	cl,21			;write sequential
	int	0e0h

	cmp	al,0			;OK?
	jz	r0830			;yes

;------ try to clean up after a write error

	pop	dx
	pop	cx

	mov	dx,fcbxxx
	mov	cl,16			;close file
	int	0e0h

	mov	dx,offset m025		;write error
	mov	cl,9			;display text
	int	0e0h			

r0825:
	mov	dx,fcbxxx
	mov	cl,19			;delete file
	int	0e0h

	mov	dl,curuser		;restore original user number
	mov	cl,32			;set/get user code
	int	0e0h

	jmp	stoprun2
r0830:
	
;------ prepare for writing next record

	pop	dx

	add	dx,128
	mov	cl,26			;set DMA address (offset)
	int	0e0h

	pop	cx
	loop	r0820			;loop if more records to write

;------ close file

	mov	dx,fcbxxx
	mov	cl,16			;close file
	int	0e0h

	cmp	al,3			;return code 0...3?
	jbe	r0850			;OK

	mov	dx,offset m027		;close error
	mov	cl,9			;display text
	int	0e0h			
	jmp	r0825			;try to clean up

;------ set file to read-only

r0850:
	mov	bx,fcbxxx
	or	byte ptr [bx+9],80h	;set read-only attribute T1
	mov	dx,bx
	mov	cl,30			;set file attributes
	int	0e0h

	cmp	al,0			;OK?
	jz	r0860			;yes

	mov	dx,offset m032		;no
	mov	cl,9			;display text
	int	0e0h

;------ restore original user number

r0860:
	mov	dl,curuser		;original user number
	mov	cl,32			;set/get user code
	int	0e0h

ENDIF
;-------------- end of program ----------------------------------------

	call	drvreset		;PC-ROM-BIOS reset diskette drive

	mov	dx,offset m009		;diskette prepared successfully

IF DOS
	mov	ah,9			;display text
	int	21h

	mov	ax,4c00h		;stop run
	int	21h
ELSE
	mov	cl,9			;display text
	int	0e0h

stoprun2:

	call	rest1e			;restore diskette parameter table

	mov	cl,13			;logically reset all CP/M-86 drives
	int	0e0h

	mov	cl,14			;select disk
	mov	dl,curdsk
	int	0e0h

	mov	ax,0
	mov	es,ax

	mov	ax,word ptr save1b
	mov	es:01bh+01bh+01bh+01bh,ax	;restore
	mov	ax,word ptr save1b+2		; old
	mov	es:01bh+01bh+01bh+01bh+2,ax	;  int 1Bh (ctrl-break handler)

	push	cs
	pop	es

stoprun:
	mov	cl,0			;return to CCP
	mov	dl,0			;free all our memory, including the
	int	0e0h			; 18 KB double track buffer
ENDIF

;-------------- report a diskette write or read error ----------------------

r0700:
	push	ds
	pop	es

	mov	w_error,ah	;INT 13h returned an error code in AH
	mov	w_sect,al	;# sectors read/written

	mov	al,ah		;error code
	mov	si,offset m101d
	call	b2hex

	pop	dx		;discard old ES-value

	pop	dx		;restore DX

	mov	al,dh		;head
	mov	si,offset m101b
	call	b2hex

	pop	cx		;restore CX

	add	cl,w_sect	;starting sector + sectors read/written
				; = sector in error (well, most of the time...)

	cmp	cl,n_sect	;sector number never larger
	jbe	r0705		; than max. sector number
	dec	cl
r0705:
	mov	al,cl
	mov	si,offset m101c
	call	b2hex

	mov	al,ch		;cylinder
	mov	si,offset m101a
	call	b2hex
	
	pop	bx		;restore BX

	mov	byte ptr m101x,'2'	;change message number to M102
	mov	word ptr m101y,'er'	;set text to "reading"
	mov	word ptr m101y+2,'da'

	pop	ax		;restore AX

	cmp	ah,3		;command in AH: was it write?
	jne	r0709		;no

	mov	byte ptr m101x,'1'	;change message number to M101
	mov	word ptr m101y,'rw'	;set text to "writing"
	mov	word ptr m101y+2,'ti'

r0709:
	mov	dx,offset m101
IF DOS
	mov	ah,9		;display text
	int	21h
ELSE
	mov	cl,9		;display text
	int	0e0h
ENDIF

;Load an appropriate error message. 
;This code is not very elegant, but it works. 

	mov	dx,offset m201
	cmp	w_error,1
	jne	$+5 
	jmp	r0710
	mov	dx,offset m202
	cmp	w_error,2
	jne	$+5
	jmp	r0710
	mov	dx,offset m203
	cmp	w_error,3
	jne	$+5
	jmp	r0710
	mov	dx,offset m204
	cmp	w_error,4
	jne	$+5 
	jmp	r0710
	mov	dx,offset m205
	cmp	w_error,5
	jne	$+5 
	jmp	r0710
	mov	dx,offset m206
	cmp	w_error,6
	jne	$+5 
	jmp	r0710
	mov	dx,offset m207
	cmp	w_error,7
	jne	$+5 
	jmp	r0710
	mov	dx,offset m208
	cmp	w_error,8
	jne	$+5 
	jmp	r0710

	mov	dx,offset m209
	cmp	w_error,9
	jne	$+5 
	jmp	r0710
	mov	dx,offset m20a
	cmp	w_error,0ah
	jne	$+5 
	jmp	r0710
	mov	dx,offset m20b
	cmp	w_error,0bh
	jne	$+5 
	jmp	r0710
	mov	dx,offset m20c
	cmp	w_error,0ch
	jne	$+5 
	jmp	r0710
	mov	dx,offset m20d
	cmp	w_error,0dh
	jne	$+5 
	jmp	r0710
	mov	dx,offset m20e
	cmp	w_error,0eh
	jne	$+5 
	jmp	r0710
	mov	dx,offset m20f
	cmp	w_error,0fh
	jne	$+5 
	jmp	r0710

	mov	dx,offset m210
	cmp	w_error,10h
	jne	$+5 
	jmp	r0710
	mov	dx,offset m211
	cmp	w_error,11h
	jne	$+5 
	jmp	r0710
	mov	dx,offset m220
	cmp	w_error,20h
	jne	$+5 
	jmp	r0710
	mov	dx,offset m240
	cmp	w_error,40h
	jne	$+5 
	jmp	r0710
	mov	dx,offset m280
	cmp	w_error,80h
	jne	$+5 
	jmp	r0710

	mov	dx,offset m2bb
	cmp	w_error,0bbh
	jne	$+5 
	jmp	r0710
	mov	dx,offset m2cc
	cmp	w_error,0cch
	jne	$+5 
	jmp	r0710
	mov	dx,offset m2e0
	cmp	w_error,0e0h
	jne	$+5 
	jmp	r0710
	mov	dx,offset m2ff
	cmp	w_error,0ffh
	jne	$+5 
	jmp	r0710

	mov	dx,offset m2zz	;unknown error code
r0710:

IF DOS
	mov	ah,9		;display text
	int	21h
ELSE
	mov	cl,9		;display text
	int	0e0h
ENDIF

	call	drvreset	;PC-ROM-BIOS reset diskette drive

	mov	dx,offset m010	;preparation failed
IF DOS
	mov	ah,9		;display text
	int	21h

	mov	ax,4c99h	;stop run
	int	21h
ELSE
	mov	cl,9		;display text
	int	0e0h

	jmp	stoprun2
ENDIF

;-------------- report stack usage --------------------------------

IF CPM
rptstak:
	push	cs
	pop	es			;scan memory at es:di

	mov	di,offset endstak

	cld
	mov	ax,'hf'			;scan for word 'fh'
	mov	cx,STAKSIZ		;scan max. STAKSIZ words
	repe	scasw		

	mov	ax,cx			;stack usage in words
	add	ax,cx			;stack usage in bytes	
	mov	si,offset m017a		;print AX in hex
	call	w2hex
	
	mov	cl,9			;print stack usage
	mov	dx,offset m017
	int	0e0h

	ret
ENDIF

;-------------- format the contents of MCB18K into M016 -----------

IF CPM
fmtmcb:
	push	ax
	push	si

	mov	ax,mcbase		;M-Base
	mov	si,offset m016a
	call	w2hex
	
	mov	ax,mcblen		;M-Length
	mov	si,offset m016b
	call	w2hex
	
	mov	al,mcbext		;M-Ext
	mov	si,offset m016c
	call	b2hex

	pop	si
	pop	ax

	ret
ENDIF

;-------------- restore original contents of interrupt vector 1Eh -----

IF CPM

rest1e:
	mov	ax,0
	mov	es,ax			;ES := 0

	mov	ax,word ptr save1e
	mov	es:01eh+01eh+01eh+01eh,ax	;restore
	mov	ax,word ptr save1e+2		; old
	mov	es:01eh+01eh+01eh+01eh+2,ax	;  int 1Eh (diskette parms)

	push	cs
	pop	es

rest199:
	retn

ENDIF

;-------------- convert word in AX to decimal string at [SI] ----------

;Repeat dividing by 10 and pushing remainder on stack, until quotient is zero.

w2dec:
	push	ax
	push	cx
	push	dx
	call	w2dec10
	pop	dx
	pop	cx
	pop	ax

	ret

w2dec10:
	mov	cx,10			;divisor
	mov	dx,0			;high word of dividend

	div	cx			;AX := (DX:AX)/CX; DX := remainder
	cmp	ax,0			;is the quotient/result zero?
	jz	w2dec20			;yes

	push	dx			;put remainder on stack
	call	w2dec10			;recursively divide by 10
	pop	dx			;get remainder from stack

w2dec20:
	add	dl,'0'			;transform remainder to ASCII
	mov	[si],dl			;store ASCII digit
	inc	si

	ret

;-------------- convert word in AX to hexadecimal string at [SI] ------

w2hex:
	push	ax

	mov	al,ah
	call	b2hex		;convert AH

	pop	ax
				;fall through to convert AL

;-------------- convert byte in AL to hexadecimal string at [SI] ------

b2hex:
	push	ax
	shr	al,1
	shr	al,1
	shr	al,1
	shr	al,1
	call	n2hex		;convert high nibble of AL
	pop	ax
	and	al,0fh
				;fall through to convert low nibble of AL

;-------------- convert lower nibble of AL to hexadecimal string at [SI]

n2hex:
	add	al,090h
	daa
	adc	al,040h
	daa
	mov	[si],al		;store hexadecinal  digit
	inc	si

	ret

;-------------- reset diskette drive through PC ROM BIOS --------------

drvreset:

	mov	ah,0
	mov	dl,w_drive	;drive 1 or 2 from FCB
	dec	dl		;make drive 0 or 1 for INT 13h

	int	13h		;reset drive

	ret

;-------------- check command line option character in AL -------------

chkopt:
	push	bx

	cmp	al,' '		;blank?
	je	chkop99		;yes, ignore it, return

	cmp	al,'a'
	jb	chkop02
	cmp	al,'z'
	ja	chkop02
	sub	al,'a'-'A'	;make uppercase

chkop02:
	cmp	al,'3'		;test 1.2 MB format on 3.5 inch media?
	jne	chkop05
	mov	w_3inch,1
	jmp	chkop99

chkop05:
	cmp	al,'V'		;verbose option?
	jne	chkop10		;no
	mov	w_verb,1	;yes
	jmp	chkop99		;return

chkop10:
	cmp	al,'Q'		;quick option?
	jne	chkop20		;no
	mov	w_quick,1	;yes
	jmp	chkop99		;return

chkop20:
	cmp	al,'7'		;720 KB option?
	jne	chkop30		;no
				;yes
	cmp	w_12m,0		;1.2 MB option used before?
	je	chkop25		;no
	mov	dx,offset m013
	mov	m013a,'7'	;yes, ignore
	jmp	chkop95		; 720 KB option
chkop25:
	mov	w_720,1		;720 KB option OK
	jmp	chkop99		;return

chkop30:
	cmp	al,'1'		;1.2 MB option?
	jne	chkop90		;no
				;yes
	cmp	w_720,0		;720 KB option used before?
	je	chkop35		;no

	mov	dx,offset m013
	mov	m013a,'1'	;yes, ignore
	jmp	chkop95		; 1.2 MB option
chkop35:
	mov	w_12m,1		;1.2 MB option OK
	jmp	chkop99		;return

chkop90:
	mov	m012a,al	;report an invalid option

	mov	dx,offset m012

chkop95:
IF DOS
	mov	ah,9		;display text
	int	21h
ELSE
	mov	cl,9		;display text
	int	0e0h
ENDIF

chkop99:
	pop	bx

	ret

;-------------- build timestamps from current time & date -------------

;16 bits time stamp       : Hours * 2048 + Minutes * 32 + Seconds / 2
;for DOS directory
;
;individual bits          :   15...11       10...5        4...0
;for DOS directory
;
;results from INT 21h/2Ch : Hours = CH     Minutes = CL   Seconds = DH

stamp:

IF DOS
	mov	ah,2ch		;get system time into CH, CL and DH
	int	21h
ELSE
	mov	cl,49		;get A(system parameters) into ES:BX
	int	0e0h

;------ transform CP/M-86 time results to DOS 21h time results in CH, CL and DH

;AAD: if ax equals 0204 , after an aad ax will be 0018, which is 24 decimaal

	mov	ax,es:[bx][syshh]	;AL:=tens, AH:=units
	mov	word ptr m009hh,ax
	xchg	al,ah			;AL:=units, AH:=tens
	sub	ax,'00'			;make BCD
	aad				;make binary
	and	al,1fh			;reduce to a 5 bit value
	mov	ch,al			;hours

	mov	ax,es:[bx][sysmm]	;AL:=tens, AH:=units
	mov	word ptr m009mm,ax
	xchg	al,ah			;AL:=units, AH:=tens
	sub	ax,'00'			;make BCD
	aad				;make binary
	and	al,1fh			;reduce to a 6 bit value
	mov	cl,al			;minutes

	mov	ax,es:[bx][sysss]	;AL:=tens, AH:=units
	mov	word ptr m009ss,ax
	xchg	al,ah			;AL:=units, AH:=tens
	sub	ax,'00'			;make BCD
	aad				;make binary
	shr	ax,1			;AX:=AX/2
	and	al,1fh			;reduce to a 5 bit value
	mov	dh,al			;seconds/2

	push	cs
	pop	es
ENDIF

	mov	bx,cx		;save in BX, we'll need CX for shift counts

	mov	ax,0		;initialize result field to zero

	mov	al,bh		;add hour

	mov	cl,6		;move hour
	shl	ax,cl		; to bits 10...6

	or	al,bl		;add minutes

	mov	cl,5		;move hour and minutes
	shl	ax,cl		; to bits 15...5

	shr	dh,1		;seconds / 2

	or	al,dh		;add seconds / 2

	mov	deTime,ax	;put time into directory for volume label
	mov	word ptr volid,ax	;put time into boot sector volume ID

	mov	si,offset m009a
	call	w2hex

;get the current date, to time stamp the DOS volume label

;16 bits date stamp       :  (Year - 1980) * 512 + Month * 32 + Day
;for DOS directory
;
;individual bits          :    15...9              8...5        4...0
;for DOS directory
;
;results from INT 21h/2Ah :   Year = CX            Month = DH   Day = DL

IF DOS
	mov	ah,2ah		;get system date (year = CX = 1980...2099)
	int	21h
ELSE
	mov	cl,49
	int	0e0h

;------ transform CP/M-86 date results to DOS 21h date results in CX, DH and DL

	mov	ax,es:[bx][sysyy]	;AL:=tens, AH:=units
	mov	word ptr m009yy,ax
	xchg	al,ah			;AL:=units, AH:=tens
	sub	ax,'00'			;make BCD
	aad				;make binary
	and	ax,7fh			;reduce to a 7 bit value
	mov	cx,ax			;year 00...99

;Y2K stuff: assume 21st century if 00 <= year <= 79
;           assume 20th century if 80 <= year <= 99

	add	cx,1900			;make 1900...1999
	mov	word ptr m009cc,'91'

	cmp	cx,1980			;1980...1999?
	jae	stamp10			;yes, done

	add	cx,100			;no, transform from 1900...1979
	mov	word ptr m009cc,'02'	;    to 2000...2079
stamp10:

	mov	ax,es:[bx][sysmo]	;AL:=tens, AH:=units
	mov	word ptr m009mo,ax
	xchg	al,ah			;AL:=units, AH:=tens
	sub	ax,'00'			;make BCD
	aad				;make binary
	and	ax,0fh			;reduce to a 4 bit value
	mov	dh,al			;month

	mov	ax,es:[bx][sysdd]	;AL:=tens, AH:=units
	mov	word ptr m009dd,ax
	xchg	al,ah			;AL:=units, AH:=tens
	sub	ax,'00'			;make BCD
	aad				;make binary
	and	ax,1fh			;reduce to a 5 bit value
	mov	dl,al			;day

	push	cs
	pop	es
ENDIF

	mov	ax,cx		;year (DOS: 1980...2099, CPM: 1980...2079)
	sub	ax,1980		; minus 1980
	jge	stamp02		;signed comparison: jump if AX >= zero
	mov	ax,0
stamp02:

	mov	cl,4		;move year
	shl	ax,cl		; to bits 11...5

	or	al,dh		;add month

	mov	cl,5		;move year and month
	shl	ax,cl		; to bits 15...5

	or	al,dl		;add day

	mov	deDate,ax	;put date into directory for volume label
	mov	word ptr volid+2,ax	;put date into boot sector volume ID

	mov	si,offset m009b
	call	w2hex

	ret

;------- hit ENTER to continue or ctrl-C to stop ----------------------

getenter:

IF DOS
	mov	ah,8			;console character input without echo
	int	21h			;(control-c will abort this program)
ELSE
	mov	dl,0ffh			;console input
	mov	cl,6			;direct console I/O
	int	0e0h

	cmp	al,3			;control-c?
	jne	getent10		;no
	jmp	stoprun			;yes, end program
getent10:

ENDIF

	cmp	al,0dh			;enter?
	je	getent99		;yes, done

IF DOS
	cmp	al,0			;extended key?
	jnz	getenter		;no, retry

	mov	ah,8			;yes, eat the
	int	21h			; extended code
ENDIF

	jmp	getenter		;retry...

getent99:
	ret

;------
;control-break handler (interrupt 1Bh)

IF CPM
int1b:
	iret			;just ignore control-break
ENDIF

;-------------- DOS FAT -----------------------------------------------
;written to track 0, head 0, sectors 3 and 4

fat12start:

	db	0FEh			;media byte (same as in boot sector)
	db	0ffh,0ffh		;plus filler bytes (= fat entries 0+1)

;The 12-bit FAT entry for "bad sector in cluster" is ff7, i.e. bytes f7 and 0f
;for even fat entries. For uneven fat entry numbers it is 70 ff.
;The combination of two 12-bit entries, starting with an even fat entry
;number,  gives three bytes: f7 7f ff.

;A standard 160 KB DOS disk holds 313 clusters.
;This "simulated" 160 KB disk has 315 clusters:
;- three additional clusters as the directory occupies only one sector
;  instead of four sectors
;- but there is one extra reserved sector, for the CP/M-86 system parameters.
;- so 313 + 3 - 1 equals 315.

	db	157 dup (0f7h,07fh,0ffh)	;12 fat bits for 314 clusters
						;(fat entries 2...315)
	db	0f7h,0fh 			;315th is the last cluster
						;(fat entry 316)
	db	39 dup(0)			;filler

;-------------- DOS directory -----------------------------------------
;written to track 0, head 0, sector 5

dosdirstart:

					;start of DOS DIRENTRY structure

deName		db	'CPM-86-D'	;DOS doesn't like slashes...
deExtension	db	'ISK'
ATTR_READONLY	equ	01h
ATTR_HIDDEN	equ	02h
ATTR_SYSTEM	equ	04h
ATTR_VOLUME	equ	08h
ATTR_DIRECTORY	equ	10h
ATTR_ARCHIVE	equ	20h
ATTR_BIT6	equ	40h
ATTR_BIT7	equ	80H
deAttributes	db	ATTR_ARCHIVE + ATTR_VOLUME
deReserved	db	10 dup(0)	;OS/2: address of extended attributes
deTime		dw	?
deDate		dw	?
deStartCluster	dw	?
deFileSize	dd	?
					;end of DOS DIRENTRY structure

;15 empty directory entries, 32 bytes each

		db	480 dup(0)	;15 * 32

;-------------- skeleton for CP/M-86 directory entry ------------------
;written to track 1, head 0, sector 1

cpmdirstart:

UU		db	0		;user number
FN		db	'CP/M-86 '	;file name
FT		db	'1' + 80h	;file type; write-protect bit is on
		db	'4'		;file type
		db	'4'		;file type
EX		db	0		;low byte extent counter (0...9)
S1		db	0		;reserved
S2		db	0		;high byte extent counter (0)
RC		db	80h		;record count for this extent:
					;80h = extent is full

ALL		db	2,3,4,5		;block numbers allocated to this file
		db	6,7,8,9		;(2...155 on 160 KB media)
		db	10,11,12,13	;last directory record has 92...9B
		db	14,15,16,17	; plus six zero bytes
		
;-------------- end of program ----------------------------------------

		db	'<<<<144PREP2<<<<'
		align	128

;============== 512 bytes boot sector code will be appended here ======

bootstart	equ	$

pvbackup	equ	bootstart + 3		;text: "PVBACKUP"
volid		equ	bootstart + 504		;dword: volume ID
cpmedia		equ	bootstart + 511		;CP/M-86 media byte

;============== secondary boot loader program will be appended here ===

x44bldr2	equ	bootstart + 512
x44code2	equ	x44bldr2  + 384		;128 bytes CMD header,
						; and 256 bytes "PSP"

x44tag		equ	x44code2 + 2		;text: "BLDR"
x44flag		equ	x44code2 + 6
x44size		equ	x44code2 + 7		;word: size of BLDR program


;============== CPM.SYS might be appended here ========================

;To verify the presence of CPM.SYS, we might check at offset 8Bh for 16 blanks,
;followed by the text "COPYRIGHT (C) 1980, DIGITAL RESEARCH", followed by two
;blanks.
;The size of CPM.SYS, in 16-byte paragraphs, could be found in the word at
;offset 1.

;Then, if an image of CPM.SYS was found, we might write a CPM.SYS file
;onto the freshly prepared diskette.

;Maybe we'll implement this in the next version of the "1.44 MB Feature".

;============== standard MASM 5.1 epilog for a .COM file ==============

prep2		ends
	end	$fbegin
