;
;	interface module for ddt86 disassembler
;	7/15/82
;
	name	dislnk86
dgroup	group	dats
dats	segment	public	'DATS'
	db	'?'
dats	ends
cgroup	group	code
	extrn	disem:near
	public	boot
	public	conin,conout
code	segment public 'CODE'
	assume cs:cgroup
disent	proc
	org	1500h
	jmp	disem
disent	endp
boot	proc
	ret
boot	endp
conin	proc
	jmp	$-1401h
conin	endp
conout	proc
	jmp	$-1401h
conout	endp
code	ends
	end
