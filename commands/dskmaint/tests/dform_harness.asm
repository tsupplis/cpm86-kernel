; Execute DFORM's linked CMD with simulated ROM BIOS and BDOS services.
; DOS calls belong to this test harness only; no host disk is accessed.
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
    xor ax,ax
    mov es,ax
    mov word [es:78h],1234h
    mov word [es:7ah],5678h
    mov ax,cs
    add ax,(payload-$$+100h)/16
    mov es,ax
    mov byte [es:80h],tail_end-tail
    mov si,tail
    mov di,81h
    mov cx,tail_end-tail
    rep movsb
    mov ds,ax
    push ax
    mov bx,100h
    push bx
    retf

equipment:
    mov ax,EQUIPMENT
    iret
bdos:
    cmp cl,0
    je finish
    cmp cl,6
    je rawio
    cmp cl,12
    je version
    cmp cl,37
    je resetdrive
    jmp bad
version:
    mov ax,OSVER
    jmp corrupt
resetdrive:
    cmp dx,(1 << DRIVE)
    jne bad
    inc byte [cs:login_reset]
    xor ax,ax
    jmp corrupt
rawio:
    cmp dl,0ffh
    je input
    push dx
    cmp dl,'?'
    jne .print
    mov byte [cs:prompt_seen],1
.print:
    mov ah,2
    int 21h
    pop dx
    xor ax,ax
    jmp corrupt
input:
    xor ax,ax
    cmp byte [cs:prompt_seen],0
    je corrupt
    cmp byte [cs:flushed],0
    jne .answer
    mov byte [cs:flushed],1
    jmp corrupt
.answer:
    cmp byte [cs:answered],0
    jne .poll
    mov byte [cs:answered],1
    mov al,ANSWER
    jmp corrupt
.poll:
%if ABORT_VERIFY
    cmp byte [cs:write_count],1
    jne .format_poll
    mov al,3
    jmp corrupt
.format_poll:
%endif
%if ABORT_AT >= 0
    cmp byte [cs:format_count],ABORT_AT
    jb corrupt
    mov al,3
%endif
    jmp corrupt
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

bios:
    push bp
    mov bp,sp
    and word [ss:bp+6],0fffeh
    cmp ah,0
    je .success
    cmp al,8
    jne bad
    cmp cl,1
    jne bad
    cmp dl,DRIVE
    jne bad
    cmp ch,40
    jae bad
    cmp dh,SIDES
    jae bad
    cmp bx,0
    jne bad
    push ax
    mov ax,es
    test ax,0ffh
    pop ax
    jnz bad
    ; Check that the program installed DSKMAINT's parameter table.
    push ds
    push si
    push cx
    push ax
    xor ax,ax
    mov ds,ax
    lds si,[78h]
    mov cx,11
.params:
    mov bx,cx
    neg bx
    add bx,11
    mov al,[cs:params+bx]
    cmp al,[si]
    jne bad
    inc si
    loop .params
    pop ax
    pop cx
    pop si
    pop ds
%if FAIL_OP
    cmp ah,FAIL_OP
    jne .no_failure
    cmp byte [cs:failed_requests],FAIL_LIMIT
    jb .failure
.no_failure:
%endif
    cmp ah,5
    je .format
    cmp ah,3
    je .write
    cmp ah,4
    je .verify
    jmp bad
.format:
    mov al,[cs:format_count]
    call check_chs
    push cx
    push si
    mov si,0
    mov cl,1
.ids:
    cmp [es:si],ch
    jne bad
    cmp [es:si+1],dh
    jne bad
    cmp [es:si+2],cl
    jne bad
    cmp byte [es:si+3],2
    jne bad
    inc cl
    add si,4
    cmp cl,9
    jne .ids
    pop si
    pop cx
    inc byte [cs:format_count]
    jmp .success
.write:
    cmp ch,0
    jne bad
    cmp dh,0
    jne bad
    cmp byte [cs:format_count],SIDES*40
    jne bad
    push ds
    push cs
    pop ds
    mov si,expected_track
    xor di,di
    mov cx,1000h
    cld
    repe cmpsb
    jne bad
    pop ds
    inc byte [cs:write_count]
    jmp .success
.verify:
    mov al,[cs:verify_count]
    call check_chs
    inc byte [cs:verify_count]
.success:
    xor ax,ax
    pop bp
    iret
.failure:
    inc byte [cs:failed_requests]
    mov ah,FAIL_STATUS
    or word [ss:bp+6],1
    pop bp
    iret

; The second head runs backwards, exactly as in DSKMAINT.
check_chs:
    cmp al,40
    jb .head0
    neg al
    add al,79
    cmp dh,1
    jne bad
    jmp .cylinder
.head0:
    cmp dh,0
    jne bad
.cylinder:
    cmp ch,al
    jne bad
    ret

finish:
    cmp byte [cs:format_count],EXPECT_FORMATS
    jne bad
    cmp byte [cs:write_count],EXPECT_WRITES
    jne bad
    cmp byte [cs:verify_count],EXPECT_VERIFIES
    jne bad
    cmp byte [cs:failed_requests],EXPECT_FAILURES
    jne bad
    cmp byte [cs:login_reset],EXPECT_RESET
    jne bad
    xor ax,ax
    mov es,ax
    cmp word [es:78h],1234h
    jne bad
    cmp word [es:7ah],5678h
    jne bad
    mov ax,4c00h
    int 21h
bad:
    mov ax,4c01h
    int 21h

prompt_seen db 0
flushed db 0
answered db 0
format_count db 0
write_count db 0
verify_count db 0
failed_requests db 0
login_reset db 0
params db 0cfh,02h,25h,02h,08h,2ah,0ffh,50h,0e5h,19h,04h
tail db TAIL
tail_end:
expected_track:
incbin TRACK
align 16
payload:
incbin IMAGE,128
