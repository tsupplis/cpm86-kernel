; Synthetic IBM BIOS and CP/M BDOS for the actual linked CMD image.
; Runs under emu2 as a DOS COM harness.  No host disks are accessed.
; BDOS deliberately corrupts registers and ES; disk contents depend on CH/DH.
bits 16
cpu 8086

%ifndef NATIVE
%define NATIVE 0
%endif
%ifndef OSVER
%define OSVER 22h
%endif
%ifndef FULL_VERSION
%define FULL_VERSION 1431h
%endif
%ifndef CONSOLE_STATE
%define CONSOLE_STATE 0
%endif
%ifndef CONSOLE_NUMBER
%define CONSOLE_NUMBER 0
%endif
%ifndef OPEN_FILES
%define OPEN_FILES 0
%endif
%ifndef OPEN_AFTER_LOCK
%define OPEN_AFTER_LOCK 0
%endif
%ifndef QUEUE_FAIL
%define QUEUE_FAIL 0
%endif
%ifndef INITIAL_KEEP
%define INITIAL_KEEP 0
%endif
%ifndef FLOPPY_COUNT
%define FLOPPY_COUNT 2
%endif
%ifndef ABORT_AT
%define ABORT_AT -1
%endif
%ifndef ABORT_WRITE
%define ABORT_WRITE -1
%endif
%ifndef EXPECT_RESET
%define EXPECT_RESET 1
%endif
%ifndef FAIL_PROBE
%define FAIL_PROBE 0
%endif
%ifndef PROBE_DRIVE
%define PROBE_DRIVE -1
%endif
%ifndef NATIVE_STATUS
%define NATIVE_STATUS 1
%endif
%ifndef EXPECT_TOUCHED
%define EXPECT_TOUCHED 0
%endif
%ifndef FAIL_NATIVE
%define FAIL_NATIVE 0
%endif
%ifndef FAIL_TIMES
%define FAIL_TIMES 1
%endif
%ifndef IS_COPY
%define IS_COPY 0
%endif
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
%if NATIVE
    mov ax,3000h
    mov es,ax
    mov word [es:28h],xios
    mov ax,cs
    mov [es:2ah],ax
    mov word [es:54h],200h
    mov word [es:88h],OPEN_FILES
    mov byte [es:105h],99
    mov word [es:106h],40h | INITIAL_KEEP
    mov word [es:110h],3100h
    mov word [es:20eh+2ch*CONSOLE_NUMBER],CONSOLE_STATE
    mov word [es:300h],FLOPPY_COUNT
    mov byte [es:406h],55h
    mov byte [es:426h],55h
    mov ax,3100h
    mov es,ax
    mov byte [es:10h],7
%endif
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
%if NATIVE
    jmp bad
%endif
    mov ax,41h ; two installed floppies
    iret

bdos:
    cmp cl,12
    je version
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
version:
    mov ax,OSVER
    jmp corrupt
output:
    mov si,dx
.find:
    lodsb
    cmp al,'k'
    jne .not_swap
    cmp byte [si],'e'
    jne .not_swap
    mov byte [cs:waiting],1
.not_swap:
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
    mov byte [cs:flushing],1
    mov al,0ffh
    jmp corrupt
raw:
    xor ax,ax
    cmp byte [cs:flushing],0
    je .not_flush
    mov byte [cs:flushing],0
    jmp corrupt
.not_flush:
%if ABORT_WRITE >= 0
    cmp word [cs:write_count],ABORT_WRITE
    jb .not_abort_write
    mov al,3
    jmp corrupt
.not_abort_write:
%endif
%if ABORT_AT >= 0
    cmp word [cs:read_count],ABORT_AT
    jb .not_abort
    mov al,3
    jmp corrupt
.not_abort:
%endif
    cmp byte [cs:waiting],0
    jne input
    cmp byte [cs:asking],0
    jne input
    jmp corrupt
input:
    mov byte [cs:waiting],0
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
%if NATIVE
    jmp bad
%endif
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
%if NATIVE
    mov byte [cs:allocated],1
    mov byte [bx+4],1
%endif
    xor ax,ax
    jmp corrupt
allocate:
%if NATIVE
    jmp bad
%endif
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
    mov ax,3000h
.normal_es:
    mov es,ax
    pop ax
    mov cx,0cccch
    std
    iret
finish:
%if NATIVE
    cmp byte [cs:invalidated],EXPECT_TOUCHED
    jne bad
    cmp byte [cs:queue_held],0
    jne bad
    mov ax,3000h
    mov es,ax
    cmp word [es:106h],40h | INITIAL_KEEP
    jne bad
    cmp byte [es:105h],99
    jne bad
    cmp word [es:20eh+2ch*CONSOLE_NUMBER],CONSOLE_STATE
    jne bad
    mov ax,3100h
    mov es,ax
    cmp byte [es:10h],7
    jne bad
%endif
    cmp word [cs:read_count],EXPECT_READS
    jne bad
    cmp word [cs:write_count],EXPECT_WRITES
    jne bad
    cmp byte [cs:reset_done],EXPECT_RESET
    jne bad_6
    mov ax,4c00h
    int 21h
bad:
    mov ax,4c01h
    int 21h

bios:
%if NATIVE
    jmp bad
%endif
disk_model:
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
%if NATIVE
    cmp ah,4
    je .nonzero
%endif
    cmp bx,0
    jne .nonzero
    ; Each 4 KiB track buffer must fit within a 64 KiB DMA page.
    push ax
    mov ax,es
    test ax,0ffh
    pop ax
    jnz bad_11
.nonzero:
%if NATIVE
    cmp ah,2
    jne .not_verify
%if IS_COPY
    cmp byte [cs:last_write],1
    jne .not_verify
    mov ah,4
    mov byte [cs:last_write],0
.not_verify:
%else
.not_verify:
%endif
%endif
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
    mov byte [cs:last_write],1
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
%if NATIVE
    mov byte [cs:formatted],1
    jmp .reset
%endif
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
    mov ax,3000h
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
    mov ax,0
%if QUEUE_FAIL == 135
    mov ax,1
%endif
    jmp corrupt
queue_read:
%if QUEUE_FAIL == 137
    mov ax,1
    jmp corrupt
%endif
    cmp byte [cs:queue_held],0
    jne bad
    mov byte [cs:queue_held],1
%if OPEN_AFTER_LOCK
    push es
    mov ax,3000h
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
    mov ax,3000h
    mov es,ax
%if EXPECT_TOUCHED & 1
    cmp byte [es:406h],0
    jne bad
%endif
%if EXPECT_TOUCHED & 2
    cmp byte [es:426h],0
    jne bad
%endif
    mov byte [cs:reset_done],1
    xor ax,ax
    jmp corrupt
xios:
    push bp
    mov bp,sp
    push ds
    pop bx
    cmp bx,3000h
    jne bad
    push es
    pop bx
    cmp bx,3100h
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
    cmp byte [es:10h],0feh
    jne bad
    cmp byte [ss:bp+15],8
    jne bad
    cmp byte [ss:bp+14],1
    ja bad
    cmp word [ss:bp+10],0
    jne bad
    mov dx,[ss:bp+12]
    cmp dx,80
    jae bad
    mov ch,dl
    xor dh,dh
    cmp ch,40
    jb .track_ready
    mov ch,79
    sub ch,dl
    inc dh
.track_ready:
    mov dl,[ss:bp+14]
    mov cl,1
    mov bx,[ss:bp+6]
    mov es,[ss:bp+8]
    cmp al,15
    je .dma_ok
    push ax
    mov ax,es
    test ax,0ffh
    pop ax
    jnz bad
.dma_ok:
%if FAIL_NATIVE
    cmp byte [cs:native_failures],FAIL_TIMES
    jae .failure_done
%if FAIL_PROBE
    cmp ch,0
    jne .failure_done
    cmp dh,1
    jne .failure_done
%if PROBE_DRIVE >= 0
    cmp dl,PROBE_DRIVE
    jne .failure_done
%endif
%endif
%if FAIL_NATIVE == 2
    cmp al,10
%elif FAIL_NATIVE == 3
    cmp al,11
%elif FAIL_NATIVE == 4
    cmp al,10
    jne .failure_done
    cmp byte [cs:last_write],1
%else
    cmp al,15
%endif
    jne .failure_done
    inc byte [cs:native_failures]
%if FAIL_NATIVE == 4
    ; Destroy scratch on a failed read; retries must still have source data.
    xor di,di
    mov cx,1000h
    mov al,0ffh
    cld
    rep stosb
%endif
    mov ax,NATIVE_STATUS
    jmp .return
.failure_done:
%endif
    cmp al,10
    jne .not_read
    mov ax,0208h
    jmp .issue
.not_read:
    cmp al,11
    jne .not_write
    mov ax,0308h
    jmp .issue
.not_write:
    cmp al,15
    jne bad
    mov ax,0508h
.issue:
    pushf
    push cs
    call disk_model
    jc .error
    xor ax,ax
    jmp .return
.error:
    mov ax,1
    jmp .return
.equipment:
    mov ax,300h
    jmp .return
.select:
    cmp dl,1
    jne bad
    mov bl,1
    shl bl,cl
    or [cs:invalidated],bl
    xor bx,bx
    mov bl,cl
    mov ax,20h
    mul bx
    add ax,400h
.return:
    mov bx,0bbbbh
    mov cx,0cccch
    mov dx,0ddddh
    mov si,0eeeeh
    mov di,0ffffh
    mov es,bx
    std
    pop bp
    retf
%endif
native_failures db 0
invalidated db 0
waiting db 0
flushing db 0
last_write db 0
queue_held db 0
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
