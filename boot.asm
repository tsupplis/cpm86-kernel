; disassembly of boot sector with ndisasm
cpu 8086
bits 16

        org 0x7C00
        cli
        mov ax,cs
        mov ds,ax
        mov ss,ax
        mov sp,0x7c00
        sti
        int 0x12
        sub ax, 0x08                ; reassembly discrepancy
        mov cl,0x6
        shl ax,cl
        mov [os_seg],ax
read_loop:
        mov ah,0x0
        int 0x13
        mov es,[os_seg]
        mov dx,0x0
        mov cx,0x5
        mov bx,0x0
        mov ax,0x204
        int 0x13
        jnc to_os
        dec byte [dsk_count]
        jnz read_loop
        jmp error                   ; reassembly discrpancy
to_os:
        jmp far [os_boot]
error:
        mov si, error_msg
        cld
        lodsb
disp_loop:
        mov ah,0xe
        sub bx,bx                   ; reassembly discrepancy
        int 0x10
        lodsb
        test al,al
        jnz disp_loop
dead_loop:
        sti
        jmp short dead_loop
os_boot:
    db  0,1
os_seg:
    dw 0
dsk_count:
    db 4
error_msg:
     db 0x0D, 0x0A, 0x0A, "*** Error while reading Loader ***", 0x0D, 0x0A
     db "Try another diskette.", 0x0D, 0x0A, 0x00

