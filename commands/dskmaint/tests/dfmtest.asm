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
%if NATIVE
    mov ax,5000h
    mov es,ax
    mov word [es:28h],xios
    mov ax,cs
    mov [es:2ah],ax
    mov word [es:54h],200h
    mov word [es:88h],OPEN_FILES
    mov byte [es:105h],99
    mov word [es:106h],40h | INITIAL_KEEP
    mov word [es:110h],5100h
    mov word [es:20eh+2ch*CONSOLE_NUMBER],CONSOLE_STATE
    mov word [es:300h],FLOPPY_COUNT
    mov word [es:406h],5555h
%endif
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
%if NATIVE
    jmp bad
%endif
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
%if NATIVE
    cmp cl,163
    je fullversion
    cmp cl,154
    je sysdata
    cmp cl,156
    je pdaddress
    cmp cl,153
    je console
    cmp cl,145
    je priority
    cmp cl,135
    je queue_open
    cmp cl,137
    je queue_read
    cmp cl,139
    je queue_write
    cmp cl,13
    je reset_all
%endif
    jmp bad
version:
    mov ax,OSVER
    jmp corrupt
resetdrive:
%if NATIVE
    jmp bad
%endif
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
    cmp cl,156
    je .keep_bx
    mov bx,0bbbbh
.keep_bx:
    mov dx,0ddddh
    mov si,0eeeeh
    mov di,0ffffh
    mov bp,0aaaah
    push ax
    mov ax,1234h
    cmp cl,154
    jne .normal_es
    mov ax,5000h
.normal_es:
    mov es,ax
    pop ax
    mov cx,0cccch
    std
    iret


%if NATIVE
fullversion:
    mov ax,FULL_VERSION
    jmp corrupt
sysdata:
    xor ax,ax
    jmp corrupt
pdaddress:
    mov bx,100h
    xor ax,ax
    jmp corrupt
console:
    mov ax,CONSOLE_NUMBER
    jmp corrupt
priority:
    push es
    mov ax,5000h
    mov es,ax
    mov [es:105h],dl
    pop es
    xor ax,ax
    jmp corrupt
queue_open:
    mov si,dx
    cmp word [si+8],'MX'
    jne bad
    cmp word [si+10],'di'
    jne bad
    mov ax,QUEUE_FAIL
    jmp corrupt
queue_read:
    cmp byte [cs:queue_held],0
    jne bad
    mov byte [cs:queue_held],1
%if OPEN_AFTER_LOCK
    push es
    mov ax,5000h
    mov es,ax
    mov word [es:88h],1
    pop es
%endif
    xor ax,ax
    jmp corrupt
queue_write:
    cmp byte [cs:queue_held],1
    jne bad
    mov byte [cs:queue_held],0
    xor ax,ax
    jmp corrupt
reset_all:
    cmp byte [cs:queue_held],0
    jne bad
    push es
    mov ax,5000h
    mov es,ax
    cmp byte [es:406h],0
    jne bad
    pop es
    inc byte [cs:login_reset]
    xor ax,ax
    jmp corrupt

; Synthetic XIOS entry. A PUSH BP supplies the same stack depth as the
; real XIOS ENTRY's internal near call to its selected disk driver.
xios:
    push bp
    mov bp,sp
    push ds
    pop bx
    cmp bx,5000h
    jne bad
    push es
    pop bx
    cmp bx,5100h
    jne bad
    cmp al,14
    je .equipment
    cmp al,9
    je .select
    cmp byte [cs:queue_held],1
    jne bad
    cmp word [106h],42h
    jne bad
    cmp byte [105h],150
    jne bad
    cmp word [20eh+2ch*CONSOLE_NUMBER],8
    jne bad
    cmp byte [ss:bp+14],DRIVE
    jne bad
    cmp byte [ss:bp+15],8
    jne bad
    cmp word [ss:bp+10],0
    jne bad
    cmp word [ss:bp+6],0
    jne bad
    mov bx,[ss:bp+8]
    test bx,0ffh
    jnz bad
    mov es,bx
    mov bx,[ss:bp+12]
    cmp bx,SIDES*40
    jae bad
    cmp al,15
    je .format
    cmp al,11
    je .write
    cmp al,10
    je .verify
    jmp bad
.equipment:
    cmp cx,0
    jne bad
    mov ax,300h
    jmp .return
.select:
    cmp cl,DRIVE
    jne bad
    mov ax,400h
    jmp .return
.format:
%if FAIL_OP == 5
    cmp byte [cs:failed_requests],FAIL_LIMIT
    jb .failed
%endif
    xor bh,bh
    cmp bl,[cs:format_count]
    jne bad
    inc byte [cs:format_count]
    xor ax,ax
    jmp .return
.write:
%if FAIL_OP == 3
    cmp byte [cs:failed_requests],FAIL_LIMIT
    jb .failed
%endif
    cmp bx,0
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
    xor ax,ax
    jmp .return
.verify:
%if FAIL_OP == 4
    cmp byte [cs:failed_requests],FAIL_LIMIT
    jb .failed
%endif
    cmp bl,[cs:verify_count]
    jne bad
    inc byte [cs:verify_count]
    xor ax,ax
    jmp .return
.failed:
    inc byte [cs:failed_requests]
    mov ax,FAIL_STATUS
.return:
    mov bx,ax
    mov cx,0cccch
    mov dx,0ddddh
    mov si,0eeeeh
    mov di,0ffffh
    pop bp
    retf
%endif
queue_held db 0

bios:
%if NATIVE
    jmp bad
%endif
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
%if NATIVE
    cmp byte [cs:queue_held],0
    jne bad
    mov ax,5000h
    mov es,ax
    cmp word [es:106h],40h | INITIAL_KEEP
    jne bad
    cmp byte [es:105h],99
    jne bad
    cmp word [es:20eh+2ch*CONSOLE_NUMBER],CONSOLE_STATE
    jne bad
%endif
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
