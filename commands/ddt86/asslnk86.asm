;
;	interface module for ddt86 assembler
;	7/15/82
;
	name	asslnk86
dgroup	group	dats
dats	segment	public	'DATS'
	db	'?'
dats	ends
;
cgroup	group	code
	extrn	asm:near
	public	ddtgetline
	public	goddt
	public	ddtset
;
code	segment public 'CODE'
	assume cs:cgroup
;
assent	proc
	org	2400h
	jmp	asm
assent	endp
;
ddtgetline	proc
	jmp	$-22fah
ddtgetline	endp
;
goddt	proc
	jmp	$-22fah
goddt	endp
;
ddtset	proc
	jmp	$-22fah
ddtset	endp
;
code	ends
	end
