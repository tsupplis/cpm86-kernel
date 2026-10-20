; Synthetic IBM BIOS and CP/M BDOS for the actual linked CMD image.
; Runs under emu2 as a DOS COM harness.  No host disks are accessed.
; BDOS deliberately corrupts registers and ES; disk contents depend on CH/DH.
bits 16
cpu 8086

org 100h
start:
    mov ax,cs
    mov ds,ax
    mov dx,bdos
    mov ax,25e0h
    int 21h
    mov dx,bios
    mov ax,2513h
    int 21h
    mov dx,equipment
    mov ax,2511h
    int 21h
    mov ax,cs
    add ax,(payload-$$+100h) / 16
    mov es,ax
    mov byte [es:80h],tailend-tail
    mov si,tail
    mov di,81h
    mov cx,tailend-tail
    rep movsb
    push ax
    mov bx,100h
    push bx
    mov ds,ax
    retf

equipment:
    mov ax,41h ; two installed floppies
    iret

bdos:
    cmp cl,0
    je finish
    cmp cl,9
    je output
    cmp cl,11
    je status
    cmp cl,6
    je raw
    cmp cl,1
    je input
    cmp cl,25
    je drive
    cmp cl,37
    je reset
    cmp cl,53
    je maximum
    cmp cl,55
    je allocate
    jmp bad_2
output:
    mov si,dx
.find:
    lodsb
    cmp al,'?'
    jne .next
    mov byte [cs:asking],1
.next:
    cmp al,'$'
    jne .find
    mov ah,9
    int 21h
    xor ax,ax
    jmp corrupt
status:
    xor ax,ax
    cmp byte [cs:queued],0
    je corrupt
    dec byte [cs:queued]
    mov al,0ffh
    jmp corrupt
raw:
    xor ax,ax
    jmp corrupt
input:
    mov al,' '
    cmp byte [cs:asking],0
    je corrupt
    mov al,'N'
%if REPEAT
    cmp byte [cs:repeated],0
    jne corrupt
    mov byte [cs:repeated],1
    mov byte [cs:asking],0
    mov al,'Y'
%endif
    jmp corrupt
drive:
    xor ax,ax
    jmp corrupt
reset:
    cmp dx,3
    jne bad_3
    mov byte [cs:reset_done],1
    xor ax,ax
    jmp corrupt
maximum:
%if MEMFAIL == 53
    mov ax,00ffh
    jmp corrupt
%endif
    mov bx,dx
    mov word [bx],4001h ; deliberately unaligned
    mov word [bx+2],MEMSIZE
    xor ax,ax
    jmp corrupt
allocate:
%if MEMFAIL == 55
    mov ax,00ffh
    jmp corrupt
%endif
    mov bx,dx
    cmp word [bx],4001h
    jne bad_4
    cmp byte [bx+4],0
    jne bad_5
    mov byte [cs:allocated],1
    xor ax,ax
corrupt:
    mov bx,0bbbbh
    mov cx,0cccch
    mov dx,0ddddh
    mov si,0eeeeh
    mov di,0ffffh
    mov bp,0aaaah
    push ax
    mov ax,1234h
    mov es,ax
    pop ax
    std
    iret
finish:
    cmp word [cs:read_count],EXPECT_READS
    jne bad
    cmp word [cs:write_count],EXPECT_WRITES
    jne bad
    cmp byte [cs:reset_done],1
    jne bad_6
    mov ax,4c00h
    int 21h
bad:
    mov ax,4c01h
    int 21h

bios:
    push bp
    mov bp,sp
    and word [ss:bp+6],0fffeh
    cmp ah,0
    je .reset
    cmp byte [cs:allocated],1
    jne bad_7
    cmp ch,40
    jae bad_8
    cmp dh,1
    ja bad_9
    cmp dl,1
    ja bad_10
    cmp bx,0
    jne .nonzero
    ; Each 4 KiB track buffer must fit within a 64 KiB DMA page.
    push ax
    mov ax,es
    test ax,0ffh
    pop ax
    jnz bad_11
.nonzero:
    cmp al,8
    jne bad_12
    cmp ah,2
    je .read
    cmp ah,3
    je .write
    cmp ah,4
    je .reset
    cmp ah,5
    je .format
    jmp bad_13
.read:
%if READ_RETRY
    cmp byte [cs:read_retried],0
    jne .read_retry_done
    mov byte [cs:read_retried],1
    mov ah,80h
    jmp .error
.read_retry_done:
%endif
%if SIDES == 1
    cmp dh,1
    je .absent
%endif
    inc word [cs:read_count]
    push cx
    push di
    push ax
    mov al,ch
    xor al,dh
    mov di,bx
    mov cx,1000h
    cld
    rep stosb
%if MISMATCH
    cmp dl,1
    jne .same
    mov byte [es:bx],0ffh
.same:
%endif
    pop ax
    pop di
    pop cx
    jmp .reset
.write:
%if FORCE_FORMAT
    cmp byte [cs:formatted],0
    jne .write_ready
    mov ah,4
    jmp .error
.write_ready:
%endif
    inc word [cs:write_count]
    push cx
    push di
    mov al,ch
    xor al,dh
    mov cx,1000h
    mov di,bx
    cld
    repe scasb
    jne bad_14
    pop di
    pop cx
.reset:
    xor ah,ah
    pop bp
    iret
.format:
    ; Validate all eight CHRN entries supplied to the BIOS.
    push si
    push cx
    mov si,bx
    mov cl,1
.format_id:
    cmp [es:si],ch
    jne bad
    cmp [es:si+1],dh
    jne bad
    cmp [es:si+2],cl
    jne bad
    cmp byte [es:si+3],2
    jne bad
    add si,4
    inc cl
    cmp cl,9
    jne .format_id
    mov byte [cs:formatted],1
    pop cx
    pop si
    jmp .reset
.absent:
    mov ah,4
.error:
    or word [ss:bp+6],1
    pop bp
    iret
bad_2:
    mov ax,4c02h
    int 21h

bad_3:
    mov ax,4c03h
    int 21h

bad_4:
    mov ax,4c04h
    int 21h

bad_5:
    mov ax,4c05h
    int 21h

bad_6:
    mov ax,4c06h
    int 21h

bad_7:
    mov ax,4c07h
    int 21h

bad_8:
    mov ax,4c08h
    int 21h

bad_9:
    mov ax,4c09h
    int 21h

bad_10:
    mov ax,4c0ah
    int 21h

bad_11:
    mov ax,4c0bh
    int 21h

bad_12:
    mov ax,4c0ch
    int 21h

bad_13:
    mov ax,4c0dh
    int 21h

bad_14:
    mov ax,4c0eh
    int 21h

queued db 2
repeated db 0
read_retried db 0
formatted db 0
read_count dw 0
write_count dw 0
asking db 0
allocated db 0
reset_done db 0
tail db TAIL
tailend:
align 16
payload:
incbin IMAGE,128
