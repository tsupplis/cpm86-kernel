	page ,132
DOSTEST	equ	0		;0 = run program from boot sector at boot time
				;1 = run program from DOS prompt

;======================================================================

; 144BOOT2.ASM - initial release

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

;This is 144BOOT, the boot sector program to read (the first 4 KB of) the
;secondary boot loader program 144BLDR2.CMD, from a 720 KB, 1.2 Mb or 1.44 MB
;CP/M-86 diskette.

;Limitations:
;- 144BLDR2.CMD must not be greater than 16 KB (16384 bytes) on 1.2 and 1.44
;  MB diskettes. Otherwise, 144BLDR2.CMD will not be found in the directory.
;  This is because we do not consider the EXM from the DPB when scanning the
;  directory. On 720 KB, EXM is zero so this not an issue.

;Requirements:
;- The PC must have at least 128 KB of memory (not checked here, but in the
;  secondary boot loader).
;- the 144BLDR2.CMD file must have user number zero; it can have system and
;  read-only attributes.
;- the 144BLDR2.CMD file must be a standard CP/M-86 CMD file using the "8080
;  memory model" (somewhat similar to the COM executable file format in DOS).

;------

;The boot sector program will set ES to the "top of ram" as returned by
;INT 12h, minus 26 KB. This 26 KB is used as follows:
;
;- ES:0...FF      256 bytes: PSP (zero page) of the boot loader program file
;- ES:100...F7F   the first 4-KB-minus-384 bytes of the boot loader program
;- ES:F80...FFF   128 bytes not used
;- ES:1000...33FF buffer for a full track of data (max. 9 KB on 1.44 MB disk)
;- ES:3400...53FF the full 8 KB directory of the 720 KB/1.2 MB/1.44 MB diskette
;- ES:5400...63FF 4 KB work space, for reading the first 2 or 4 KB of CPM.SYS
;- ES:6400...67FF 1 KB for local stack during execution of boot loader program

espsp	equ	0
esbldr	equ	100h
estrkbf	equ	1000h
esdirbf	equ	3400h
eswrk	equ	5400h
eswrknd	equ	6400h
estack	equ	6400h+400h

;The top of RAM as returned by INT 12h is ES:67FF plus 1, is ES:6800.

;============== standard MASM 5.1 prolog for a COM file ===============

x144boot	segment para public 'code'
		assume	cs:x144boot
		assume	ds:x144boot
		assume	es:nothing

		org	100h
r0000:

;============== start of transient program ============================

				;runtime location (initial IP): 7C00h
				;initial SS: 0
				;initial SP: 03Ex...03Fx (machine dependent)

;The first part of the program is a more or less standard DOS boot sector

	jmp	short r0010	;either a short jump plus a nop, or a near jump
	nop

	db	'PVBACKUP'	;signature, don't let win9x touch this disk

L7C0B	equ	$		;diskette parameters

	dw	512		;number of bytes per sector
	db	1		;number of sectors per cluster
L7C0E	dw	1+1		;number of reserved sectors (original: 1)
	db	2		;number of fats
	dw	16		;number of directory entries (original: 64)
	dw	320		;number of sectors on disk
	db	0feh		;media byte
	dw	1		;number of sectors per fat
	dw	8		;number of sectors per track
	dw	1		;number of heads per cylinder
	dw	0		;number of hidden sectors

	db	0,0,0,0,0,0,0,0,0

;------ working storage

track	db	255			;number of CP/M-86 track currently in
					; track buffer estrkbf (0...159)

spt	db	18			;number of physical sectors per track
					; (9/15/18 for 720KB/1.2MB/1.44MB)

bls	dw	4096			;size of a CP/M-86 data block:
					; 2048 for 720 KB, 4096 for 1.2/1.44 MB

spb	dw	8			;physical sectors per CP/M data block:
					; 4 for 720 KB, 8 for 1.2/1.44 MB

;------ set SS, SP, DS

r0010:
	cli
	mov	sp,cs
	mov	ss,sp			;use a local stack, top of
	mov	sp,07c00h		; stack is 0:7C00
	sti

IF DOSTEST
	push	cs
	pop	ds
ELSE
	mov	ax,cs
	add	ax,07B0h		;makes our data items, ORG-ed at 100h,
	mov	ds,ax			; accessable at run-time offset 7C00h
ENDIF

;------ get amount of RAM; ES := segment address of 26 KB work area

	int	12h			;AX := KB's of real memory
					;typical 638...640 = 27Eh...280h
	
	sub	ax,26			;reserve 26 KB for boot loader, track
					;buffer, full directory and local stack

	mov	cl,6			;from kilobytes (2^10)
	shl	ax,cl			; to paragraphs (2^4)

	mov	es,ax			;segment of reserved 26 KB

	mov	[r0210],ax		;setup segment value for far jump to
					; secondary boot loader program
	
;------ setup some media-dependent values

;	mov	[spt],18		;initial value of [spt] is 18
;	mov	[spb],8			;initial value of [spb] is 8
;	mov	[bls],4096		;initial value of block size = 4096
	mov	cx,2			;number of directory blocks = 2

	mov	al,byte ptr [cpmedia]
	cmp	al,144			;1.44 MB?
	je	r0020			;yes
;
	shr	[spt],1			;sectors per track = 9
	shr	[spb],1			;sectors per block = 4
	shr	[bls],1			;block size = 2048
	shl	cx,1			;number of directory blocks = 4

	cmp	al,72			;720 KB?
	je	r0020			;yes
;
	mov	al,15
	mov	[spt],al		;sectors per track = 15
	shl	[spb],1			;sectors per block = 8
	shl	[bls],1			;block size = 4096
	shr	cx,1			;number of directory blocks = 2

;	mov	byte ptr [dpt35+4],al	;adjust DPT so it will be correct for
;	mov	byte ptr [dpt35+7],054h	; 1.2 MB on 5.25 inch media
r0020:

;------ set interrupt 1Eh to our diskette parameter table (DPT)
;
;	push	ds
;	xor	ax,ax
;	mov	ds,ax			;DS := 0
;
;	mov	ds:01eh+01eh+01eh+01eh,offset dpt35	;setup new table
;	mov	ds:01eh+01eh+01eh+01eh+2,cs		;at INT 1Eh
;
;	pop	ds

;------ reset diskette drive

	xor	ax,ax			;AH = 0: reset disks
	xor	dx,dx			;DL = drive

	int	13h

;------ loading ...

	mov	si,offset m100
	call	dspmsg

;------ read the full 8 KB directory into ES:esdirbf
;
;	4 KB data blocks 0...1 on 1.2 and 1.44 MB
;	or
;	2 KB data blocks 0...3 on 720 KB

	mov	di,offset esdirbf	;read into buffer at ES:DI

	xor	ax,ax			;first block number to be read,
					; the number of blocks to read is in CX
r0022a:
	push	ax
	push	cx
	call	readblk
	pop	cx
	pop	ax

	inc	ax			;prepare for next block number
	loop	r0022a			;jump if more blocks to read

;------ Scan the directory at ES:esdirbf...esdirbf+2000h for the first or only
;	directory record of the boot loader file 144BLDR2.CMD.
;
;       Note: we assume the file is not using multiple directory entries
;       (directory extents).

r0030:
	mov	al,0			;scan 256 directory entries
	mov	di,esdirbf		;start of buffer for directory sectors
r0035:

	and	word ptr es:[di+9],07f7fh	;clear r/o and sys bits
	and	byte ptr es:[di+11],07fh	;clear arc bit (CP/M Plus only)

	mov	si,offset dsn1
	mov	cx,1+8+3+1		;user number: 1 byte
					;file name: 8 bytes
					;file type: 3 bytes
					;directory extent sequence#: 1 byte
	cld
	rep	cmpsb
	jz	r0100			;jump if found
r0050:
	and	di,0ffe0h		;make lower five bits zero, 
	add	di,32			; increment to next directory entry,
					; assuming buffer on a 32-byte boundary

	dec	al			;decrement entry counter
	jnz	r0035			;jump if more entries to check

	mov	si,offset m103		;boot loader file not found
	jmp	dsperr

;------ the boot loader file has been found, now read its first 4 KB of data.
;
;       The first block number of the file is in ES: [DI+3...4] (a 16 bit value
;	on 720 KB, 1.2 MB and 1.44 MB diskettes).
;       On 720 KB only, a block is 2 KB so we will read two data blocks.

r0100:
	inc	[m101a]			;turn message M101 into message M102

	push	es:[di+5]		;save number of 2nd data block (only
					;needed on 720 KB media)

	mov	ax,es:[di+3]		;first data block of boot loader file
	xor	di,di			;target offset within ES

	call	readblk

	pop	ax			;second data block of boot loader file

	cmp	[cpmedia],72		;720 KB media?
	jne	r0100a			;no, done

	or	ax,ax			;number of 2nd data block is zero?
	jz	r0100a			;yes, done

	call	readblk
r0100a:
	mov	si,offset msgok
	call	dspmsg

;------ Move the boot loader program 128 bytes (= the size of the CMD header)
;	down, so its first instruction will end up at offset 100h within its
;	intended code segment.
;
;	As the boot loader program is written in the 8080 model (similar to
;	the COM format in DOS), its IP must be 100h.

	mov	ax,word ptr [cpmedia-1]	;version and media bytes,
					; do this before changing DS
	mov	bl,[track]		;track currently in buffer
					; do this before changing DS
	push	es
	pop	ds

	mov	si,128
	xor	di,di
	mov	cx,4096-128

	cld
	rep	movsb

;------ set the magic words so the secondary boot loader program will know
;	that is has not been started from the CP/M-86 command line

	mov	cx,'GK'
	mov	dx,'DB'

;------ Jump far to the boot loader file's first instruction. 
;       This instruction is now in memory at ES:100.

;Registers and parameters passed to the secondary boot loader program:
;
;- AH = the media byte of the boot diskette (12/72/144)
;- AL = the version of the program that prepared the boot diskette
;
;- BL = number of the track currently in track buffer estrkbf
;- CX = magic word 'GK'
;- DX = magic word 'DB'
;
;- CS = ES (see below)
;- IP = 100h

;This boot sector program has set ES to the "top of ram" as returned by
;INT 12h, minus 26 KB. This 26 KB is used as follows:
;
;- ES:0...FF      256 bytes: PSP of the boot loader program file
;- ES:180...F7F   the first 4-KB-minus-384 bytes of the boot loader program
;- ES:F80...FFF   128 bytes not used
;- ES:1000...33FF buffer for a full track of data (max. 9 KB on 1.44 MB disk)
;- ES:3400...53FF the full 8 KB directory of the 720 KB/1.2 MB/1.44 MB diskette
;- ES:5400...63FF 4 KB work space
;- ES:6400...67FF 1 KB for local stack during execution of boot loader program

;	jmp	far ptr ES:100
	db	0eah
	dw	0100h			; IP value for 8080 model
r0210	dw	?			;  segment of buffer


;------ Subroutine to read CP/M-86 data block [AX] from diskette into ES:DI
;
;Input: AX = CP/M-86 data block number 0...354 (= maximum value, for 1.44 MB)
;       ES:DI = where to put the data

readblk:

	mov	cx,[spb]
	mul	cx			;AX := first sector of data block
					; (zero-based nunber)

	div	byte ptr [spt]		;divide AX by sectors-per-track
					; AL := track 0...159
					; AH := sector 0...17 (zero-based)

	add	al,2			;add 2 reserved tracks (OFF from DPB),
					; giving track number 2...159

;now read 4 or 8 (720 KB or 1.2/1.44 MB) consecutive sectors, starting with
;the track AL and the sector AH we just have calculated

readb20:
	push	cx			;counter for number of sectors

	cmp	al,[track]		;track already present in track buffer?
	jz	readb40			;yes, skip the physical I/O

	mov	[track],al		;new track in buffer

;read all sectors on the track into the full track buffer

	call	int13

;move data from the full track buffer to our "DMA area" at ES:DI

readb40:

	mov	bh,ah			;sector number 0...8/14/17
	mov	bl,0			;clear low byte
					;BX := sector * 256
					
	shl	bx,1			;BX := sector * 512
	mov	si,bx
	add	si,estrkbf

	push	ds

	push	es
	pop	ds			;DS := ES

	mov	cx,256			;move 256 words
	cld
	rep	movsw			;nove from full track buffer to "DMA"

	pop	ds

	push	ax
	mov	si,offset msgdot	;progress indicator
	call	dspmsg
	pop	ax

;prepare for next sector

	inc	ah			;next sector

	cmp	ah,[spt]		;exceeding sectors per track?
	jb	readb50			;no

	mov	ah,0			;yes, set sector 0
	inc	al			;set next track 

readb50:
	pop	cx
	loop	readb20			;jump if more sectors to read

	ret

;------ read all sectors on track AL with INT 13h into the buffer at ES:estrkbf

int13:
	mov	si,5			;retry count

int1302:
	push	ax			;save the track in AL

;calculate head and track for INT 13h from CP/M-86's track number:
;if track number in AL >= 80 then AL := (159 - AL) and head := 1

	xor	dx,dx			;DH := 0, assume head 0

	cmp	al,80			;track 80 or higher?
	jb	int1305			;no, done

	sub	al,159			;yes, subtract 159
	neg	al			;make two's complement

	inc	dh			;head := 1
int1305:

	mov	ch,al			;CH := track for INT 13h

	mov	bx,estrkbf		;offset of track buffer (segment = ES)
	mov	cl,1			;CL := starting sector
					;DL already = 0 = drive A:

int1310:
	mov	al,[spt]		;AL := number of sectors,
	mov	ah,2			;AH := 2 =read

	int	13h

	pop	ax
	jnc	int1399			;jump if no error

	dec	si			;error; give it another try?
	jnz	int1302			;yes

	mov	si,offset m101		;display I/O error
	jmp	short dsperr

int1399:
	retn

;------ display ASCII$ message at DS:SI on the console ----------------

dsperr:
	call	dspmsg

IF DOSTEST
	mov	ax,4cffh
	int	21h
ELSE
	jmp	short $			;loop forever
ENDIF

dspmsg:
	cld
	lodsb				;get a character from the string

	cmp	al,'$'			;string terminator?
	jz	dspm99			;yes, done

	mov	ah,0eh			;write in TTY mode
	xor	bx,bx			;BH=0=page BL=0=color
	int	10h

	jmp	short dspmsg		;next character
dspm99:
	ret

;------ error messages

msgdot	db	'.$'

msgok	db	'OK$'

m100	db	'Loading 144BLDR2.CMD$'

m101	db	0dh,0ah
	db	'M10'
m101a	db	'1'			;m101 = error when reading directory
					;m102 = error when reading boot loader
	db	' - Error reading diskette$'

m103	db	0dh,0ah
	db	'M103 - Cannot find 144BLDR2.CMD$'

dsn1	db	0			;user number = 0
	db	'144BLDR2'		;file name
	db	'CMD'			;file type
	db	0			;directory extent sequence# = 0

;------ DPT's for 3.5 inch diskettes (values taken from MS-DOS 6.2)
;       and for 1.2 MB capacity on 5.25 inch diskette (values taken from 
;	the magazine C'T, 02/1990)
;
;dpt35:	db	0dfh,002h,025h,002h,012h,01bh,0ffh,06ch,0f6h,00fh,008h
;                                    **             **       
;dpt12:	db	0dfh,002h,025h,002h,00fh,01bh,0ffh,054h,0f6h,00fh,008h

;------ check & adjust current location counter

hier	equ	$

IF (hier - r0000) gt 01f0h
	.err  144BOOT2.ASM: Bootcode is longer than 01F0h bytes.
ENDIF

	org	02f0h

;------ fields reserved by the 1.44 MB Feature for CP/M-86

	dd	0,0		;tgb

volid	dd	0		;maybe we'll use this in the 1.44 MB Feature

	db	0
	db	0		;boot drive: 00=diskette 80h...81h=harddisk

	db	1		;version of program that prepared this diskette

cpmedia	db	144		;CP/M-86 "media byte" at offset 01ffh
				;72 for 720 KB, 144 for 1.44 MB, 12 for 1.2 MB

;============== standard MASM 5.1 epilog for a COM file ===============

x144boot	ends

	end	r0000
