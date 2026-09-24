	page ,132

;======================================================================

; 144BLDR2.ASM - initial release

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

;This is 144BLDR, the secondary boot loader program for CP/M-86 version 1.1
;
;It is loaded into memory by its partner program, the boot sector program
;144BOOT. Note that only the first <4 KB minus 384> i.e. 3712 bytes
;(hex 0E80 bytes) will be loaded by the boot sector program.
;
;Registers and parameters as passed to 144BLDR by the boot sector code:
;
;- AH = the media byte of the boot diskette (12/72/144)
;- AL = the version of the program that prepared the boot diskette
;
;- CS = DS = ES (see below)
;- IP = 100h
;
;The boot sector program has set ES to the "top of ram" as returned by
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

esize	equ	( estack - espsp ) SHR 10	;size in KB

;The top of RAM as returned by INT 12h is ES:67FF plus 1, is ES:6800.


;============== standard MASM 5.1 prolog for a COM file ===============

x44bldr segment para public 'code'

	assume	cs:x44bldr
	assume	ds:x44bldr
	assume	es:nothing

	org	100h
r0000:

;-------------- start of program --------------------------------------

	jmp	short r0001

x44tag	db	'BLDR'			;signature

x44flag	db	-1			;If 0, then no patches are done to
					; the CPM.SYS image in memory. After
					; loading CPM.SYS into memory, it is
					; immediately cold started.
					; Just in case a new CPM.SYS with 
					; built-in support for higher capacity
					; diskettes shows up...
					; This byte is at offset 182h from the
					; start of the image, use DDT86 or
					; DEBUG to set this flag to 0.

x44size:
	dw	k9999			;Size of this program, intended
					; for the "prepare" program so it knows
					; how much of 144BLDR2.CMD to write to
					; diskette, from an image appended to
					; the "prepare" program-itself.
					; This word is at offset 183h from the
					; start of the image.

;------ check data being passed from the boot sector program

r0001:
	cmp	cx,'GK'			;check first magic word
	je	r0002			;probably started at system boot time
	jmp	k0000			;we're started in a running CP/M system
r0002:
	cmp	dx,'DB'			;check second magic word
	je	r0005			;OK, started at system boot time
	jmp	k0000			;we're started in a running CP/M system
r0005:
	mov	[track],bl		;track currently in buffer estrkbf

;------ set SS, SP

	cli
	mov	sp,cs
	mov	ss,sp			;use a local stack
	mov	sp,estack
	sti

;------ setup some media-dependent values

	xchg	al,ah
	mov	[cpmedia],al

;	mov	[spt],18		;initial value of [spt] is 18
;	mov	[spb],8			;initial value of [spb] is 8
;	mov	[bls],4096		;initial value of block size = 4096
	mov	bx,offset dpt35
	mov	cx,2			;number of directory blocks = 2
	mov	dl,exm144		;extent mask from DPB

	cmp	al,144			;1.44 MB?
	je	r0020			;yes
;
	shr	[spt],1			;sectors per track = 9
	shr	[spb],1			;sectors per block = 4
	shr	[bls],1			;block size = 2048
	shl	cx,1			;number of directory blocks = 4
	mov	dl,exm720		;extent mask from DPB

	cmp	al,72			;720 KB?
	je	r0020			;yes
;
	mov	[spt],15		;sectors per track = 15
	shl	[spb],1			;sectors per block = 8
	shl	[bls],1			;block size = 4096
	mov	bx,offset dpt12
	shr	cx,1			;number of directory blocks = 2
	mov	dl,exm12m		;extent mask from DPB
r0020:
	mov	[exmcurr],dl

;------ set interrupt 1Eh to our diskette parameter table (DPT), as in BX.

	push	ds

	xor	ax,ax
	mov	ds,ax

	mov	ds:01eh+01eh+01eh+01eh,bx	;setup new table
	mov	ds:01eh+01eh+01eh+01eh+2,cs	;at INT 1Eh

	pop	ds

;------ intro
	
	mov	si,offset m200		;loading CPM.SYS
	call	dspmsg

;------ we need 128 KB or more RAM

	int	12h
	cmp	ax,128
	jge	r0010

	mov	si,offset m207
	jmp	dsperr
r0010:

;------ find first directory record for CPM.SYS

r0100:
	call	scan
	jnc	r0199			;jump if found

	mov	si,offset m202		;not found
	jmp	dsperr
r0199:

;------ the CPM.SYS file has been found, now read its first data block
;	(including the CMD header) into the memory buffer at ES:eswrk
;       The first block number of the file is in [DI+16...17];

r0200:
	add	di,16			;DI points to CPM.SYS directory record
	mov	[dirptr],di		;pointer to AL-array in dir. record

	mov	ax,[di]			;number of first data block of CPM.SYS
	cmp	ax,0			;zero block number, i.e. empty file?
	jnz	r0210			;not empty, OK

	mov	m204a,'1'		;empty file, loader error #1
	jmp	r0390
r0210:
	mov	di,eswrk		;start of buffer for header CPM.SYS
	call	readblk			;read 1st data block (2 or 4 KB)
r0299:

;------ check and process the 128 bytes CMD header of CPM.SYS

r0300:
	mov	bx,eswrk		;offset of sector buffer

	mov	si,offset m204b		
	mov	al,[bx]
	call	b2hex

	mov	si,offset m204c
	mov	ax,[bx+1]
	call	w2hex

	mov	si,offset m204d
	mov	ax,[bx+3]
	call	w2hex

	mov	si,offset m204e
	mov	ax,[bx+5]
	call	w2hex

	mov	si,offset m204f
	mov	ax,[bx+7]
	call	w2hex

	mov	si,offset m204g
	mov	al,[bx+9]
	call	b2hex

;	mov	si,offset m204
;	call	dspmsg

	mov	m204a,'2'		;loader error  #2
	cmp	byte ptr [bx],1		;G-form in first descriptor must be 1
	jne	r0390			;jump if no code segment group

	inc	m204a			;loader error #3
	cmp	word ptr [bx+1],0800h	;G-length must be < 2048 paras = 32 KB
	jae	r0390

	inc	m204a			;loader error #4
	cmp	word ptr [bx+5],0800h	;G-min must be < 2048 paras = 32 KB
	jae	r0390

	inc	m204a			;loader error #5
	cmp	byte ptr [bx+9],0	;second descriptor should be empty,
	jnz	r0390			;i.e. there should be only 1 descriptor

	mov	ax,[bx+3]		;A-base in first descriptor,
	mov	[cpmseg],ax		; this will be the CP/M-86 segment

	mov	[r0580],ax		;for far jump to CP/M-86 BIOS init
	mov	[r0910],ax		;for far jump to CP/M-86 CCP/BDOS init
	mov	[our6799],ax		;for far jump to CP/M-86 RAM test proc
	mov	[ourfi99],ax		;for far jump to CP/M-86 FIDD proc

	inc	m204a			;loader error #6
	cmp	ax,51h			;A-base must be > 0051h, just above
	jb	r0390			;PC-ROM-BIOS data areas

	cmp	ax,3051h		;our debugger load address?
	je	r0399			;yes, an A-base of 3051h is OK

	inc	m204a			;loader error #7
	cmp	ax,100h			;A-base must be < 100h (a somewhat
	jb	r0399			;arbitrary limit...)
r0390:
	mov	si,offset m204		;loader error #1...#8
	jmp	dsperr

r0399:					;the CMD header of CPM.SYS looks good

;------ move the first KB's (2 or 4) of CPM.SYS, minus the 128 bytes CMD
;	header, to its final location at cpmseg

r0400:
	mov	es,[cpmseg]		;target segment = the CP/M-86 segment
	xor	di,di			;target offset

					;source segment = DS
	mov	si,eswrk + 128		;source offset

	mov	cx,[bls]		;data block size (2 or 4 KB)
	sub	cx,128			;subtract length of CMD header

	cld
	rep	movsb

;------ read the remaining data blocks of CPM.SYS into storage at [cpmseg]:DI

	mov	[blcount],2		;start with entry 2 in AL-array
r0410:

	add	word ptr [dirptr],2
	mov	si,[dirptr]
	mov	ax,[si]

	cmp	ax,0			;block number is 0?
	jz	r0499			;yes, done

	mov	es,[cpmseg]
	call	readblk

	inc	[blcount]		;go to next element in AL-array
	cmp	[blcount],8		;all 8 entries processed?
	jbe	r0410			;no, not yet

;------ All eight blocks listed in the first directory record have been read.
;       On 1.2 and 1.44 MB media, eight blocks are 32 K, which we consider
;	enough for a regular CPM.SYS file.
;       On 720 KB, eight blocks are 16 KB, definitely not enough for the
;       standard CPM.SYS which is 18.432 bytes. So we will try to find and
;       process a second directory record for CPM.SYS.

	cmp	[cpmedia],72		;720 KB?
	jne	r0499			;no, done

	inc	[dsn1ext]		;look for next directory record

	cmp	[dsn1ext],1
	ja	r0499			;only process directory records 0 and 1
	
	push	di			;save the pointer to where the next
					; data block will be loaded

	push	ds
	pop	es
	call	scan			;find 2nd directory record for CPM.SYS
	mov	ax,di			;save offset of this directory record

	pop	di

	jc	r0499			;2nd directory record not found;
					; apparently a rather small CPM.SYS...
					
	add	ax,14			;let AX point to 2 bytes before the
					; AL-array in the directory record: so
					; 14, not 16, as r0410 adds 2 to dirptr
					; (yes, this is very unelegant coding!)
	mov	[dirptr],ax

	mov	[blcount],1		;start with the first data block in the
	jmp	r0410			; 2nd directory record

r0499:
	mov	si,offset msgok		;end the progress line of dots
	call	dspmsg			; with Ok and a CR/LF

;------ Make some patches to the memory image op the CPM.SYS file
;
;	- patch X: let CP/M-86 return to our code when it has finished
;	  its cold start procedures.
;
;	- patch Y: let CP/M-86 perform a non-destructive RAM test when
;	  setting up a RAM disk. The original test might destroy our code.
;
;	- patch Z: ensure enough FIDD storage will be available for
;	  the 1.44 MB Feature.

r0500:
	jmp	r0510			;jump past patch data

;General layout for a patch, where ? is a single character patch ID:

;------
;off?	equ	nnnnh			;offset within CP/M-86 segment
;old?:					;old code fragment
;	< old code and data >
;new?:					;new code
;	< new code and data >
;
;len?a	equ	new?-old?
;len?b	equ	$-new?
;if	len?a ne len?b
;	.err 144BLDR2.ASM R9000: Old and new lengths for patch #? are not equal
;endif
;------

;------	
;Patch W: subroutine bios_fidd, page 27

;Here, the BIOS allocates memory for FIDDS.

;The patch makes the CP/M-86 BIOS jump to label ourfid in this program, where
;we will mess around a little bit with the amount of FIDD storage.

offw		equ	03E89h		;offset within CP/M-86 segment

fidd_size_kb	equ	03AC0h		;FIDD size in KB, from system parms
					; on diskette track 0, sector 2
write_tty_dec	equ	04028h		;print a number in decimal digits

oldw:					;old code fragment
	mov	ax,ds:[fidd_size_kb]	;FIDD size in KB

;	call	write_tty_dec		;display FIDD size
;	db	0e8h,99h,01h
	db	0e8h
	dw	write_tty_dec - offw - ($ - oldw) - 2

	retn

neww:					;new code
;	jmp	far our_cs:ourfid
lds3	equ	$+3
	db	0eah			;jmp far
	dw	ourfid
	dw	?							;@@lds

	nop				;padding
	nop

lenwa	equ	neww-oldw
lenwb	equ	$-neww

if	lenwa ne lenwb
	.err 144BLDR2.ASM R9000: Old and new lengths for patch #W are not equal
endif

;------	
;Patch X: subroutine sub_64, page 23

;Here, the BIOS has completed all of its initialization, and jumps to the
;cold start entry point of the CCP at offset 0 within the CP/M-segment.

;The patch makes the BIOS jump to label r0600 in this program, so we can
;perform our own post-initialiation processing (i.e. applying the patches
;to support higher diskette capacities).

ccpcold	equ	0
offx	equ	03D15h			;offset within CP/M-86 segment
data_22	equ	024b7h

oldx:					;old code fragment

	mov	ds:[data_22],cl		;put boot-drive into the
	sti				; CP/M-86 system variables

;	jmp	near ptr ccpcold
;	db	0E9h,0E3h,0C2h
	db	0e9h
	dw	ccpcold - offx - ($ - oldx) - 2

newx:					;new code

;	jmp	far our_cs:r0600	;MASM won't assemble a far jump
lds1	equ	$+3
	db	0eah			;jmp far
	dw	r0600			;label where our program continues
	dw	?			;segment = our segment		;@@lds

	nop				;padding
	nop
	nop

lenxa	equ	newx-oldx
lenxb	equ	$-newx

if	lenxa ne lenxb
	.err 144BLDR2.ASM R9000: Old and new lengths for patch #X are not equal
endif

;------	
;Patch Y: subroutine sub_67, page 25

;Here, the BIOS performs a destructive memory test and initializes a RAMDISK

;The patch makes the test non-destructive, and branches to some extra code.

;The high byte of the "start segment for RAMDISK" can be 08h...90h 
;or 0c0h...0e0h - according to the standard CP/M-86 program SETUP.CMD.
;The low byte is always zero, so the RAMDISK starts at a 4 KB boundary.


offy	equ	03DF9h			;offset within CP/M-86 segment
loc_228	equ	03E27h			;label within RAMDISK test routine

data_195	equ	03a72h		;start-segment for RAMDISK
ramdisk_size_kb	equ	03a74h		;size of RAMDISK in KB

oldy:					;old code fragment

	mov	[di],bl			;poke a test byte (5Ah)
	cmp	[di],bl			;peek it
;	jne	loc_228			;jump if not identical
;	db	75h,28h
	db	75h, loc_228 - offy - ($ - oldy) - 1

	mov	[di],bh			;poke a different test byte (0Fh)
	cmp	[di],bh			;peek it
;	jne	loc_228			;jump if not identical
;	db	75h,22h
	db	75h, loc_228 - offy - ($ - oldy) - 1

	mov	cx,800h			;fill 2K words
	mov	ax,0e5e5h		; with E5E5h
	rep	stosw			;  to initialize 4 KB part of RAMDISK

	add	cs:word ptr [ramdisk_size_kb],4	;add 4 KB to RAM disk size

	mov	ax,ds
	add	ax,100h			;next segment to test for RAM

newy:					;new code

	push	[di]			;save original contents
	mov	[di],bl			;poke a byte
	cmp	[di],bl			;peek it
	pop	[di]			;restore original contents
;	jne	loc_228			;jump if not identical
;	db	75h,24h
	db	75h, loc_228 - offy - ($ - newy) - 1

	push	[di]			;save original contents
	mov	[di],bh			;poke a byte
	cmp	[di],bh			;peek it
	pop	[di]			;restore original contents
;	jne	loc_228			;jump if not identical
;	db	75h,1ah
	db	75h, loc_228 - offy - ($ - newy) - 1

	inc	word ptr cs:[ramdisk_size_kb]	;one more KB found for RAMDISK

;	jmp	far our_cs:our67
lds2	equ	$+3
	db	0eah			;jmp far
	dw	our67
	dw	?							;@@lds

	nop				;padding

lenya	equ	newy-oldy
lenyb	equ	$-newy

if	lenya ne lenyb
	.err 144BLDR2.ASM R9000: Old and new lengths for patch #Y are not equal
endif

;------	
;Patch Z: subroutine bios_fidd, page 27

;Here, the BIOS allocates memory for FIDDS.

;The patch makes CP/M-86 allocate an additional <fidreq> KB of FIDD memory,
;that we'll use later in this program. This is to prevent the user from
;having to reserve these <fidreq> KB's manually with SETUP.CMD.

offz		equ	03E59h		;offset within CP/M-86 segment
;fidd_size_kb	equ	03AC0h		;FIDD size in KB, from system parms
					; on diskette track 0, sector 2

oldz:					;old code fragment
	mov	ax,ds:[fidd_size_kb]	;FIDD size in KB
	test	ax,ax			;is it zero?
;	jz	loc_ret_232		;yes, done
	db	74h,2fh

newz:					;new code
	mov	ax,ds:[fidd_size_kb]	;FIDD size in KB
	add	ax,fidreq		;add what we need for ourselves
;	nop				;padding, assembler will insert this
					;as it does not yet know the type of
					;the variable named "fidreq"

lenza	equ	newz-oldz
lenzb	equ	$-newz

if	lenza ne lenzb
	.err 144BLDR2.ASM R9000: Old and new lengths for patch #Z are not equal
endif

;------ relocate (adjust offsets in new driver code and data, and
;	in some of the patches)

;@@lds: for far jumps: put our current code segment value into the segment
;       data part of the displacement. The patch label lds<n> is a pointer to
;	the instruction bytes 4 & 5, i.e. the segment part of the operand.
;	# items: 3

r0510:
	cmp	x44flag,0		;shall we patch CPM.SYS?
	jnz	r0511			;yes, let's do that

	jmp	r0570			;no, just cold start it.
r0511:
	mov	ax,cs			;@@lds items
	mov	word ptr lds1,ax
	mov	word ptr lds2,ax
	mov	word ptr lds3,ax

;------ verify the patches

	mov	m209a,'W'		;put patch number into message text
	mov	si,offset oldw
	mov	di,offw
	mov	cx,lenwa
	call	verify

	mov	m209a,'X'		;put patch number into message text
	mov	si,offset oldx
	mov	di,offx
	mov	cx,lenxa
	call	verify

	mov	m209a,'Y'		;put patch number into message text
	mov	si,offset oldy
	mov	di,offy
	mov	cx,lenya
	call	verify

	mov	m209a,'Z'		;put patch number into message text
	mov	si,offset oldz
	mov	di,offz
	mov	cx,lenza
	call	verify

	cmp	ptcherr,0		;all patches OK?
	jz	r0530			;yes
	jmp	dsperr10		;no
r0530:

;------ apply Richard Kanarek's "AT Patch"

;This patch might already be present in CPM.SYS, so we just continue
;if we do not find the two original CP/M-86 stosw instructions.

	push	ds
	mov	ds,[cpmseg]

	mov	bx,03d2fh
	cmp	byte ptr [bx],0abh	;stosw?
	jnz	r0540
	mov	byte ptr [bx],47h	;inc di
r0540:
	mov	bx,3d39h
	cmp	byte ptr [bx],0abh	;stosw?
	jnz	r0550
	mov	byte ptr [bx],47h	;inc di
r0550:
	pop	ds

;------ apply the patches

	mov	si,offset neww
	mov	di,offw
	mov	cx,lenwa
	call	patch

	mov	si,offset newx
	mov	di,offx
	mov	cx,lenxa
	call	patch

	mov	si,offset newy
	mov	di,offy
	mov	cx,lenya
	call	patch

	mov	si,offset newz
	mov	di,offz
	mov	cx,lenza
	call	patch

;------ cold start CPM.SYS
;
;The official cold start entry point of the BIOS INIT is at [cpmseg]:2500h.
;However, we jump directly into the INIT routine, just _after_ the point where
;INIT sets up its local 128 byte stack.
;The size of that stack is not enough for our Dell Pentium system, which needs
;about 180 bytes and thus overwrites the DPB's in the CPM BIOS. So we will
;jump to INIT while our own local stack of 1 KB is still active.

r0570:
	mov	dl,0			;INT 13h number of boot drive

;	jmp	far ptr [cpmseg]:3BE9h
	db	0eah
	dw	3be9h
r0580	dw	?

r0599:

;------ Control returns here, after the BIOS in CPM.SYS has initialized itself.
;       Now we can do the patches for the 1.44 MB Feature.

r0600:
	mov	ds:[data_22],cl	;put boot-drive into CP/M-86 system variables

	sti

;set DS and ES back to our own segment

	push	cs
	pop	ds

	push	cs
	pop	es

;switch back to our own local stack

	push	cs
	cli
	pop	ss			;use a local stack, just below
	mov	sp,estack		; the top of RAM
	sti

	jmp	r0610			;jump past patch data

;------ patches for a running CP/M-86 system (same as done by 144PAT2.CMD)

;Patch 1: routine sub_37, page 8

;Original CP/M-86 calls this routine when a diskette drive is about to be 
;accessed "for the very first time". The bios reads track 0 of the diskette 
;and checks the last byte on the bootsector of the track to see whether it's
;160 KB or 320 KB media. Then, it puts the address of the appropriate DPB into
;the DPH for the drive.

;The original instructions are replaced by a far jump to new routine #1,
;which is placed in the old 4 KB track buffer

off1	equ	02D18h			;offset within CP/M-86 segment

old1:					;old code fragment

sub_37:
	push	ds:[03a5eh]		;save track number from bios_settrk

	mov	ds:[03a5eh],word ptr 0	;set track number 0

;	call	sub_33			;read track number 0
	db	0e8h,0eeh,0feh

	jnc	loc_162			;jump if no error

;	jmp	loc_202			;jump if error
	db	0e9h,06eh,004h

loc_162:
	mov	word ptr [bx][10],dpb160;put 160 KB DPB into current DPH

	push	bx
	mov	bx,offset track_buf_org	;offset int13h_track_buffer
	dec	byte ptr [bx][511]	;CP/M-86 media byte: 0=160 KB, 1=320 KB
	pop	bx

	jnz	loc_163			;jump if media byte was 0 = 160 KB

	mov	word ptr [bx][10],dpb320;put 320 KB DPB into current DPH
loc_163:

	pop	ds:[03a5eh]		;restore track number from bios_settrk
	retn

new1:					;new code fragment

;	jmp	far cs:ar100		;MASM won't assemble a far jump
cps2	equ	$+3
	db	0eah			;jmp far
	dw	rcode00 + ar100 - tcode00
	dw	0			;segment = cpmseg		;@@cps

	dw	9090h,9090h,9090h,9090h	;39 NOP's
	dw	9090h,9090h,9090h,9090h
	dw	9090h,9090h,9090h,9090h
	dw	9090h,9090h,9090h,9090h
	dw	9090h,9090h,9090h
	db	90h

len1a	equ	new1-old1
len1b	equ	$-new1			;length of old and new code fragments

if	len1a ne len1b
	.err 144BLDR2.ASM R9000: Old and new lengths for patch #1 are not equal
endif

;------

;Patch 2: subroutine sub_38, page 9
;
;Original CP/M-86 sets up some parameters for PC-ROM-BIOS interrupt 13h 
;to read a full diskette track of 8 sectors.

;The original instructions are replaced by a far jump to new routine #2,
;which is placed in the old 4 KB track buffer


off2	equ	02D4Fh			;offset within CP/M-86 segment

old2:					;old code fragment

	mov	ch,al			;track #
	cmp	ch,40			;track 40 or higher?
	jb	loc_164			;no
	mov	ch,79			;yes: calculate 79
	sub	ch,al			; minus track #
	mov	dh,1			;  and set head to 1
loc_164:
	mov	cl,1			;starting sector for INT 13h
	mov	al,8			;read 8 sectors = 1 full track

new2:					;new code fragment

;	jmp	far cs:ar200		;MASM won't assemble a far jump
cps3	equ	$+3
	db	0eah			;jmp far
	dw	rcode00 + ar200 - tcode00
	dw	0			;segment = cpmseg		;@@cps

	dw	9090h,9090h,9090h,9090h	;12 NOP's
	dw	9090h,9090h

len2a	equ	new2-old2
len2b	equ	$-new2			;length of old and new code fragments

if	len2a ne len2b
	.err 144BLDR2.ASM R9000: Old and new lengths for patch #2 are not equal
endif

;------

;Patch 3: subroutine sub_30, page 5

;Here, the BIOS is calculating the displacement of a given sector number
;within the full track buffer.

;The patch directs the BIOS to the new 9KB buffer

off3	equ	02BEBh			;offset within CP/M-86 segment

old3:					;old code fragment (3 bytes)
	mov	ax,offset track_buf_org	;3be2h

new3:					;new code
nof1	equ	$+1
	mov	ax,0			;@@nof

len3a	equ	new3-old3
len3b	equ	$-new3

if	len3a ne len3b
	.err 144BLDR2.ASM R9000: Old and new lengths for patch #3 are not equal
endif

;------

;Patch 4: subroutine sub_38, page 9:

;Here, the BIOS puts the offset of the memory buffer for PC-ROM-BIOS interrupt
;13h into BX.

;The patch directs the BIOS to the new 9KB buffer

off4	equ	02D95h			;offset within CP/M-86 segment

old4:					;old code fragment (3 bytes)
	mov	bx,offset track_buf_org	;3be2h

new4:					;new code
nof2	equ	$+1
	mov	bx,0			;@@nof

len4a	equ	new4-old4
len4b	equ	$-new4

if	len4a ne len4b
	.err 144BLDR2.ASM R9000: Old and new lengths for patch #4 are not equal
endif

;------

;Patch 5: after label loc_181, page n/a

;Here, the BIOS is switching to a 64 byte local stack during control-break
;handling (?). This stack is immediately followed by a second 64 byte local
;stack that is used by the user timer tick handler.
;
;New: reuse part of the old full_track_buffer for a larger (256 byte) stack.
;I hoped this would prevent the hang-up of my Toshiba when the ctrl-break
;key combination is pressed - but it didn't. But it won't harm, either.

;Moving this control-break stack also allows for the user timer tick handler
;stack to use 128 instead of the original 64 bytes.

off5	equ	02EB7h			;offset within CP/M-86 segment

old5:					;old code fragment (3 bytes)
	mov	sp,offset track_buf_org - 64

new5:					;new code
	mov	sp,offset ctrl_break_stk

len5a	equ	new5-old5
len5b	equ	$-new5

if	len5a ne len5b
	.err 144BLDR2.ASM R9000: Old and new lengths for patch #5 are not equal
endif

;------
;Patch sites for the CCP and BDOS stack switches.
;
;These move when the kernel is rebuilt from the cleaned-up sources, so the
;offsets and the BDOS stack value are selected at assembly time. Assemble with
;/Dexpkrnl=1 to target cpmexp.sys instead of cpm.sys.

ifndef	expkrnl
expkrnl	equ	0
endif

if	expkrnl
ccpstk1	equ	00322h			;cpmexp.sys
ccpstk2	equ	00362h
ccpstk3	equ	00362h
ccpstk4	equ	007B9h
else
ccpstk1	equ	0031Fh			;cpm.sys / cpmorg.sys
ccpstk2	equ	0035Fh
ccpstk3	equ	0035Fh
ccpstk4	equ	007DBh
endif

;Same in both kernels: bdosexp.a86 pins WKFCB so the BDOS data area cannot move.
bdosoff	equ	00B31h
bdosstk	equ	0248Eh

;------

;Patches 6 through 9:

;Here, the CCP is switching to its 96 byte local stack at offset 930h.
;
;New: reuse part of the old full_track_buffer for a larger (256 byte) stack.
;This cures the scrambled status line when erasing or renaming a read-only
;file from the CCP command prompt.

off6	equ	ccpstk1			;offset within CP/M-86 segment

old6:					;old code fragment (3 bytes)
	mov	sp,930h

new6:					;new code
	mov	sp,offset ccp_new_stk

len6a	equ	new6-old6
len6b	equ	$-new6

if	len6a ne len6b
	.err 144BLDR2.ASM R9000: Old and new lengths for patch #6 are not equal
endif

off7	equ	ccpstk2			;offset within CP/M-86 segment
old7	equ	old6			;old code fragment (3 bytes)
new7	equ	new6			;new code
len7a	equ	len6a

off8	equ	ccpstk3			;offset within CP/M-86 segment
old8	equ	old6			;old code fragment (3 bytes)
new8	equ	new6			;new code
len8a	equ	len6a

off9	equ	ccpstk4			;offset within CP/M-86 segment
old9	equ	old6			;old code fragment (3 bytes)
new9	equ	new6			;new code
len9a	equ	len6a

;------
;Patch A:

;Here, the BDOS is switching to a 164 (?) byte local stack at offset 248Eh
;
;New: reuse part of the old full_track_buffer for a larger (256 byte) stack.

offa	equ	bdosoff			;offset within CP/M-86 segment

olda:					;old code fragment (3 bytes)
	mov	sp,bdosstk

newa:					;new code
	mov	sp,offset bdos_new_stk

lenaa	equ	newa-olda
lenab	equ	$-newa

if	lenaa ne lenab
	.err 144BLDR2.ASM R9000: Old and new lengths for patch #A are not equal
endif

;------	verify the patches to the in-memory CPM.SYS

r0610:
	mov	m209a,'1'		;put patch number into message text
	mov	si,offset old1
	mov	di,off1
	mov	cx,len1a
	call	verify

	mov	m209a,'2'		;put patch number into message text
	mov	si,offset old2
	mov	di,off2
	mov	cx,len2a
	call	verify

	mov	m209a,'3'		;put patch number into message text
	mov	si,offset old3
	mov	di,off3
	mov	cx,len3a
	call	verify

	mov	m209a,'4'		;put patch number into message text
	mov	si,offset old4
	mov	di,off4
	mov	cx,len4a
	call	verify

	mov	m209a,'5'		;put patch number into message text
	mov	si,offset old5
	mov	di,off5
	mov	cx,len5a
	call	verify

	mov	m209a,'6'		;put patch number into message text
	mov	si,offset old6
	mov	di,off6
	mov	cx,len6a
	call	verify

	mov	m209a,'7'		;put patch number into message text
	mov	si,offset old7
	mov	di,off7
	mov	cx,len7a
	call	verify

	mov	m209a,'8'		;put patch number into message text
	mov	si,offset old8
	mov	di,off8
	mov	cx,len8a
	call	verify

	mov	m209a,'9'		;put patch number into message text
	mov	si,offset old9
	mov	di,off9
	mov	cx,len9a
	call	verify

	mov	m209a,'A'		;put patch number into message text
	mov	si,offset olda
	mov	di,offa
	mov	cx,lenaa
	call	verify

	cmp	ptcherr,0		;all patches OK?
	jz	r0630			;yes
r0620:					;no
	jmp	r0620			;loop forever
r0630:

;-------------- find number of diskette drives known to CP/M-86

r6200:
	mov	es,cpmseg
	mov	bx,03ab2h		;CP/M-86 BIOS table data_224
	mov	cl,'A'			;counter 'A'...'D'
r6210:
	mov	al,byte ptr es:[bx]	;get a byte from the BIOS table

	cmp	al,80h			;harddisk (80h...83h)?
	jae	r6230			;yes

	cmp	al,0			;drive number is 00?
	jnz	r6220			;no, it's a valid diskette drive

	cmp	cl,'A'			;yes, 00 is only valid if drive A:
	jne	r6230			;jump if not drive A:
r6220:
	inc	nflop			;one more diskette drive found
r6230:
	inc	bx			;next byte from BIOS table
	inc	cl			;next drive letter A...D
	cmp	cl,'E'			;at drive E:?
	jb	r6210			;not yet, continue
r6299:
;-------------- find the FIDD storage descriptor ----------------------

r7000:
	mov	ax,[cpmseg]		;the CP/M-86 code and data segment
	mov	si,offset m205e
	call	w2hex

	mov	ax,fidreq		;required FIDD kb's
	mov	si,offset m205d
	call	w2hex

	mov	es,[cpmseg]		;segment of FIDD storage descriptor
	mov	bx,es:2556h		;near ptr to FIDD storage descriptor
	
	mov	ax,es:[bx]		;size of FIDD storage in KB (0...99)
	mov	[fidsize],ax
	mov	si,offset m205c
	call	w2hex

	mov	ax,es:[bx][2]		;segment of FIDD storage
	mov	[fidseg],ax
	mov	si,offset m205b
	call	w2hex

r7099:

;	mov	si,offset m205
;	call	dspmsg

;-------------- check amount of FIDD storage in kilobytes -------------

r8000:
	mov	m205a,'1'		;FIDD error 1

	mov	ax,fidsize		;FIDD size in KB
	cmp	ax,fidreq		;is it enough?
	jae	r8099			;yes, OK

	mov	si,offset m205		;no, FIDD error 1
	jmp	dsperr
r8099:

;-------------- check that the FIDD segment is above the CP/M-86 segment

r8200:

	mov	ax,fidseg
	cmp	ax,cpmseg		;FIDD segment above CP/M-86 segment?
	ja	r8299			;yes, OK

	inc	m205a			;no, strange....
	mov	si,offset m205		;FIDD error 2
	call	dspmsg

	jmp	$			;loop forever
r8299:

;-------------- check that the first <fidreq> KB of FIDD storage is "near"

;We want the first <fidreq> KB of FIDD storage to be "near" to the CP/M-86,
;i.e. we want to be able to access all these KB's using a segment register
;that holds the value of the CP/M-86 code and data segment.
;
;Why do we want this: if the first KB's of FIDD storage were not "near", we
;would had to make a number of additional patches to the CP/M-86 code in
;storage.

;1 KB equals 64 16-byte paragraphs. So the FIDD segment should not be more
;than 9 * 64 = 576 paragraphs above the CP/M-86 segment.

r8300:
	mov	ax,cpmseg
	add	ax,(64 - fidreq) SHL 6

	cmp	ax,fidseg
	jae	r8399			;OK

	inc	m205a
	mov	si,offset m205		;FIDD error 3
	call	dspmsg

	jmp	$			;loop forever
r8399:

;-------------- calculate the "near" offset of the first FIDD storage byte
;		relative to the CP/M-86 code and data segment

r8400:
	mov	ax,fidseg		;FIDD segment
	sub	ax,cpmseg		;minus CPM segment
	mov	cl,4			;convert from 16-byte-paragraphs
	shl	ax,cl			; to bytes
	mov	fidnof,ax		;"near" offset of first FIDD byte
r8499:

;-------------- relocate (adjust offsets in new driver code and data, and
;               in some of the patches)

;@@nof: for data references: fill in the offset of the new track buffer.
;	The patch label nof<n> is a pointer to the appropriate offset in the
;	instruction.
;	# items: 2
;
;@@cps: for far jumps: put the CP/M-86 segment value into the segment
;       data part of the displacement. The patch label cps<n> is a pointer to
;	the instruction bytes 4 & 5, i.e. the segment part of the operand.
;	# items: 5

r10200:
	push	cs
	pop	ds

	mov	ax,fidnof		;@@nof items
	mov	word ptr nof1,ax
	mov	word ptr nof2,ax

	mov	ax,cpmseg		;@@cps items
	mov	word ptr cps1,ax
	mov	word ptr cps2,ax
	mov	word ptr cps3,ax
	mov	word ptr cps4,ax
	mov	word ptr cps5,ax

;-------------- update the FIDD storage descriptor

r10000:

	mov	ax,fidsize		;old FIDD size in KB
	sub	ax,fidreq		;subtract what we need in KB
	mov	fidnsize,ax		;new FIDD size in KB

	mov	ax,fidreq		;required FIDD size in KB
	mov	cl,6			;convert from KB
	shl	ax,cl			; to 16 byte paragraphs
	add	ax,fidseg		;add old FIDD segment
	mov	fidnseg,ax		;new FIDD segment

	cmp	fidnsize,0		;is the new FIDD size zero?
	jne	r10010			;no
	mov	fidnseg,0		;yes, set new FIDD segment to zero

r10010:
	mov	es,cpmseg		;the cpm segment
	mov	bx,es:2556h		;pointer to FIDD storage descriptor

	mov	ax,fidnsize
	mov	es:[bx],ax		;new FIDD size in KB

	mov	ax,fidnseg
	mov	es:[bx][2],ax		;new FIDD segment

r10099:

;-------------- patch the CP/M-86 BIOS

r13000:

	mov	si,offset new1
	mov	di,off1
	mov	cx,len1a
	call	patch

	mov	si,offset new2
	mov	di,off2
	mov	cx,len2a
	call	patch

	mov	si,offset new3
	mov	di,off3
	mov	cx,len3a
	call	patch

	mov	si,offset new4
	mov	di,off4
	mov	cx,len4a
	call	patch

r13999:

;-------------- copy old track buffer to new one

r14000:

;------ copy old 4 KB (8 sectors) track buffer to new 9 KB buffer (18 sectors)

	mov	si,track_buf_org
	mov	di,fidnof
	mov	cx,4096

	mov	es,cpmseg
	mov	ds,cpmseg
	cld
	rep	movsb

	push	cs
	pop	ds			;restore DS

;the original 4 KB track buffer is now available for other purposes

;fill in some variables

	mov	es,cpmseg

	mov	ax,fidnof
	mov	es:rfidnof,ax

;make patch #5

	mov	si,offset new5
	mov	di,off5
	mov	cx,len5a

	call	patch

;make patch #6

	mov	si,offset new6
	mov	di,off6
	mov	cx,len6a

	call	patch

;make patch #7

	mov	si,offset new7
	mov	di,off7
	mov	cx,len7a

	call	patch

;make patch #8

	mov	si,offset new8
	mov	di,off8
	mov	cx,len8a

	call	patch

;make patch #9

	mov	si,offset new9
	mov	di,off9
	mov	cx,len9a

	call	patch

;make patch #A

	mov	si,offset newa
	mov	di,offa
	mov	cx,lenaa

	call	patch

;------ for each diskette drive: set the pointers in its dph to new, 
;       larger csv and alv areas in the old buffer

	mov	es,cpmseg

	mov	bx,es:[03AAAh+0]		;get address of first DPH
						;from DPH table at data_223

	mov	es:[bx][12],csv144a		;csv
	mov	es:[bx][14],offset alv144a	;alv

	dec	nflop				;more drives?
	jz	r14100				;no

	mov	bx,es:[03AAAh+2]		;get address of second DPH
	mov	es:[bx][12],offset csv144b	;csv
	mov	es:[bx][14],offset alv144b	;alv

	dec	nflop				;more drives?
	jz	r14100				;no

	mov	bx,es:[03AAAh+4]		;get address of third DPH
	mov	es:[bx][12],offset csv144c	;csv
	mov	es:[bx][14],offset alv144c	;alv

	dec	nflop				;more drives?
	jz	r14100				;no

	mov	bx,es:[03AAAh+6]		;get address of fourth DPH
	mov	es:[bx][12],offset csv144d	;csv
	mov	es:[bx][14],offset alv144d	;alv

r14100:

;------ move DPT's to old buffer

	mov	es,cpmseg
	mov	si,offset dpt35
	mov	di,offset rdpt35
	mov	cx,11
	cld
	rep	movsb

	mov	es,cpmseg
	mov	si,offset dpt12
	mov	di,offset rdpt12
	mov	cx,11
	cld
	rep	movsb

;------ move DPB's for higher capacity diskette formats to old buffer

	mov	es,cpmseg
	mov	si,offset dpb144
	mov	di,offset rdpb144
	mov	cx,15
	cld
	rep	movsb

	mov	es,cpmseg
	mov	si,offset dpb720
	mov	di,offset rdpb720
	mov	cx,15
	cld
	rep	movsb

	mov	es,cpmseg
	mov	si,offset dpb12m
	mov	di,offset rdpb12m
	mov	cx,15
	cld
	rep	movsb

	mov	es,cpmseg
	mov	si,offset dpb72p
	mov	di,offset rdpb72p
	mov	cx,15
	cld
	rep	movsb

;------ fill in some control block separators

	mov	ds,cpmseg

	mov	byte ptr ds:[db1],0DBh
	mov	byte ptr ds:[db2],0DBh
	mov	byte ptr ds:[db3],0DBh
	mov	byte ptr ds:[db4],0DBh
	mov	byte ptr ds:[db5],0DBh
	mov	byte ptr ds:[db6],0DBh
	mov	byte ptr ds:[db7],0DBh
	mov	byte ptr ds:[db8],0DBh
	mov	byte ptr ds:[db9],0DBh
	mov	byte ptr ds:[db10],0DBh
	mov	byte ptr ds:[db11],0DBh
	mov	byte ptr ds:[db12],0DBh
	mov	byte ptr ds:[db13],0DBh
	mov	byte ptr ds:[db14],0DBh
	mov	byte ptr ds:[db15],0DBh
	mov	byte ptr ds:[db16],0DBh
	mov	byte ptr ds:[db17],0DBh
	mov	byte ptr ds:[db18],0DBh
	mov	byte ptr ds:[db19],0DBh
	mov	byte ptr ds:[db20],0DBh

	mov	word ptr ds:[progid1+0],'14'	;ASCII text '41F4AE02'
	mov	word ptr ds:[progid1+2],'4F'
	mov	word ptr ds:[progid1+4],'EA'
	mov	word ptr ds:[progid1+6],'20'

	push	cs
	pop	ds

;------ move additional resident code to old buffer

	mov	es,[cpmseg]
	mov	si,offset tcode00
	mov	di,rcode00
	mov	cx,tcodeln
	cld
	rep	movsb

	push	cs
	pop	es
r0799:

;------ Format the RAMDISK. Normally, this would overwrite our code.
;	So we will not format the last 26 KB of the RAMDISK, if the RAMDISK
;	starts somewhere in the 640 KB base memory, i.e. below A000h.
;
;	To remove any residual data in this 26 KB, originating from a RAMDISK
;	in a previous life, we will clear out most of this 26 KB separately.

r0800:
	mov	es,[cpmseg]
	mov	ax,es:[ramdisk_size_kb]	;size of RAMDISK in KB (0...512+ KB)

	cmp	ax,0			;any RAMDISK present?
	jnz	r0805			;yes
	jmp	r0899			;no, done
r0805:
	sub	ax,esize		;subtract the KB's for our own code
	jg	r0810			;jump if any KB's left to format
	
	jmp	r0890			;rather small RAMDISK, standard CPM.SYS
					; assumes at least 64 KB...

r0810:

;how many blocks of 64 KB?

	mov	bl,64
	div	bl			;quotient in AL, remainder in AH
	push	ax			;AL = number of 64 KB blocks

	mov	bl,al			;number of 64 KB blocks

	mov	es,es:[data_195]	;start-segment of RAMDISK
	xor	di,di

	cmp	bl,0			;any full 64 KB blocks?
	jz	r0850			;no

	mov	ax,0e5e5h
r0820:
	mov	cx,32768		;32 KB words
	cld
	rep	stosw

	mov	cx,es
	add	cx,1000h		;prepare segment for next 64 KB block
	mov	es,cx

	dec	bl
	jnz	r0820			;jump if more full 64 KB blocks

r0850:
	pop	ax			;AH = number of KB's (0...63)

	cmp	ah,0			;any loose KB's?
	jz	r0850			;no, done

	mov	al,ah
	mov	ah,0			;number of KB's now in AX (1...63)

	mov	cl,9
	shl	ax,cl			;from KB's to words
	mov	cx,ax

	mov	ax,0e5e5h

	cld
	rep	stosw

r0890:

;clear most of the 26 KB memory used by this boot loader program

	push	cs
	pop	es
	mov	di,estrkbf

	mov	ax,0e5e5h
	mov	cx,(eswrknd - estrkbf) / 2

	cld
	rep	stosw
r0899:

;------ Done. Now we're ready to cold start the CCP and the BDOS

r0900:

	mov	si,offset m203		;final hints & tips
	call	dspmsg

;The CCP will set its own SP, assuming that SS already holds the CPM segment.
;So we set SS to the CPM segment, which means that we should also set a new SP
;now.

	cli
	mov	ss,[cpmseg]
	mov	sp,offset ccp_new_stk	;use the new, larger CCP stack
	sti

	mov	es,[cpmseg]
	mov	ds,[cpmseg]

	mov	ds:[351fh],byte ptr 23	;set cursor line
					; (CP/M BIOS init code has set this
					; before, but after that we have
					; displayed our own message M203)

;	jmp	far ptr [cpmseg]:0	;CCP cold start entry point
	db	0eah
	dw	0
r0910	dw	?

r0999:

;------ called by patch #W: increase FIDD memory with <fidreq> KB's, without
;       CP/M-86 telling it to the user. Otherwise, CP/M-86 would report some
;       KB's which the user wouldn't be able to use later on, as these KB's
;       then already have been eaten up by the 1.44 MB support in this program.

ourfid:
	mov	ax,ds:[fidd_size_kb]	;original user-defined FIDD size in KB,
					; this will be displayed by CP/M-86

	add	word ptr ds:[fidd_size_kb],fidreq
					;sneak in another <fidreq> KB

;	jmp	far ptr [cpmseg]:write_tty_dec
	db	0eah
	dw	write_tty_dec		;this routine does the retn
ourfi99	dw	?

;------ Called by patch #Y: RAM test for RAMDISK

;Changes to the original routine:
;1. RAM is tested non-destructively, to prevent clobbering our boot loader.
;2. RAM is tested in 1 KB increments (was 4 KB).
;3. Consider modern systems with only 638 or 639 KB RAM available (where upper
;   1 or 2 KB's are reserved for use by the PC-ROM-BIOS).

our67:
	int	12h			;AX := system RAM in KB's
	mov	cl,6
	shl	ax,cl			;AX := system RAM in paragraphs
	mov	cx,ax			;CX := system RAM in paragraphs

	mov	ax,ds
	add	ax,40h			;prepare for next 1 KB block

	cmp	ax,cx			;top-of-RAM reached?
	jne	our6798			;no, continue standard CP/M processing
	mov	ax,0A000h		;yes, A000 forces end of memory scan

our6798:				;back to the standard CP/M-86 routine

;	jmp	far ptr [cpmseg]:03E18h
	db	0eah
	dw	03e18h
our6799	dw	?

;------ Subroutine to read a CP/M-86 data block [AX] from diskette into ES:DI
;
;Input: AX = CP/M-86 data block number 0...354 (= maximum value, for 1.44 MB)
;       ES:DI = where to put the data

readblk:

	mov	cx,[spb]
	mul	cx			;AX := first sector of data block
					; (zero-based number)

	div	byte ptr [spt]		;divide AX by sectors-per-track
					; AL := track 0...159
					; AH := sector 0...17 (zero-based)

	add	al,2			;add 2 reserved tracks (OFF from DPB),
					; giving track number 2...159

;now read 4 or 8 (720 KB or 1.2/1.44 MB) consecutive sectors, starting with
;the track AL and the sector AH we just have calculated

readb20:				;AH=track 0...158 AL=sector 0...17
	push	cx

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

	mov	cx,512
	cld
	rep	movsb			;move from full track buffer to "DMA"

	mov	si,offset msgdot	;progress indicator
	call	dspmsg

;prepare for next sector

	inc	ah			;next sector

	cmp	ah,[spt]		;exceeding sectors per track?
	jb	readb50			;no

	mov	ah,0			;yes, set sector 0
	inc	al			;set next track 

readb50:
	pop	cx
	loop	readb20			;jump if more sectors to read

	retn

;------ read all sectors on track AL with INT 13h into the buffer at ES:estrkbf

int13:

	push	es
	push	ds
	pop	es

	mov	si,5			;retry count

int1302:
	push	ax

;calculate head and track for INT 13h from CP/M-86's track number:
;if track number in AL >= 80 then AL := (159 - AL) and head := 1

	mov	dh,0			;assume head 0

	cmp	al,80			;track 80 or higher?
	jb	int1305			;no, done

	sub	al,159			;yes, subtract 159
	neg	al			;make two's complement

	inc	dh			;head := 1
int1305:

	mov	ch,al			;track for INT 13h

	mov	bx,estrkbf		;offset of track buffer (segment = ES)
	mov	cl,1			;CL := starting sector
	mov	dl,0			;DL := 0 = drive

int1310:
	mov	al,[spt]		;AL := number of sectors,
	mov	ah,2			;AH := 2 =read

	int	13h

	pop	ax
	jnc	int1399			;jump if no error

	dec	si			;error; give it another try?
	jnz	int1302			;yes

	mov	si,offset m201		;display I/O error
	jmp	dsperr

int1399:
	pop	es

	retn

;------ Scan the whole directory, loaded by the boot ssector program into
;	ES:esdirbf...esdirbf+2000h, for a directory record of CPM.SYS

;Returns: when found, carry is clear, DI holds offset of directory record
;         when not found, carry is set

scan:
	mov	al,0			;scan 256 directory entries
	mov	di,esdirbf		;start of buffer for directory sectors
scan35:

	and	word ptr es:[di+9],07f7fh	;clear r/o and sys bits
	and	byte ptr es:[di+11],07fh	;clear arc bit (CP/M Plus only)

	mov	cl,[exmcurr]		;EXM from DPB for current media
	not	cl			;flip all bits
	and	byte ptr es:[di+12],cl	;FEh for 1.2/1.44 MB; FFh for 720 KB

scan45:
	mov	si,offset dsn1
	mov	cx,1+8+3+1		;user number: 1 byte (user 0)
					;file name: 8 bytes
					;file type: 3 bytes
					;directory extent sequence #: 1 byte
	cld
	rep	cmpsb
	jz	scan98			;jump if found
scan50:
	and	di,0ffe0h		;make lower five bits zero, 
	add	di,32			; increment to next directory entry
					; assuming buffer on a 32-byte boundary

	dec	al			;decrement entry counter
	jnz	scan35			;jump if more entries to check

	stc				;not found
	jmp	short scan99
scan98:
	and	di,0ffe0h		;make lower five bits zero
	clc				;found; ES:DI points to first byte
					;of the directory record
scan99:
	retn

;-------------- display a message and loop forever --------------------

dsperr:
	call	dspmsg

dsperr10:
	mov	si,offset m208
	call	dspmsg

	jmp	short $			;loop forever

;------ display ASCII$ message at DS:SI on the console ----------------

dspmsg:
	push	ax
	push	bx

dspm10:
	cld
	lodsb

	cmp	al,'$'			;string terminator?
	jz	dspmsg99		;yes, done

	mov	ah,0eh			;write in TTY mode
	xor	bx,bx			;BH=0=page BL=0=color
	int	10h

	jmp	short dspm10		;next character

dspmsg99:
	pop	bx
	pop	ax

	ret

;-------------- verify a patch

verify:
	mov	es,[cpmseg]
	cld
	rep	cmpsb
	jz	ver999			;OK

	mov	[ptcherr],1		;not OK

	dec	si
	mov	al,[si]			;expected value
	mov	si,offset m209d
	call	b2hex

	dec	di			;offset within CP/M-86 segment
	mov	ax,di			; where first mismatch occurred
	mov	si,offset m209c
	call	w2hex

	mov	al,es:[di]		;value actually found in storage
	mov	si,offset m209e
	call	b2hex	

	mov	ax,[cpmseg]		;CP/M-86 segment
	mov	si,offset m209b
	call	w2hex

	mov	si,offset m209		;verify for patch #? failed
	call	dspmsg			;display string

ver999:
	ret

;-------------- make a patch

patch:
	mov	es,[cpmseg]
	cld
	rep	movsb
pat999:
	ret

;------

;============== start of working storage ==============================

fidreq		equ	9	;number of near FIDD KB's required by this pgm:
				;9 KB for a full 18-sector track on 1.44 MB

fidseg		dw	0	;segment for FIDD storage
fidsize		dw	0	;size of FIDD storage in KB (1024 bytes)

fidnseg		dw	0	;new segment for FIDD storage
fidnsize	dw	0	;new size of FIDD storage in KB

fidnof		dw	0	;near offset of first FIDD storage byte

cpmseg		dw	0	;the CP/M-86 code and data segment

cpmseg1		dw	0	;segment for INT E0h (BDOS calls)
cpmseg2		dw	0	;segment for INT E6h (FIDD disk interrupt)
cpmseg3		dw	0	;segment from BDOS call 27 get addr(alloc)
cpmseg4		dw	0	;segment from BDOS call 31 get addr(dpb)
cpmseg5		dw	0	;segment from BDOS call 49 get addr(sysvars)
cpmseg6		dw	0	;segment for INT 00h (overflow)
cpmseg7		dw	0	;segment for INT 1Bh (keyboard break)
cpmseg8		dw	0	;segment for INT 1Ch (user timer tick)
cpmseg9		dw	0	;segment for INT 1Eh (diskette parameters)

nsegs		equ	9	;total number of "cpm segments" checked

w_verb		db	0	;0 or 1, meaning no/yes verbose output
w_3inch		db	0	;0 or 1, meaning no/yes always use 3.5 inch DPT

nflop		db	0	;number of CP/M-86 diskette drives
curdsk		db	0	;current drive
logvec		dw	0	;login vector drives P...A for bits 15...0


msgok	db	'OK'
	db	0dh,0ah,'$'

msgdot	db	'.$'

m200	db	0dh,0ah
	db	'Loading CPM.SYS$'

m201	db	'M201 - Sorry, error while reading CPM.SYS from'
	db	' your boot diskette.'
	db	0dh,0ah,'$'

m202	db	0dh,0ah
	db	'M202 - Sorry, the file CPM.SYS '
	db	'cannot be found on your boot diskette.'
	db	0dh,0ah,'$'

m203	db	'The 1.44 MB Feature for CP/M-86 - by Freek Heite - '
	db	'version 2.0 - 16Oct2000'
	db	0dh,0ah
	db	'Driver for 720KB, 1.2 MB and 1.44 MB diskettes '
	db	'loaded succesfully.'
	db	0dh,0ah
	db	0dh,0ah
	db	'P.S. Don''t forget to press control-C after '
	db	'changing diskettes!'
	db	0dh,0ah,'$'

m204	db	0dh,0ah
	db	'M204 - Sorry, bad data in the CMD-header of CPM.SYS - error #'
m204a	label	byte
	db	'?.'
	db	0dh,0ah
	db	'       Info: G-Form1='
m204b	db	'??h G-Length='
m204c	db	'????h A-Base='
m204d	db	'????h G-Min='
m204e	db	'????h G-Max='
m204f	db	'????h'
	db	0dh,0ah
	db	'             G-Form2='
m204g	db	'??h'
	db	0dh,0ah,'$'

m205	db	0dh,0ah
;	db	'M205 - Sorry, problem found with FIDD storage - error #'
	db	'M205 - FIDD error #'
m205a	label	byte
	db	'?.'
	db	0dh,0ah
	db	'       Info: FIDDSEG='
m205b	db	'????h FIDDSIZE='
m205c	db	'????h FIDDREQ='
m205d	db	'????h CPMSEG='
m205e	db	'????h'
	db	0dh,0ah,'$'

m207	db	0dh,0ah
	db	'M207 - Sorry, your system should have more than'
	db	' 128 KB of memory'
	db	0dh,0ah,'$'

m208	db	0dh,0ah
	db	'M208 - Sorry, CP/M-86 cannot be started. Insert other'
	db	0dh,0ah
	db	'       diskette, and press Ctrl-Alt-Del to reboot.'
	db	0dh,0ah,'$'

m209	db	'M209 - Sorry, patch '
m209a	db	'x at '
m209b	db	'????:'
m209c	db	'????h failed: expected '
m209d	db	'??h, found '
m209e	db	'??h.'
	db	0dh,0ah,'$'

;------ DPT's for 3.5 inch diskettes (values taken from MS-DOS 6.2)
;       and for 1.2 MB capacity on 5.25 inch diskette (values taken from 
;	the magazine C'T, 02/1990)
;
;dpt35:	db	0dfh,002h,025h,002h,012h,01bh,0ffh,06ch,0f6h,00fh,008h
;                                    **             **       
;dpt12:	db	0dfh,002h,025h,002h,00fh,01bh,0ffh,054h,0f6h,00fh,008h

dsn1	db	0			;user number = 0
	db	'CPM     '		;file name
	db	'SYS'			;file type
dsn1ext	db	0			;directory record sequence # = 0

cpmedia	db	?			;12/72/144

exm	db	1			;EXM (as in DPB): 0 for 720 kb,
					;1 for 1.2 and 1.44 MB

nrtot	db	?			;total # sectors to read

dirptr	dw	?			;pointer to array of 8 block numbers in
					; a single directory entry for CPM.SYS

blcount	db	?			;index for array of block numbers in
					; a directory entry for CPM.SYS (1...8)

dcount	db	?			;counter for number of directory
					;entries for CPM.SYS (1...2)

ptcherr	db	0			;1 = error when verifying patches

track	db	255			;number of CP/M-86 track currently in
					; track buffer (0...159)

spt	db	18			;number of physical sectors per track
					; (9/15/18 for 720KB/1.2MB/1.44MB)

bls	dw	4096			;size of a CP/M data block:
					; 2048 for 720 KB, 4096 for 1.2/1.44 MB

spb	dw	8			;physical sectors per CP/M data block:
					; 4 for 720 KB, 8 for 1.2/1.44 MB

exmcurr	db	?			;extent mask for current media

;============== end of working storage ================================

;============== start of data to be copied to old buffer ==============

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

;output from STAT DSK: for a 1.44 MB CP/M-86 diskette:
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
		db	0DBh

;output from STAT DSK: for a 720 KB CP/M-86 diskette:
;
;     X: Drive Characteristics
; 5,680: 128 Byte Record Capacity
;   710: Kilobyte Drive  Capacity
;   256: 32 Byte  Directory Entries
;   256: Checked  Directory Entries
;   128: 128 Byte Records / Directory Entry
;    16: 128 Byte Records / Block
;    36: 128 Byte Records / Track
;     2: reserved  Tracks

;------ DPB for 1.2 MB

;blocksize: we choose 4K, is 8 sectors of 512 bytes, is 32 sectors of 128 bytes
;
;1 track is 15 sectors of 512 bytes, is 60 sectors of 128 bytes, is 7.5 KB
;
;total tracks: 78 on side 0 plus 80 on side 1, total is 158 tracks
;
;total sectors of 512: 158 * 15 is 2370 sectors is 1185 kb is 296.25 blocks
;                        of 4 KB 
;total sectors of 128: 4 * 158 * 15 is 9480 is 1185 KB is 296.25 blocks 
;                        of 4 kb
;
;total capacity is thus 1185 KB is 296.25 blocks. 
;We're not supposed to use fractions. So we drop .25 block of 4 KB is 1 KB
;is 2 sectors of 512 bytes is 8 sectors of 128 bytes. So we end up with
;a capacity of 1184 KB is 296 blocks.
;
;DSM must be 295, i.e. one less than 296.
;
;direntries of 32 bytes: 128 in a 4 KB block; 16 in a sector of 512 bytes;
;                         4 in a sector of 128 bytes.
;direntries of 32 bytes: we reserve two blocks of 4 KB, is 256 entries,
;                         is 16 sectors.


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
		db	0DBh

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
		db	0DBh

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

;------ DPT for 5.25 inch, 160 and 320 KB, diskettes as supplied by CP/M-86

dpt525	equ	03AC6h			;standard CP/M-86 supplied DPT

;------ additional DPT for 3.5 inch diskettes (values taken from MS-DOS 6.2):

	db	'DPT35>>>'
dpt35:	db	0dfh,002h,025h,002h,012h,01bh,0ffh,06ch,0f6h,00fh,008h
	db	'<<<DPT35'

;------ additional DPT for 5.25 inch, 1.2 MB diskettes (values taken from C'T):

	db	'DPT12>>>'
dpt12:	db	0dfh,002h,025h,002h,00fh,01bh,0ffh,054h,0f6h,00fh,008h
	db	'<<<DPT12'

;============== end of data to be copied to old buffer ================

;============== start of code that will be made resident ==============

tcode00	equ	$

;------ this code will be placed in the old 4 KB track buffer,
;	at offset rcode00

;============== additional routine #1

;Patch #1 puts a far jump at 02D18h to this routine.
;
;The original BIOS reads all of track 0. Then it checks the last byte on the 
;very first sector of the diskette (= the boot sector) to see whether it's a
;160 KB or a 320 KB. Finally, it puts the address of the appropriate DPB into
;the DPH.
;
;New 1: To read this boot sector, the original CP/M-86 BIOS always reads
;8 sectors on track 0 as it only "knows" diskette types with 8 sectors per
;track. The patched BIOS however will read 8, 9, 15 or 18 sectors per track
;based on the type of media found in the drive (see additional routine ar200).
;For a new diskette, we do not yet know the media type. So before reading
;track 0, we temporarily set the DPB for the drive to 160 KB so we will only
;read 8 sectors from track 0.
;
;New 2: On a 1.44 MB CP/M-86 diskette, the media byte, i.e. the last byte on
;the first sector is decimal 144. On a 720 KB diskette it is 72, and on a 1.2
;MB diskette it is 12. The DPB-pointer in the current DPH is set to the
;appropriate DPB based on the value of this media byte.

;On entry:
;- BX = address of DPH for current disk (pointer to DPB is at offset 10 in DPH)
;- CS = CP/M-86 segment
;- DS = CP/M-86 segment

ar100:

;------ new: for the time being, assume 160 Kb media

	nop				;for INT 3

	mov	word ptr [bx][10],dpb160	;put 160 KB DPB in current DPH

;------ continue with some of the original code

	push	ds:[03a5eh]		;save track number for bios_settrk

	mov	ds:[03a5eh],word ptr 0	;set track number 0

;	call	near sub_33		;read track 0; routine does RETN
;------ simulate the near call to sub_33 by
;       - pushing on the stack the offset of where we want to continue
;       - performing a far jump to sub_33

	mov	ax,rcode00 + offset ar103 - tcode00
	push	ax			;offset where sub_33 should return

;	jmp	far sub_33
cps5	equ	$+3
	db	0eah			;jmp far
	dw	2C13h			;offset = label sub_33
	dw	0			;segment = cpmseg		;@@cps

ar103:					;RETN from sub_33 arrives here
	jnc	ar105			;jump if no error

;	jmp	far loc_202		;error reading track 0
cps4	equ	$+3
	db	0eah			;jmp far
	dw	3198h			;offset = label loc_202
	dw	0			;segment = cpmseg		;@@cps

ar105:
	pop	ds:[03a5eh]		;restore track from bios_settrk

;------ new: get additional media types and versions from the last bytes in
;            the diskette boot sector, and fill in the correct DPB

	push	si

	mov	si,ds:[rfidnof]		;offset of new track buffer

	mov	[bx][10],offset dpb320	;dpb 320 kb
	cmp	byte ptr [511][si],1	;media byte = 1?
	je	ar190			;yes, it's 320 kb

	mov	[bx][10],offset rdpb72p	;dpb 720 KB PCPM
	cmp	byte ptr [511][si],17	;media byte = 17?
	je	ar190			;yes, it's 720 KB PCPM

	mov	[bx][10],offset rdpb144	;dpb 1.44 mb
	cmp	byte ptr [511][si],144	;media byte = 144?
	jne	ar110			;no, not a 1.44 mb

	cmp	byte ptr [510][si],1	;media version = 1?
	je	ar190			;yes, 1.44 MB version 1

ar110:
	mov	[bx][10],offset rdpb720	;dpb 720 kb
	cmp	byte ptr [511][si],72	;media byte = 72?
	jne	ar120			;no, not a 720 kb

	cmp	byte ptr [510][si],1	;media version = 1?
	je	ar190			;yes, 720 kb version 1

ar120:
	mov	[bx][10],offset rdpb12m	;dpb 1.2 mb
	cmp	byte ptr [511][si],12	;media byte = 12?
	jne	ar180			;no, not a 1.2 mb

	cmp	byte ptr [510][si],1	;media version = 1?
	je	ar190			;yes, 1.2 mb version 1

ar180:
	mov	[bx][10],offset dpb160	;otherwise: dpb 160 kb


;------ we're done; the DPH now has a pointer to the correct DPB

ar190:
	dec	byte ptr [511][si]	;just like CP/M-86 does
					; (but why?)
	pop	si
;ar199:
	retn

;============== additional routine #2

;Patch #2 puts a far jump at 02D4Fh to this routine.
;
;The original code only supports 160 KB diskettes (40 CP/M-tracks) and 320 Kb
;diskettes (80 CP/M-tracks - the CP/M-86 BDOS does not deal with heads).
;In the original code,the bios sets up the following parameters for INT 13h to
;read a full track from a diskette:
;
;- put the number of sectors on a full track into AL (= 8, hard coded)
;- put the number of the first sector to read into CL (= 1, hard coded)
;- put the track number for PC-ROM-BIOS INT 13h into CH (0...39)
;- put the head number for PC-ROM-BIOS INT 13h into DH (0 or 1)
;
;Once this has been done, the bios translates the CP/M track numbers for
;double-sided media (0...79) to track numbers (0...39) and head numbers (0...1)
;for the PC ROM-BIOS interrupt 13h.
;
;New: more sectors per track, and more tracks per diskette. A full track on a
;1.44 MB diskette is 18 sectors = 9 KB. On a 720 kb diskette, a full track is
;9 sectors = 4.5 kb. On a 1.2 MB diskette, a full track is 15 sectors = 7.5 KB.
;All these types of media have 160 CP/M tracks.
;
;New 2: we will set the PC-ROM-BIOS interrupt vector 01Eh to a 11 bytes
;"diskette parameter table" (DPT) with the timing e.a. parameters for a 3.5
;inch (720 KB or 1.44 MB) diskette or for a 5.25 inch 1.2 MB diskette -
;depending on the diskette format that has been found by routine ar100
;coded above.
;
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
;For 720 KB and 1.44 MB, 3.5 inch diskettes we will use (source: MS-DOS 6.2):
;DF 02 25 02 12 1B FF 6C F6 0F 08.
;
;For 1.2 MB on 5.25 inch media we will use (source: C'T):
;DF 02 25 02 0F 1B FF 54 F6 0F 08.
;
;Limited testing has shown, that you can read and write 1.44 MB diskettes with 
;the standard CP/M-86 table - except that the byte at offset 04: the "last
;sector number" MUST be set to 18 (12h). To be on the safe side, we'll activate
;our own full DPT when dealing with 3.5 inch diskettes, using the same values
;as seen with MS-DOS 6.2. See below at label dpt35. For high-density 5.25 inch,
;1.2 MB diskettes we will use the table at dpt12.

;------ Determine the media type for the current drive by looking at the
;       dpb that is addressed by the dph for the current drive. Then, for
;	double-sided media only, put half the number of logical CP/M-86
;       tracks in BL (40 or 80). Track numbers >= BL will be translated
;       to head 1.
;
;       On single sided 160 KB: CPM tracks 0...39 are INT 13h tracks 0...39,
;       head 0.
;
;       On double sided 320 KB: CPM tracks 0...39 are INT 13h tracks 0...39,
;       head 0; CPM tracks 40...79 are INT 13h tracks 39...0, head 1.
;
;       For 720 KB, 1.2 MB and 1.44 MB: CPM tracks 0...79 are INT 13h tracks
;       0...79, head 0; CPM tracks 80...159 are INT 13h tracks 79...0, head 1.
;
;       So, reading all tracks on a double sided diskette involves two passes
;       over the media: first from outer to inner using head 0, then from 
;       inner to outer using head 1. That's the way the original CP/M-86 does
;	it on 320 KB double-sided diskettes; we'll use this same way for
;	720 KB and 1.44 MB diskettes.
;
;	FYI: DOS uses head 0 and then head 1 on a track, before advancing
;	to the next track, and thus needs only a single pass over the media
;       when reading all tracks on a diskette.
;
;	PCPM 720 KB does it the DOS way: even tracks are on head 0, alternating
;	with the odd tracks on head 1.

;On entry:
;- DX = CP/M-diskette-drive (0=A, 1=B...)
;- AL = CP/M-86 track number to read or write
;- CS = CP/M-86 segment
;- DS = CP/M-86 segment
;
;On exit:
;- AL = the number of sectors on a full track (8/9/15/18)
;- CL = the number of the first sector to read (always 1)
;- CH = the track number for PC-ROM-BIOS INT 13h (0...39/79)
;- DH = the head number for PC-ROM-BIOS INT 13h (0/1)
;- AH, DL, CS and DS unchanged
;- BX = don't care

ar200:
	nop				;for INT 3

	push	es

	mov	bx,0
	mov	es,bx			;ES := 0

	mov	bx,dx			;current drive A=0, B=1...
	add	bx,bx			;BX * 2, DPH-pointers are 2 bytes

	mov	bx,[bx][3aaah]		;get pointer to DPH for current drive
					;from the BIOS DPH table at 3AAAh
	mov	bx,[bx][10]		;get pointer to DPB for current DPH

;------ find out what to do, based on the current DPB

	cmp	bx,offset dpb320	;320 KB DPB?
	jne	ar205			;no

	mov	es:01eh+01eh+01eh+01eh,dpt525	;use CP/M-86's own 5.25 DD DPT

	mov	bl,40			;320 KB has 40 tracks per head
	mov	bh,8			;320 KB has 8 sectors per track
	jmp	ar240

ar205:
	cmp	bx,offset rdpb720	;720 KB DPB?
	jne	ar210			;no

	mov	es:01eh+01eh+01eh+01eh,offset rdpt35	;720 KB, 3.5 inch DPT

	mov	bl,80			;720 KB has 80 tracks per head
	mov	bh,9			;720 KB has 9 sectors per track
	jmp	ar240

ar210:
	cmp	bx,offset rdpb144	;1.44 MB DPB?
	jne	ar220			;no

	mov	es:01eh+01eh+01eh+01eh,offset rdpt35	;1.44 MB, 3.5 inch DPT

	mov	bl,80			;1.44 MB has 80 tracks per head
	mov	bh,18			;1.44 MB has 18 sectors per track
	jmp	ar240

ar220:
	cmp	bx,offset rdpb12m	;1.2 MB DPB?
	jne	ar225			;no

	mov	es:01eh+01eh+01eh+01eh,offset rdpt12	;1.2 MB, 5.25 HD DPT

	mov	bl,80			;1.2 MB has 80 tracks per head
	mov	bh,15			;1.2 MB has 15 sectors per track
	jmp	ar240

ar225:
	cmp	bx,offset rdpb72p	;720 KB DPB PCPM?
	jne	ar230			;no

	mov	es:01eh+01eh+01eh+01eh,offset rdpt35	;1.44 MB, 3.5 inch DPT

	nop				;for INT 3

	xor	dh,dh			;clear DH and carry
	rcr	al,1			;roll track number 1 bit to the right
	adc	dh,0			;put carry bit into DH (carry is 1 if
					; track number was odd: use head 1)
	mov	ch,al			;put the halved track number into CH

	mov	cl,1			;start with sector 1
	mov	al,9			;720 KB PCPM has 9 sectors per track
	jmp	ar299			;done

ar230:					;otherwise: assume single sided 160 KB

	mov	es:01eh+01eh+01eh+01eh,dpt525	;use CP/M-86's own 5.25 DD DPT

	mov	bl,40			;160 KB has 40 tracks
	mov	bh,8			;160 KB has 8 sectors per track

ar240:
	mov	ch,al			;CP/M-86 track number (0...159)
	cmp	ch,bl			;is this track on first diskette side?
	jb	ar250			;yes, use head 0 (DH was already 0
					; upon entry to this routine)
;##add comments
	mov	ch,bl		
	add	ch,bl
	dec	ch
	sub	ch,al
	mov	dh,1			;use head 1

ar250:
	mov	cl,1			;starting sector to read
	mov	al,bh			;number of sectors to read (8/9/15/18)

ar299:
	pop	es

;	jmp	far cs:loc_166h		;back to original CP/M-86 code
cps1	equ	$+3
	db	0eah			;jmp far
	dw	2d8fh			;offset = label loc_166, page 9
	dw	0			;segment = cpmseg		;@@cps

;-------------- convert word in AX to hexadecimal string at [SI] ------

;Contents of AX is NOT preserved!

w2hex:
	push	ax

	mov	al,ah
	call	b2hex			;convert AH

	pop	ax
					;fall through to convert AL

;-------------- convert byte in AL to hexadecimal string at [SI]

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

;-------------- convert lower nibble of AL to hexadecimal string at [SI];
;		before calling n2hex, make sure the high nibble of AL is zero

n2hex:
	add	al,090h
	daa
	adc	al,040h
	daa
	mov	[si],al
	inc	si

	ret
tcode99	equ	$

tcodeln	equ	tcode99 - tcode00

;============== end of code that will be made resident ================

;============== start layout of the reused 4 KB track buffer ==========

;The original 4 KB track buffer at 3BE2...4BE1 within the CP/M-86 BIOS is
;no longer used for this purpose, once the 1.44 MB feature is active. This is
;because the Feature must use a new and larger, 9 KB track buffer so a full
;18-sector track of a 1.44 MB diskette can be processed.
;
;So, the old buffer can be reused for other purposes.
;
;NOTE: be careful when referencing data through equates like the ones below.
;If you code something like "mov ax,[someword]" MASM 5.1 generates the
;opcode B8 which means "mov ax,someword". This code loads AX with the 
;constant value "someword", and NOT with the contents of memory location 
;someword. All this despite the [] around the operand...
;Work-around: write "mov ax,ds:[someword]" or any other appropriate segment
;register override to generate the correct opcode A1.

track_buf_org	equ	03BE2h		;3BE2: start of old 4 KB track buffer

progid1		equ	03BE2h		;3BE2...3BE9 ASCII text '41F4AE02'

db1		equ	03BEAh

ctrl_break_stk	equ	03CEBh		;3BEB...3CEA: 256 bytes local stack
					;for the CP/M-86 control-break handler

db2		equ	03CEBh

ccp_new_stk	equ	03DECh		;3CEC...3DEB: 256 bytes local stack
					;for the CP/M-86 CCP

db3		equ	03DECh

bdos_new_stk	equ	03EEDh		;3DED...3EEC: 256 bytes local stack
					;for the CP/M-86 BDOS

db4		equ	03EEDh

filler1		equ	03EEEh		;3EEE...3EFE: stack underflow

db5		equ	03EFFh

;------	CSV areas for 256 directory entries (drm144 = drm720 = drm12m = 255);
;       size = CKS bytes = (DRM+1)/4 bytes = 64

csv144a		equ	03F00h		;3F00...3F3F CSV buffer floppy drive A:

db6		equ	csv144a+0+64

csv144b		equ	csv144a+1+64	;3F41...3F80 CSV buffer floppy drive B:

db7		equ	csv144a+1+128

csv144c		equ	csv144a+2+128	;3F82...3FC1 CSV buffer floppy drive C:

db8		equ	csv144a+2+192

csv144d		equ	csv144a+3+192	;3FC3...4002 CSV buffer floppy drive D:

db9		equ	csv144a+3+256

;------ ALV areas for 355 data blocks (dsm144 = dsm720 = 354; dsm12m = 295);
;       size = (DSM/8)+1 bytes, then rounded up to the next integer value = 46

alv144a		equ	db9+1		;4004...4031 ALV buffer floppy drive A:

db10		equ	alv144a+0+46

alv144b		equ	alv144a+1+46	;4033...4060 ALV buffer floppy drive B:

db11		equ	alv144a+1+92

alv144c		equ	alv144a+2+92	;4062...408F ALV buffer floppy drive C:

db12		equ	alv144a+2+138

alv144d		equ	alv144a+3+138	;4091...40BE ALV buffer floppy drive D:

db13		equ	alv144a+3+184

;------ PC-ROM-BIOS Diskette Parameter Tables (DPT's)

rdpt35		equ	db13+1		;40C0...40CA DPT 3.25 inch diskettes

db14		equ	rdpt35+0+11	;40CB

rdpt12		equ	rdpt35+1+11	;40CC...40D6 DPT for 1.2 MB diskettes

db15		equ	rdpt35+1+22	;40D7

;------ CP/M-86 Disk Parameter Blocks (DBB's)

dpb160		equ	03B22h		;standard CP/M-86-supplied DPB
dpb320		equ	03B32h		;standard CP/M-86-supplied DPB

rdpb144		equ	db15+1		;40D8...40E6 new DPB for 1.44 MB

db16		equ	rdpb144+0+15	;40E7

rdpb720		equ	rdpb144+1+15	;40E8...40F6 new DPB for 720 K

db17		equ	rdpb144+1+30	;40F7

rdpb12m		equ	rdpb144+2+30	;40F8...4106 new DPB for 1.2 MB

db18		equ	rdpb144+2+45	;4107

;------ check the current location counter

IF db18 NE 04107h
	.err 144BLDR2.ASM: Offset of "db18" is incorrect. Check previous EQU's.
ENDIF

;------ resident working storage fields for the 1.44 MB Feature

reserv1		equ	04108h		;4108...4109
reserv2		equ	0410Ah		;410A...410B

rfidnof		equ	0410Ch		;410C...410D: word holding the offset
					;of the first byte of FIDD storage,
					;within the CP/M-86 segment.

db19		equ	0410Eh

rdpb72p		equ	0410Fh		;410F...411D new DPB for 720 K PCPM

db20		equ	0411Eh

;------ storage for the additional resident code for the 1.44 MB feature

rcode00		equ	0411Fh		;411F...4BE1

rcode99		equ	04BE1h

rcodeln		equ	rcode99-rcode00	;amount of space for additional code

IF	rcodeln LT tcodeln
	.err 144BLDR2.ASM: Not enough room for resident code.
ENDIF

track_buf_end	equ	04BE1h		;4BE1: end of old 4 KB track buffer


;=============== end layout of the reused 4 KB track buffer ===========

;Now check if this program is not too large... The maximum usable size of
;this program is
;- 4 KB
;- minus 128 bytes CMD header
;- minus 256 bytes zero page (PSP)
;= 0E80h = 3712 bytes
;as the boot sector program will only load the first 4 KB of a file.

hier	equ	$ 			;0F7Fh is max allowed value

IF hier-r0000 gt 0e7fh
	.err  144BLDR2.ASM: Code is longer than (4096 - 384) bytes.
ENDIF

;=============== code and data that should not be used when booting ===

m400	db	'The 1.44 MB Feature for CP/M-86 - by Freek Heite - '
	db	'version 2.0 - 16Oct2000'
	db	0dh,0ah,0dh,0ah
	db	'M400 - Sorry, this program does not work '
	db	'when it is being run under CP/M-86.'
	db	0dh,0ah
	db	'       It is only needed when booting CP/M-86 from a '
	db	'720 KB, 1.2 MB or 1.44 MB'
	db	0dh,0ah
	db	'       diskette that has been prepared by "The 1.44 '
	db	'MB Feature for CP/M-86".'
	db	'$'

k0000:
	mov	dx,offset m400
	mov	cl,9			;display text
	int	0e0h

	mov	cl,0			;return to CCP
	mov	dl,0			;free all our memory
	int	0e0h

	db	'<<<<144BLDR2<<<<'
	align	128

k9999	equ	$			;last byte of code

;============== standard MASM 5.1 epilog for a COM file ===============

x44bldr		ends

	end	r0000
