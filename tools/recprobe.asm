; RECPROBE.ASM - issue #17 disposable-media probe (native CP/M-86 CMD).
; MODE: 0 clean/reset, 1 dirty/reset, 2 dirty/Ctrl-C, 3 clean/no reset,
;       4 removal/read retry, 5 protected/write retry, 6 dirty/reset drive,
;       7 changed-directory/no-reset write, 8 dirty/warm boot,
;       9 dirty B: followed by relogin of A: without changing media.
; A: stays mounted; all probe file operations target B:. No kernel patches.
%ifndef TARGET
%define TARGET 2
%endif
bits 16
cpu 8086
org 0
 times 100h db 0
 push cs
 pop ds
 push cs
 pop es
 cld
 mov dx,buffer
 mov cl,26
 int 224
 mov dx,source
 mov cl,15
 int 224
 cmp al,255
 je failed
 mov dx,source
 mov cl,20
 int 224
 or al,al
 jnz failed
 cmp byte [buffer],'O'
 jne failed
 mov dx,source
 mov cl,16
 int 224
%if MODE = 1 || MODE = 2 || MODE = 6 || MODE = 8 || MODE = 9
 mov dx,target
 mov cl,22
 int 224
 cmp al,255
 je failed
 push ds
 pop es
 cld
 mov di,buffer
 mov cx,128
 mov al,'X'
 rep stosb
 mov dx,target
 mov cl,21
 int 224
 or al,al
 jnz failed
%endif
 mov dx,ready
 mov cl,9
 int 224
%if MODE = 2
 mov dx,line
 mov cl,10
 int 224
 jmp failed
%else
 ; Direct input gives the host a readiness barrier without reading a disk.
waitkey:
 mov dl,255
 mov cl,6
 int 224
 or al,al
 jz waitkey
%endif
%if MODE = 9
 mov dx,1
 mov cl,37
 int 224
 xor dx,dx
 mov cl,14
 int 224
 mov dx,target
 mov cl,16
 int 224
 cmp al,255
 je failed
%endif
%if MODE = 8
 xor cx,cx
 xor dx,dx
 int 224
%endif
%if MODE = 0 || MODE = 1 || MODE = 5
 mov cl,13
 int 224
%elif MODE = 6
 mov dx,2
 mov cl,37
 int 224
%endif
 ; Reopen after replacement; reset the FCB so stale extent state is not used.
 push ds
 pop es
 cld
 mov di,source+12
 xor ax,ax
 mov cx,12
 rep stosw
 mov dx,source
 mov cl,15
 int 224
 cmp al,255
 je failed
 mov dx,source
 mov cl,20
 int 224
 or al,al
 jnz failed
 mov al,[buffer]
 cmp al,'N'
 je newmedia
 cmp al,'O'
 jne failed
 mov dx,oldmsg
 jmp report
newmedia:
 mov dx,newmsg
report:
 mov cl,9
 int 224
%if MODE = 0 || MODE = 5 || MODE = 7
 mov dx,target
 mov cl,22
 int 224
 cmp al,255
 je failed
 push ds
 pop es
 cld
 mov di,buffer
 mov cx,128
 mov al,'Y'
 rep stosb
 mov dx,target
 mov cl,21
 int 224
 or al,al
 jnz failed
 mov dx,target
 mov cl,16
 int 224
 cmp al,255
 je failed
%endif
 mov dx,done
 mov cl,9
 int 224
 xor dx,dx
 xor cx,cx
 int 224
failed:
 mov dx,error
 mov cl,9
 int 224
 xor dx,dx
 xor cx,cx
 int 224
source db TARGET,'IDENT   DAT'
 times 24 db 0
target db TARGET,'OUTPUT  DAT'
 times 24 db 0
buffer times 128 db 0
line db 20,0
 times 22 db 0
ready db 'SWAP READY',13,10,'$'
newmsg db 'READ NEW',13,10,'$'
oldmsg db 'READ OLD',13,10,'$'
done db 'PROBE DONE',13,10,'$'
error db 'PROBE FAILED',13,10,'$'
