; RECSTATE.ASM - issue #17 termination-state probe, never patches the kernel.
; MODE 0: RETF; 1: BDOS 0; 2: Ctrl-C in BDOS 10; 3: divide-error BIOS abort.
; Leave an extra allocation and altered DMA/drive/user for recovery to handle.
bits 16
cpu 8086
org 0
 times 100h db 0
 push cs
 pop ds
 mov dx,clear
 mov cl,9
 int 224
 mov dx,allocation
 mov cl,55
 int 224
 or al,al
 jnz failed
 mov dl,7
 mov cl,32
 int 224
 mov dl,1
 mov cl,14
 int 224
 mov dx,4321h
 mov cl,26
 int 224
 mov dx,cs
 mov cl,51
 int 224
 mov dx,ready
 mov cl,9
 int 224
%if MODE = 2
 mov dx,line
 mov cl,10
 int 224
 jmp failed
%elif MODE = 3
 xor ax,ax
 xor dx,dx
 xor bx,bx
 div bx
 jmp failed
%else
 mov dx,done
 mov cl,9
 int 224
%if MODE = 0
 retf
%else
 xor cx,cx
 xor dx,dx
 int 224
%endif
%endif
failed:
 mov dx,error
 mov cl,9
 int 224
 xor dx,dx
 xor cx,cx
 int 224
allocation dw 0,100h
 db 0
line db 20,0
 times 22 db 0
clear times 24 db 13,10
 db '$'
ready db 'REC READY',13,10,'$'
done db 'REC DONE',13,10,'$'
error db 'REC FAILED',13,10,'$'
