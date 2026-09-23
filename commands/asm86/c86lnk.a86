;
        name    c86lnk
        extrn   asm86:near
cgroup  group   code
dgroup  group   const,data,stack,memory

        assume  cs:cgroup,ds:dgroup

data    segment public  'DATA'
data    ends

;  
stack   segment word stack 'STACK'
stack_base      label   byte
stack   ends
;

memory  segment memory  'MEMORY'
memory  ends

const   segment public  'CONST'

        public  fcb,fcb16,tbuff,endbuf

        org     6
endbuf  equ     $
        org     5ch
fcb     equ     $
        org     6ch
fcb16   equ     $
        org     80h
tbuff   equ     $
        org     100h

const   ends

code    segment public  'CODE'

        public  mon1,mon2

start:  mov     ax,ds
        pushf
        pop     bx
        cli
        mov     ss,ax
        lea     sp,stack_base
        push    bx
        popf
        jmp     asm86

copyright       db      ' COPYRIGHT (C) DIGITAL RESEARCH, 1981 '

        public  patch
patch:
        db      90h,90h,90h,90h,90h,90h,90h,90h
        db      90h,90h,90h,90h,90h,90h,90h,90h
        db      90h,90h,90h,90h,90h,90h,90h,90h
        db      90h,90h,90h,90h,90h,90h,90h,90h
        db      90h,90h,90h,90h,90h,90h,90h,90h
        db      90h,90h,90h,90h,90h,90h,90h,90h
        db      90h,90h,90h,90h,90h,90h,90h,90h
        db      90h,90h,90h,90h,90h,90h,90h,90h

date    db      ' 01/25/82 '

bdos:
        pop     ax      ; return address
        pop     dx
        pop     cx
        push    ax
        int     224
        ret

mon1     equ    bdos
mon2     equ    bdos
code    ends

end
