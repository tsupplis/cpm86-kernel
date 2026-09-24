	page ,132

;======================================================================

; 144PAT2.ASM  - version 1, initial release
; 144PAT2.ASM - version 2: added 1.2 MB support; FIDD storage only used
;               for 9 KB full track buffer; added support for PCPM 720 KB.

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

; The source code is written for Microsoft MASM 5.1.

;============== MASM 5.1 prolog for a .COM file =======================

pat2	segment para public 'code'
		assume	cs:pat2
		assume	ds:pat2
		assume	es:nothing

		org	100h

;============== start of transient program ============================

r0000:
	mov	ax,cs
	mov	es,ax

	cli
	mov	ss,ax			;switch to
	mov	sp,offset mystack	; local stack
	sti

	mov	cl,25			;return current disk
	int	0e0h
	mov	curdsk,al		;save it

;-------------- intro

r1000:
	mov	dx,offset m000		;intro
	call	dspmsg

r1099:

;-------------- check command line option

;Valid options:
;V = verbose
;3 = for testing 1.2 MB format on 3.5 inch (copies dpt12 to dpt35)

r2000:
	mov	bx,0			;index into file name in FCB's 1 and 2
r2025:
	mov	al,[bx][05dh]		;get option character from FCB 1
	call	chkopt

	mov	al,[bx][06dh]		;get option character from FCB 2
	call	chkopt

	inc	bx			;prepare for next option character
	cmp	bx,7			;all eight positions 0...7 scanned?
	jle	r2025			;no, not yet

;------

	cmp	w_3inch,0		;option 3 given?
	jz	r2099			;no

	mov	si,offset dpt35		;yes, copy DPT for 3.5 inch media
	mov	di,offset dpt12		; to DPT for 1.2 MB on 5.25 inch media
	mov	cx,11
	cld
	rep	movsb

r2099:

;-------------- check CP/M-86 version

; CP/M-86 1.x BDOS call 12 returns version 2.2

r3000:
	mov	cl,12			;get version
	int	0e0h

	cmp	bx,22h			;version 2.2?
	je	r3099			;yes

	mov	dx,offset m003		;invalid version
	jmp	stoprun

r3099:

;-------------- check for presence of diskette drives
r4000:
	int	11h			;get equipment bits

	test	al,1			;any diskette drives present?
	jnz	r4099			;yes

	mov	dx,offset m004		;no diskette drives
	jmp	stoprun

r4099:

;-------------- find CP/M-86 segment

; In a "standard" CP/M-86 system, the CP/M-86 code and data segment is 
; at 0051h. To be sure, we sample some data in the system.

; The following values are obtained:
;
; cpmseg1 segment for INT E0h from interrupt table
; cpmseg2 segment for INT E6h from interrupt table
; cpmseg3 segment returned by BDOS call 27 get addr(alloc)
; cpmseg4 segment returned by BDOS call 31 get addr(dpb)
; cpmseg5 segment returned by BDOS call 49 get addr(sysvars)
; cpmseg6 segment for INT 00h from interrupt table
; cpmseg7 segment for INT 1Bh from interrupt table
; cpmseg8 segment for INT 1Ch from interrupt table
; cpmseg9 segment for INT 1Eh from interrupt table
;
; If all these values are the same, that value is taken as the CP/M-86 segment.
;
; If not all values are the same:
;
; - if one or more of them are 0051h, the value 0051h is taken as 
;   the CP/M-86 segment;
;
; - if one or more of them are 3051h, the value 3051h is taken as 
;   the CP/M-86 segment (our DOS debugger loads CPM.SYS at segment 3051h);
;
; - otherwise, we quit as we cannot determine the value of the CP/M-86 segment.
;
; Note:
; The CP/M-86 BIOS executes an INT E2h instruction at offset 02F46, but in a
; standard system the handler for this interrupt is 0000:0000. So this CP/M-
; interrupt E2h will not help us with finding the "real" CP/M-86 segment.

r5000:
	mov	ax,0
	mov	es,ax			;set ES to zero

	mov	ax,es:0e0h+0e0h+0e0h+0e0h+2
	mov	cpmseg1,ax		;segment for INT E0h

	cmp	w_verb,0		;verbose?
	je	r5010			;no

	mov	si,offset m051a
	call	w2hex
	mov	dx,offset m051
	call	dspmsg
r5010:

	mov	ax,0
	mov	es,ax			;set ES to zero

	mov	ax,es:0e6h+0e6h+0e6h+0e6h+2
	mov	cpmseg2,ax		;segment for INT E6h

	cmp	w_verb,0		;verbose?
	je	r5030			;no

	mov	si,offset m053a
	call	w2hex
	mov	dx,offset m053
	call	dspmsg
r5030:

	mov	cl,27			;get addr(alloc)
	int	0e0h
	mov	cpmseg3,es		;segment from BDOS 27

	cmp	w_verb,0		;verbose?
	je	r5040			;no

	mov	ax,es
	mov	si,offset m054a
	call	w2hex
	mov	dx,offset m054
	call	dspmsg
r5040:

	mov	cl,31			;get addr(disk parms)
	int	0e0h
	mov	cpmseg4,es		;segment from BDOS 31

	cmp	w_verb,0		;verbose?
	je	r5050			;no

	mov	ax,es
	mov	si,offset m055a
	call	w2hex
	mov	dx,offset m055
	call	dspmsg
r5050:

	mov	cl,49			;get addr(system variables)
	int	0e0h
	mov	cpmseg5,es		;segment from BDOS 49

	cmp	w_verb,0		;verbose?
	je	r5052			;no

	mov	ax,es
	mov	si,offset m056a
	call	w2hex
	mov	dx,offset m056
	call	dspmsg
r5052:

	mov	ax,0
	mov	es,ax			;set ES to zero

	mov	ax,es:0+2
	mov	cpmseg6,ax		;segment for INT 00h

	cmp	w_verb,0		;verbose?
	je	r5053			;no

	mov	si,offset m057a
	call	w2hex
	mov	dx,offset m057
	call	dspmsg
r5053:

	mov	ax,0
	mov	es,ax			;set ES to zero

	mov	ax,es:01bh+01bh+01bh+01bh+2
	mov	cpmseg7,ax		;segment for INT 1Bh

	cmp	w_verb,0		;verbose?
	je	r5054			;no

	mov	si,offset m058a
	call	w2hex
	mov	dx,offset m058
	call	dspmsg
r5054:

	mov	ax,0
	mov	es,ax			;set ES to zero

	mov	ax,es:01ch+01ch+01ch+01ch+2
	mov	cpmseg8,ax		;segment for INT 1Ch

	cmp	w_verb,0		;verbose?
	je	r5055			;no

	mov	si,offset m05aa
	call	w2hex
	mov	dx,offset m05a
	call	dspmsg
r5055:

	mov	ax,0
	mov	es,ax			;set ES to zero

	mov	ax,es:01eh+01eh+01eh+01eh+2
	mov	cpmseg9,ax		;segment for INT 1Eh

	cmp	w_verb,0		;verbose?
	je	r5056			;no

	mov	si,offset m05ba
	call	w2hex
	mov	dx,offset m05b
	call	dspmsg
r5056:

;All segment values have been collected. Are they all the same?

	mov	ax,cpmseg1		;get first segment value
	mov	cpmseg,ax		;assume it's correct

	mov	si,offset cpmseg2
	mov	cx,nsegs-1		;compare to the nsegs-1 other values
r5058:
	cmp	ax,[si]			;equal to first value?
	jne	r5060			;no
	add	si,2			;yes
	loop	r5058			;prepare for next value

	jmp	r5090			;all the same value, done

;Are one or more segment values equal to 0051h?

r5060:
	mov	cpmseg,51h		;assume 51h, which is correct 
					; in a standard CP/M-86 system
	push	ds
	pop	es
	mov	di,offset cpmseg1

	mov	cx,nsegs		;search all cpmseg values
	mov	ax,0051h

	cld
	repnz	scasw			;search for 0051h at ES:DI
	jz	r5090			;found 0051h, done

;Are one or more of the segment values equal to 3051h?

r5070:
	mov	cpmseg,3051h		;assume 3051h (we use this when
					; debugging CP/M-86 under DOS)
	push	ds
	pop	es
	mov	di,offset cpmseg1

	mov	cx,nsegs		;search all cpmseg values
	mov	ax,3051h

	cld
	repnz	scasw			;search for 3051h at ES:DI
	jz	r5090			;found 3051h, done

;Not all values the same; and we didn't find any 0051h or 3051h

	mov	dx,offset m059		;CP/M-86 segment cannot be determined
	jmp	stoprun

r5090:
	cmp	w_verb,0		;verbose?
	je	r5099			;no

	mov	ax,cpmseg		;display CP/M-86 segment value
	mov	si,offset m005a
	call	w2hex
	mov	dx,offset m005
	call	dspmsg

r5099:

;-------------- 1.44 MB Feature program already loaded?

r5200:
	mov	es,cpmseg

	cmp	word ptr es:[progid1+0],'14'	;ASCII text '41F4AE02'
	jne	r5299
	cmp	word ptr es:[progid1+2],'4F'
	jne	r5299
	cmp	word ptr es:[progid1+4],'EA'
	jne	r5299
	cmp	word ptr es:[progid1+6],'20'
	jne	r5299

	mov	dx,offset m001		;driver already loaded
	jmp	stoprun

r5299:

;-------------- check for BIOS jump table at offset 2500h in CP/M-86 segment

; The BIOS jump table has 21 entries. All entries are supposed to be 2-byte
; short jumps plus a NOP, or 3-byte near jumps. 

r6000:
	mov	es,cpmseg
	mov	di,2500h

	mov	cx,21			;check 21 jump table entries
r6005:
	mov	al,es:[di]
	cmp	al,0e9h			;opcode for short jump?
	je	r6010			;yes
	cmp	al,0ebh			;opcode for near jump?
	jne	r6090			;no, error
r6010:
	add	di,3			;prepare for next jump table entry
	loop	r6005			
	jmp	r6095			;OK, done

r6090:
	mov	ax,cpmseg		;the CPM segment
	mov	si,offset m006a
	call	w2hex

	mov	ax,di			;offset where no jmp opcode was found
	mov	si,offset m006b
	call	w2hex

	mov	dx,offset m006		;invalid BIOS jump table entry
	jmp	stoprun

r6095:
	cmp	w_verb,0		;verbose?
	je	r6099			;no

	mov	ax,cpmseg		;the CPM segment
	mov	si,offset m061a
	call	w2hex

	mov	dx,offset m061		;BIOS jump table OK
	call	dspmsg

	call	getenter		;pause

r6099:

;-------------- find number of diskette drives known to CP/M-86

r6200:
	mov	es,cpmseg
	mov	bx,03ab2h		;CP/M-86 BIOS table data_224
	mov	cl,'A'			;counter A...D
r6210:
	mov	m062a,cl
	mov	m063a,cl
	mov	m064a,cl

	mov	al,byte ptr es:[bx]	;get a byte from the BIOS table

	cmp	al,80h			;harddisk (80h...83h)?
	jae	r6230			;yes

	cmp	al,0			;drive number is 00?
	jnz	r6220			;no, it's a valid diskette drive

	cmp	cl,'A'			;yes, 00 is only valid if drive A:
	je	r6220			;jump if indeed drive A:

	mov	dx,offset m064		;non-existent drive
	jmp	r6240

r6220:
	inc	m065a			;one more diskette drive found
	inc	nflop

	mov	si,offset m062b		;PC-ROM-BIOS diskette drive number
	call	b2hex
	mov	dx,offset m062
	jmp	r6240

r6230:
	inc	m065b			;one more hard disk found

	mov	si,offset m063b		;PC-ROM-BIOS hard disk number
	call	b2hex
	mov	dx,offset m063

r6240:
	cmp	w_verb,0		;verbose?
	je	r6250			;no

	push	bx
	push	cx

	call	dspmsg			;display drive type and INT 13h number

	pop	cx
	pop	bx

r6250:
	inc	bx			;next byte from BIOS table
	inc	cl			;next drive letter A...D
	cmp	cl,'E'			;at drive E:?
	jb	r6210			;not yet, continue

	cmp	w_verb,0		;verbose?
	je	r6299			;no
	
	mov	dx,offset m065		;number of CP/M-86 diskette drives
	call	dspmsg

r6299:

;-------------- find & show the FIDD storage descriptor ------------

r7000:
	mov	es,cpmseg		;segment of FIDD storage descriptor
	mov	ax,es
	mov	si,offset m007a		;show it (normally 0051h)
	call	w2hex

	mov	bx,es:2556h		;pointer to FIDD storage descriptor
	mov	ax,bx
	mov	si,offset m007b		;show it (normally 3AC0h)
	call	w2hex
	
	mov	ax,es:[bx]		;size of FIDD storage in KB (0...99)
	mov	fidsize,ax
	mov	si,offset m007c		;show it
	call	w2dec

	mov	ax,es:[bx][2]		;segment of FIDD storage
	mov	fidseg,ax
	mov	si,offset m007d		;show it (varying, depending on
					; number of drives)
	call	w2hex

	cmp	w_verb,0		;verbose?
	je	r7099			;no

	mov	dx,offset m007		;display FIDD storage info
	call	dspmsg

r7099:

;-------------- check amount of FIDD storage in kilobytes;

r8000:

	mov	ax,fidsize		;FIDD size in KB
	cmp	ax,fidreq		;is it enough?
	jae	r8099			;yes

	mov	si,offset m008b
	call	w2dec

	mov	ax,fidreq
	mov	si,offset m008a
	call	w2dec

	mov	dx,offset m008		;not enough FIDD storage
	jmp	stoprun

r8099:

;-------------- check that the FIDD segment is above the CP/M-86 segment

r8200:

	mov	ax,fidseg
	cmp	ax,cpmseg		;FIDD segment above CP/M-86 segment?
	ja	r8299			;yes, OK
					;no, strange....

	mov	si,offset m083a		;FIDD segment
	call	w2hex

	mov	ax,cpmseg		;CP/M-86 segment
	mov	si,offset m083b
	call	w2hex

	mov	dx,offset m083		;FIDD segment is below CP/M-86 segment
	jmp	stoprun

r8299:

;-------------- check that the first 9 KB of FIDD storage is "near"

;We want the first 9 KB of FIDD storage to be "near" to the CP/M-86, i.e. we
;want to be able to access all these 9 KB's using a segment register that 
;holds the value of the CP/M-86 code and data segment.
;
;Why do we want this: if the first KB's of FIDD storage were not "near", we
;would have to make a number of additional patches to the CP/M-86 code in
;storage.

;1 KB equals 64 16-byte paragraphs. So the FIDD segment should not be more
;than 9 * 64 = 576 paragraphs above the CP/M-86 segment.

r8300:

	mov	ax,(64 - fidreq) SHL 6	;max delta in paragraphs
	mov	si,offset m086b
	call	w2hex

	mov	ax,cpmseg
	add	ax,(64 - fidreq) SHL 6

	cmp	ax,fidseg
	jae	r8399

	mov	ax,fidseg
	sub	ax,cpmseg

	mov	si,offset m086a
	call	w2hex

	mov	dx,offset m086		;FIDD storage too high in memory
	jmp	stoprun

r8399:

;-------------- calculate the "near" offset of the first FIDD storage byte
;		relative to the CP/M-86 code and data segment

r8400:

	mov	ax,fidseg		;FIDD segment
	sub	ax,cpmseg		;minus CPM segment
	mov	cl,4			;convert from 16-byte-paragraphs
	shl	ax,cl			; to bytes
	mov	fidnof,ax		;"near" offset of first FIDD byte

	cmp	w_verb,0		;verbose?
	je	r8499			;no

	mov	si,offset m087a
	call	w2hex

	mov	dx,offset m087		;show "near" FIDD storage numbers
	call	dspmsg

r8499:

;-------------- calculate absolute address of new 9 KB buffer

r8600:

	mov	ax,fidreq
	mov	si,offset m011z
	call	w2dec

	mov	ax,cpmseg	
	mov	dx,0

	mov	cx,4
r8610:
	shl	ax,1
	rcl	dx,1
	loop	r8610

	add	ax,fidnof
	adc	dx,0

	push	ax
	push	dx

	mov	si,offset m011b		;lower four hex digits
	call	w2hex

	mov	al,dl
	and	al,0fh
	mov	si,offset m011a		;high hex digit
	call	n2hex

	pop	dx
	pop	ax

	add	ax,(fidreq SHL 10) - 1	;required FIDD storage in bytes
	adc	dx,0

	mov	si,offset m011d		;lower four hex digits
	call	w2hex

	mov	al,dl
	and	al,0fh
	mov	si,offset m011c
	call	n2hex			;high hex digit

;	mov	al,m011a
;	cmp	al,m011c
;	jnz	...			;64 KB DMA boundary crossed

	cmp	w_verb,0		;verbose?
	je	r8699			;no

	mov	dx,offset m011
	call	dspmsg

r8699:

;-------------- check patch-points

r9000:
	cmp	w_verb,0		;verbose?
	je	r9010			;no

	call	getenter		;pause

r9010:
	jmp	r9100			;jump past patch data

;General layout for a patch, where X is a single character patch ID:

;------
;offX	equ	nnnnh			;offset within CP/M-86 segment
;oldX:					;old code fragment (... bytes)
;	< old code and data >
;newX:					;new code
;	< new code and data >
;
;lenXa	equ	newX-oldX
;lenXb	equ	$-newX
;if	lenXa ne lenXb
;	.err 144PAT2.ASM R9000: Old and new lengths for patch #X are not equal
;endif
;------

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
	.err 144PAT2.ASM R9000: Old and new lengths for patch #1 are not equal
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
	.err 144PAT2.ASM R9000: Old and new lengths for patch #2 are not equal
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
	.err 144PAT2.ASM R9000: Old and new lengths for patch #3 are not equal
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
	.err 144PAT2.ASM R9000: Old and new lengths for patch #4 are not equal
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
	.err 144PAT2.ASM R9000: Old and new lengths for patch #5 are not equal
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
bdosoff	equ	00B31h
bdosstk	equ	02483h
else
ccpstk1	equ	0031Fh			;cpm.sys / cpmorg.sys
ccpstk2	equ	0035Fh
ccpstk3	equ	0035Fh
ccpstk4	equ	007DBh
bdosoff	equ	00B31h
bdosstk	equ	0248Eh
endif

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
	.err 144PAT2.ASM R9000: Old and new lengths for patch #6 are not equal
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
	.err 144PAT2.ASM R9000: Old and new lengths for patch #A are not equal
endif

;------

r9100:					;verify patch #1
	mov	m009a,'1'		;put patch number into message text
	mov	m091a,'1'

	mov	si,offset old1
	mov	di,off1
	mov	cx,len1a

	call	verify

r9200:					;verify patch #2
	mov	m009a,'2'		;put patch number into message text
	mov	m091a,'2'

	mov	si,offset old2
	mov	di,off2
	mov	cx,len2a

	call	verify

r9300:					;verify patch #3
	mov	m009a,'3'		;put patch number into message text
	mov	m091a,'3'

	mov	si,offset old3
	mov	di,off3
	mov	cx,len3a

	call	verify

r9400:					;verify patch #4
	mov	m009a,'4'		;put patch number into message text
	mov	m091a,'4'

	mov	si,offset old4
	mov	di,off4
	mov	cx,len4a

	call	verify

r9500:					;verify patch #5
	mov	m009a,'5'		;put patch number into message text
	mov	m091a,'5'

	mov	si,offset old5
	mov	di,off5
	mov	cx,len5a

	call	verify

r9600:					;verify patch #6
	mov	m009a,'6'		;put patch number into message text
	mov	m091a,'6'

	mov	si,offset old6
	mov	di,off6
	mov	cx,len6a

	call	verify

r9700:					;verify patch #7
	mov	m009a,'7'		;put patch number into message text
	mov	m091a,'7'

	mov	si,offset old7
	mov	di,off7
	mov	cx,len7a

	call	verify

r9800:					;verify patch #8
	mov	m009a,'8'		;put patch number into message text
	mov	m091a,'8'

	mov	si,offset old8
	mov	di,off8
	mov	cx,len8a

	call	verify

r9900:					;verify patch #9
	mov	m009a,'9'		;put patch number into message text
	mov	m091a,'9'

	mov	si,offset old9
	mov	di,off9
	mov	cx,len9a

	call	verify

r9a00:					;verify patch #A
	mov	m009a,'A'		;put patch number into message text
	mov	m091a,'A'

	mov	si,offset olda
	mov	di,offa
	mov	cx,lenaa

	call	verify

	cmp	ptcherr,0		;all patches OK?
	je	r9999			;yes

	mov	dx,offset m096		;one or more patches not verified
	jmp	stoprun

r9999:

	cmp	w_verb,0		;verbose:
	je	r9999A			;no

	call	getenter		;pause
r9999a:

;--------------  reset disk system

;The purpose of this routine is to flush all disk buffers.

;Resetting the disk system causes CP/M-86 to login the boot drive. If the
;system was booted from diskette, there must be a formatted diskette in
;the boot drive - otherwise, the reset will fail with an I/O error on the
;boot drive.

ra000:
	mov	cl,24			;return login vector into BX
	int	0e0h

	cmp	w_verb,0		;verbose?
	je	ra005			;no

	mov	ax,bx
	mov	si,offset m093a
	call	w2hex

	mov	dx,offset m093		;show login vector before reset
	call	dspmsg
ra005:

	mov	cl,13			;reset disk system (flush buffers)
	int	0e0h

	mov	cl,24			;return login vector into BX
	int	0e0h
	mov	logvec,bx		;save it

	cmp	w_verb,0		;verbose?
	je	ra010			;no

	mov	ax,logvec
	mov	si,offset m094a
	call	w2hex

	mov	dx,offset m094		;show login vector after reset
	call	dspmsg

;------ the one drive that is logged-in after a disk reset is the boot drive

ra010:
	mov	cx,16			;check 16 bits in BX
ra020:
	ror	logvec,1		;copies LSB to CF
	jnc	ra030			;bit not set, drive not logged in

	cmp	w_verb,0		;verbose?
	je	ra030			;no

	push	cx
	mov	dx,offset m095		;show logged-in drive (boot drive)
	call	dspmsg
	pop	cx
ra030:
	inc	m095a			;next drive letter
	loop	ra020			;next bit/drive

ra999:

;-------------- no problems found, so start making changes

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

r10299:

;-------------- sure?

	cmp	w_verb,0		;verbose?
	je	r10000			;no

	call	getenter		;pause

;-------------- update the FIDD storage descriptor

r10000:

	mov	ax,fidsize		;old FIDD size in KB
	sub	ax,fidreq		;subtract what we need in KB
	mov	fidnsize,ax		;new FIDD size in KB

	mov	si,offset m010a		;show it
	call	w2hex

	mov	ax,fidreq		;required FIDD size in KB
	mov	cl,6			;convert from KB
	shl	ax,cl			; to 16 byte paragraphs
	add	ax,fidseg		;add old FIDD segment
	mov	fidnseg,ax		;new FIDD segment

	cmp	fidnsize,0		;is the new FIDD size zero?
	jne	r10010			;no
	mov	fidnseg,0		;yes, set new FIDD segment to zero

r10010:
	mov	ax,fidnseg		;new FIDD segment
	mov	si,offset m010b		;show it
	call	w2hex

	cmp	w_verb,0		;verbose?
	je	r10090			;no

	mov	dx,offset m010		;show new FIDD segment and size
	call	dspmsg

r10090:
	mov	es,cpmseg		;the cpm segment
	mov	bx,es:2556h		;pointer to FIDD storage descriptor

	mov	ax,fidnsize
	mov	es:[bx],ax		;new FIDD size in KB

	mov	ax,fidnseg
	mov	es:[bx][2],ax		;new FIDD segment

r10099:

;-------------- patch the CP/M-86 BIOS

r13000:

	mov	m092a,'1'

	mov	si,offset new1
	mov	di,off1
	mov	cx,len1a

	call	patch

	mov	m092a,'2'

	mov	si,offset new2
	mov	di,off2
	mov	cx,len2a

	call	patch

	mov	m092a,'3'

	mov	si,offset new3
	mov	di,off3
	mov	cx,len3a

	call	patch

	mov	m092a,'4'

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

	mov	m092a,'5'

	mov	si,offset new5
	mov	di,off5
	mov	cx,len5a

	call	patch

;make patch #6

	mov	m092a,'6'

	mov	si,offset new6
	mov	di,off6
	mov	cx,len6a

	call	patch

;make patch #7

	mov	m092a,'7'

	mov	si,offset new7
	mov	di,off7
	mov	cx,len7a

	call	patch

;make patch #8

	mov	m092a,'8'

	mov	si,offset new8
	mov	di,off8
	mov	cx,len8a

	call	patch

;make patch #9

	mov	m092a,'9'

	mov	si,offset new9
	mov	di,off9
	mov	cx,len9a

	call	patch

;make patch #A

	mov	m092a,'A'

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

;------ move DPB's to old buffer

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
	mov	si,offset dpb72p
	mov	di,offset rdpb72p
	mov	cx,15
	cld
	rep	movsb

	mov	es,cpmseg
	mov	si,offset dpb12m
	mov	di,offset rdpb12m
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

	mov	es,cpmseg
	mov	si,offset tcode00
	mov	di,rcode00
	mov	cx,tcodeln
	cld
	rep	movsb

	push	cs
	pop	es

;-------------- bye

r99000:

	cmp	w_verb,0		;verbose?
	je	r99010			;no

	call	rptstak			;report stack usage

r99010:
	mov	cl,13			;reset disk system (flush buffers);
	int	0e0h			;used to activate new CSV's and ALV's

	mov	dx,offset m014		;program ended succesfully
	jmp	stoprun

r99999:

;-------------- end this program

stoprun:

	mov	cl,9
	int	0e0h			;display message at DX

	mov	cl,14			;select disk
	mov	dl,curdsk
	int	0e0h

	mov	cl,0			;return to CCP
	mov	dl,0			;free our memory
	int	0e0h

;-------------- verify a patch

verify:
	mov	es,cpmseg
	cld
	rep	cmpsb
	jz	ver990			;OK

	mov	ptcherr,1		;not OK

	dec	si
	mov	al,[si]			;expected value
	mov	si,offset m009d
	call	b2hex

	dec	di			;offset within CP/M-86 segment
	mov	ax,di			; where first mismatch occurred
	mov	si,offset m009c
	call	w2hex

	mov	al,es:[di]		;value actually found in storage
	mov	si,offset m009e
	call	b2hex	

	mov	ax,cpmseg		;CP/M-86 segment
	mov	si,offset m009b
	call	w2hex

	mov	dx,offset m009		;verify for patch #x failed
	call	dspmsg			;display string
	jmp	ver999

ver990:
	cmp	w_verb,0		;verbose?
	je	ver999			;no

	mov	dx,offset m091		;patch #X verified OK
	call	dspmsg

ver999:
	ret

;-------------- make a patch

patch:

	mov	es,cpmseg
	cld
	rep	movsb

	cmp	w_verb,0		;verbose?
	je	pat999			;no

	mov	dx,offset m092		;patch #X has been applied
	call	dspmsg

pat999:
	ret

;-------------- display message [DX] on the console

dspmsg:

	push	ds

	push	cs
	pop	ds

	mov	cl,9			;display string
	int	0e0h

	pop	ds

dspmsg99:
	ret

;-------------- hit ENTER to continue or ctrl-C to stop

getenter:

	push	ds

	push	cs
	pop	ds

	mov	dx,offset m015		;press enter or control-c
	mov	cl,9			;display string
	int	0e0h

getent10:
	mov	dl,0ffh			;console input
	mov	cl,6			;direct console I/O
	int	0e0h

	cmp	al,0dh			;enter?
	je	getent99		;yes, done

	cmp	al,3			;control-c?
	jne	getent10		;no

	mov	cl,14			;yes, restore current drive
	mov	dl,curdsk
	int	0e0h

	mov	cl,0			;return to CCP
	mov	dl,0			;free our memory
	int	0e0h

getent99:
	pop	ds

	ret

;-------------- check command line option character in AL -------------

chkopt:

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
	jne	chkop90		;no
	mov	w_verb,1	;yes
	jmp	chkop99		;return

chkop90:
	mov	m002a,al	;report an invalid option
	mov	dx,offset m002
	jmp	stoprun		;abort

chkop99:
	ret

;-------------- report stack usage --------------------------------

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

;============== end of transient program ==============================

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

ptcherr		db	0	;1 = error when verifying patches

nflop		db	0	;number of CP/M-86 diskette drives
curdsk		db	0	;current drive
logvec		dw	0	;login vector drives P...A for bits 15...0


m000	db	0dh,0ah
	db	'The 1.44 MB Feature for CP/M-86 - by Freek Heite - '
	db	'version 2.0 - 16Oct2000'
	db	0dh,0ah
	db	0dh,0ah,'$'

m001	db	'M001 - Sorry, version 2.0 of the "1.44 MB Feature" software '
	db	'is already active.'
	db	0dh,0ah,'$'

m002	db	'M002 - Sorry, invalid program option '
m002a	db	'X given. Valid options: V 3.'
	db	0dh,0ah,'$'

m003	db	'M003 - Sorry, invalid CP/M-86 version. '
	db	'This program needs version 1.1.'
	db	0dh,0ah,'$'

m004	db	'M004 - Sorry, no diskette drives in your system.'
	db	0dh,0ah,'$'

m005	db	'M005 - Ergo conclusio: the CP/M-86 code and data '
	db	'is at segment '
m005a	db	'xxxxh.'
	db	0dh,0ah,'$'

m051	db	'M051 - Segment for INT E0h BDOS call handler is '
m051a	db	'xxxxh.'
	db	0dh,0ah,'$'
m053	db	'M053 - Segment for INT E6h FIDD handler is '
m053a	db	'xxxxh.'
	db	0dh,0ah,'$'
m054	db	'M054 - Segment for ALV of current drive is '
m054a	db	'xxxxh.'
	db	0dh,0ah,'$'
m055	db	'M055 - Segment for DPB of current drive is '
m055a	db	'xxxxh.'
	db	0dh,0ah,'$'
m056	db	'M056 - Segment for CP/M-86 system variables is '
m056a	db	'xxxxh.'
	db	0dh,0ah,'$'
m057	db	'M057 - Segment for INT 00h overflow handler is '
m057a	db	'xxxxh.'
	db	0dh,0ah,'$'
m058	db	'M058 - Segment for INT 1Bh keyboard break handler is '
m058a	db	'xxxxh.'
	db	0dh,0ah,'$'
m05a	db	'M05A - Segment for INT 1Ch user timer tick handler is '
m05aa	db	'xxxxh.'
	db	0dh,0ah,'$'
m05b	db	'M05B - Segment for INT 1Eh diskette parameter table is '
m05ba	db	'xxxxh.'
	db	0dh,0ah,'$'

m059	db	'M059 - Sorry, cannot determine the CP/M-86 code & data '
	db	'segment.'
	db	0dh,0ah,'$'

m006	db	'M006 - Sorry, the BIOS jump table at address'
m006a	db	'xxxx:2500h in the CP/M-86 segment'
	db	0dh,0ah
	db	'       is invalid: there is no short or near jump '
	db	'opcode at offset '
m006b	db	'xxxxh.'
	db	0dh,0ah,'$'

m061	db	'M061 - The BIOS jump table at '
m061a	db	'xxxx:2500 has valid jump instructions.'
	db	0dh,0ah,'$'

m062	db	'M062 - CP/M-86 drive '
m062a	db	'x: is a diskette drive, INT 13h number is '
m062b	db	'xxh.'
	db	0dh,0ah,'$'

m063	db	'M063 - CP/M-86 drive '
m063a	db	'x: is a hard disk, INT 13h number is '
m063b	db	'xxh.'
	db	0dh,0ah,'$'

m064	db	'M064 - CP/M-86 drive '
m064a	db	'x: does not exist, or is not driven by your PC''s ROM BIOS.'
	db	0dh,0ah,'$'

m065	db	'M065 - Your CP/M-86 system has '
m065a	db	'0 diskette drive(s) and '
m065b	db	'0 hard disk drive(s).'
	db	0dh,0ah,'$'

m007	db	'M007 - The FIDD storage descriptor is located at '
m007a	db	'xxxx:'
m007b	db	'xxxxh;'
	db	0dh,0ah
	db	'       the FIDD segment is '
m007d	db	'xxxxh, available FIDD storage size is '
m007c	db	'?  KB.'
	db	0dh,0ah,'$'

m008	db	'M008 - Sorry, not enough storage reserved for FIDD''s: '
m008a	db	'?  KB is required,'
	db	0dh,0ah
	db	'       but only '
m008b	db	'?  KB is available.'
	db	0dh,0ah,'$'

m083	db	'M083 - Sorry, the FIDD segment is not '
	db	'above the CP/M-86 segment:'
	db	0dh,0ah
	db	'       FIDD segment is '
m083a	db	'xxxxh, CP/M-86 segment is '
m083b	db	'xxxxh.'
	db	0dh,0ah,'$'

m086	db	'M086 - Sorry, the FIDD segment is too far '
	db	'above the CP/M-86 segment:'
	db	0dh,0ah
	db	'       actual distance is '
m086a	db	'xxxx0h, maximum acceptable distance is '
m086b	db	'xxxx0h.'
	db	0dh,0ah,'$'

m087	db	'M087 - Offset of FIDD storage within the CP/M-86 segment is '
m087a	db	'xxxxh'
	db	0dh,0ah,'$'

m009	db	'M009 - Sorry, cannot make patch nr. '
m009a	db	'x at location '
m009b	db	'xxxx:'
m009c	db	'xxxxh,'
	db	0dh,0ah
	db	'       expected value is '
m009d	db	'xxh, value found is '
m009e	db	'xxh.'
	db	0dh,0ah,'$'

m091	db	'M091 - Verification for patch nr. '
m091a	db	'x is OK.'
	db	0dh,0ah,'$'

m092	db	'M092 - Patch nr. '
m092a	db	'x has been applied.'
	db	0dh,0ah,'$'

m093	db	'M093 - Login vector before "reset disk system" is '
m093a	db	'xxxxh.'
	db	0dh,0ah,'$'

m094	db	'M094 - Login vector after  "reset disk system" is '
m094a	db	'xxxxh.'
	db	0dh,0ah,'$'

m095	db	'M095 - Your CP/M-86 boot drive is '
m095a	db	'A:.'
	db	0dh,0ah,'$'

m096	db	'M096 - Sorry, one or more patches failed verification. '
	db	'Program ended.'
	db	0dh,0ah,'$'

m010	db	'M010 - New FIDD storage size in Kbytes is '
m010a	db	'xxxxh, new FIDD segment is '
m010b	db	'xxxxh.'
	db	0dh,0ah,'$'

m011	db	'M011 - New '
m011z	db	'?  KB track buffer is at address '
m011a	db	'x'
m011b	db	'xxxxh - '
m011c	db	'x'
m011d	db	'xxxxh.'
	db	0dh,0ah,'$'

m014	db	'M014 - Driver for 720KB, 1.2 MB and 1.44 MB diskettes '
	db	'loaded succesfully.'
	db	0dh,0ah,0dh,0ah
	db	'       P.S. Don''t forget to press control-C after '
	db	'changing diskettes!'
	db	0dh,0ah,'$'

m015	db	'M015 - Press ENTER to continue (or control-C to stop)'
	db	'........................'
	db	0dh,0ah,'$'

m017	db	'M017 - This program has used '
m017a	db	'xxxxh bytes on the stack.'
	db	0dh,0ah,'$'

STAKSIZ	equ	128			;size of local stack in words
endstak	equ	$
	db	STAKSIZ dup('fh')	;local stack
mystack	equ	$

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
		db	0DBh

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

;------ DPT for 5.25 inch diskettes as supplied by CP/M-86

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

;-------------- convert word in AX to hexadecimal string at [SI]

;Contents of AX is NOT preserved!

;Note: this code will be put into FIDD storage, might be helpful
;for producing debugging messages.

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

;------

tcode99	equ	$

tcodeln	equ	tcode99 - tcode00

;============== end of code that will be made resident ================

;============== start layout of the reused 4 KB track buffer ==========

;The original 4 KB track buffer at 3BE2...4BE1 within the CP/M-86 BIOS is
;no longer used for this purpose, once the 1.44 MB feature is active. This is
;because the Feature uses a new and larger, 9 KB track buffer so a full
;18-sector track of a 1.44 MB diskette can be processed.
;
;Now, the old buffer can be reused for other purposes.
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
	.err 144PAT2.ASM: Offset of "db18" is incorrect. Check previous EQU's.
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
	.err 144PAT2.ASM: Not enough room for resident code.
ENDIF

track_buf_end	equ	04BE1h		;4BE1: end of old 4 KB track buffer

;============== end layout of the reused 4 KB track buffer ============

;============== standard MASM 5.1 epilog for a .COM file ==============

pat2		ends
	end	r0000
