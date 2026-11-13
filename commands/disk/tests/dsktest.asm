; Synthetic IBM BIOS and CP/M BDOS for the actual linked CMD image.
; Runs under emu2 as a DOS COM harness.  No host disks are accessed.
; BDOS deliberately corrupts registers and ES; disk contents depend on CH/DH.
%ifndef SECTORS
%define SECTORS 8
%endif
%if SECTORS == 8
%define SLOT_PARAS 100h
%elif SECTORS <= 16
%define SLOT_PARAS 200h
%else
%define SLOT_PARAS 400h
%endif
%ifndef REPEAT_SECTORS
%define REPEAT_SECTORS SECTORS
%endif
%macro geom_mov 3
    mov %1,%2
%if REPEAT_SECTORS != SECTORS
    cmp byte [cs:repeated],0
    je %%done
    mov %1,%3
%%done:
%endif
%endmacro
%macro geom_cmp 3
%if REPEAT_SECTORS != SECTORS
    cmp byte [cs:repeated],0
    jne %%second
%endif
    cmp %1,%2
%if REPEAT_SECTORS != SECTORS
    jmp %%done
%%second:
    cmp %1,%3
%%done:
%endif
%endmacro
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
%ifndef SECTORS
%define SECTORS 8
%endif
%ifndef SECOND_SECTORS
%define SECOND_SECTORS SECTORS
%endif
%ifndef BPB
%define BPB 1
%endif
%ifndef EXTENDED
%define EXTENDED 0
%endif
%ifndef BAD_NINTH
%define BAD_NINTH 0
%endif
%ifndef BAD_BPB
%define BAD_BPB 0
%endif
%ifndef CYLINDERS
%define CYLINDERS 40
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
%ifdef LOAD_SEG
    push ds
    mov ds,ax
    mov si,0
    mov ax,LOAD_SEG
    mov es,ax
    xor di,di
    mov cx,payload_end-payload
    cld
    rep movsb
    pop ds
%endif
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
    cmp cl,108
    je set_status
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
set_status:
%if EXPECT_STATUS < 0
    jmp bad
%else
    cmp dx,EXPECT_STATUS
    jne bad
    cmp byte [cs:status_calls],0
    jne bad
    cmp byte [cs:queue_held],0
    jne bad
    inc byte [cs:status_calls]
    jmp corrupt
%endif
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
    cmp byte [cs:status_calls],(EXPECT_STATUS >= 0) & 1
    jne bad
%ifdef LOAD_SEG
    mov ax,LOAD_SEG
    mov es,ax
    cmp byte [es:BUFFER_START-1],'$'
    jne bad
%endif
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
    cmp ch,CYLINDERS
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
    ; Each aligned head buffer must fit within a 64 KiB DMA page.
    push ax
    mov ax,es
%if REPEAT_SECTORS != SECTORS
    cmp byte [cs:repeated],0
    jne .repeat_alignment_0
%endif
    test ax,SLOT_PARAS-1
%if REPEAT_SECTORS != SECTORS
    jmp .alignment_done_0
.repeat_alignment_0:
    test ax,(100h << (REPEAT_SECTORS != 8))-1
.alignment_done_0:
%endif
    pop ax
    jnz bad_11
    call check_bulk_bounds
.nonzero:
%if IS_COPY
    cmp ah,2
    jne .not_verify
    cmp byte [cs:last_write],1
    jne .not_verify
    mov byte [cs:verify_read],1
    mov byte [cs:last_write],0
.not_verify:
%endif
    cmp al,1
    jne .bulk_count
    cmp ah,2
    jne bad_12
    jmp .geometry_probe
.bulk_count:
    geom_cmp al,SECTORS,REPEAT_SECTORS
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
%ifdef SOURCE_FAIL
    cmp byte [cs:verify_read],0
    jne .source_ok
    cmp ch,1
    jne .source_ok
    cmp dh,0
    jne .source_ok
    mov ah,10h
    jmp .error
.source_ok:
%endif
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
    cmp byte [cs:verify_read],0
    jne .counted
    inc word [cs:read_count]
.counted:
    push cx
    push di
    push ax
    mov al,ch
    xor al,dh
    mov di,bx
    geom_mov cx,SECTORS*512,REPEAT_SECTORS*512
    cld
    rep stosb
%if SECTORS >= 9 || REPEAT_SECTORS >= 9
    geom_mov cx,SECTORS,REPEAT_SECTORS
    cmp cx,9
    jb .no_last_pattern
    mov di,bx
    geom_mov cx,(SECTORS-1)*512,(REPEAT_SECTORS-1)*512
    add di,cx
    xor al,99h
    mov cx,512
    rep stosb
.no_last_pattern:
%endif
%if MISMATCH
    cmp dl,1
    jne .same
%if MISMATCH == 4
    cmp dh,1
    jne .same
    xor byte [es:bx+SECTORS*512-1],1
%elif MISMATCH == 3
    xor byte [es:bx+SECTORS*512-1],1
%elif MISMATCH == 2
    mov byte [es:bx+(SECTORS-1)*512],0ffh
%else
    mov byte [es:bx],0ffh
%endif
.same:
%endif
%ifdef POISON_PADDING
    mov di,bx
    add di,SECTORS*512
%if SECTORS == 8
    mov cx,0
%elif SECTORS <= 16
    mov cx,2000h-SECTORS*512
%else
    mov cx,4000h-SECTORS*512
%endif
    mov al,dl
    rep stosb
%endif
%ifdef CORRUPT_VERIFY
    cmp byte [cs:verify_read],0
    je .no_corruption
    xor byte [es:bx+SECTORS*512-1],1
.no_corruption:
%endif
    mov byte [cs:verify_read],0
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
    geom_mov cx,SECTORS,REPEAT_SECTORS
    cmp cx,9
    jb .write_plain_count
    dec cx
.write_plain_count:
    push dx
    push ax
    mov ax,512
    mul cx
    mov cx,ax
    pop ax
    pop dx
    mov di,bx
    cld
    repe scasb
    jne bad_14
    geom_mov cx,SECTORS,REPEAT_SECTORS
    cmp cx,9
    jb .write_data_done
    xor al,99h
    mov cx,512
    repe scasb
    jne bad_14
.write_data_done:
    pop di
    pop cx
.reset:
    xor ah,ah
    pop bp
    iret
.format:
    ; BIOS format takes its ID count from INT 1Eh, even if AL differs.
%if !NATIVE
    push ds
    push si
    xor si,si
    mov ds,si
    lds si,[78h]
    geom_cmp byte [si+4],SECTORS,REPEAT_SECTORS
    jne bad
    pop si
    pop ds
%endif
    ; Validate every CHRN entry supplied to the formatter.
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
    geom_cmp cl,SECTORS+1,REPEAT_SECTORS+1
    jne .format_id
    mov byte [cs:formatted],1
    pop cx
    pop si
    jmp .reset
.geometry_probe:
    cmp cl,9
    jne .boot_probe
%if BAD_NINTH
    mov ah,10h
    jmp .error
%endif
    cmp dl,1
    je .second_probe
    geom_mov ax,SECTORS,REPEAT_SECTORS
    cmp ax,8
    je .absent
    jmp .probe_ok
.second_probe:
    geom_mov ax,SECOND_SECTORS,REPEAT_SECTORS
    cmp ax,8
    je .absent
.probe_ok:
    jmp .reset
.boot_probe:
    cmp cl,1
    jne bad_12
    push cx
    push di
    push ax
    mov di,bx
    mov cx,512
    xor al,al
    rep stosb
%if BPB
    mov word [es:bx+11],512
%if SECTORS > 9
    mov byte [es:bx+13],1
%else
    mov byte [es:bx+13],2
%endif
%if SECTORS > 9
    mov word [es:bx+17],224
%else
    mov word [es:bx+17],112
%endif
%if CYLINDERS == 80
%if SECTORS == 18
    mov byte [es:bx+21],0f0h
%else
    mov byte [es:bx+21],0f9h
%endif
%else
    mov byte [es:bx+21],0fdh
%endif
    mov word [es:bx+14],1
    mov byte [es:bx+16],2
%if CYLINDERS == 80
%if SECTORS == 9
    mov word [es:bx+22],3
%elif SECTORS == 15
    mov word [es:bx+22],7
%else
    mov word [es:bx+22],9
%endif
%else
    mov word [es:bx+22],2
%endif
    mov word [es:bx+26],SIDES
    geom_mov word [es:bx+24],SECTORS,REPEAT_SECTORS
    geom_mov word [es:bx+19],CYLINDERS*SIDES*SECTORS,CYLINDERS*SIDES*REPEAT_SECTORS
    cmp dl,1
    jne .boot_fields_ready
    geom_mov word [es:bx+24],SECOND_SECTORS,REPEAT_SECTORS
    geom_mov word [es:bx+19],CYLINDERS*SIDES*SECOND_SECTORS,CYLINDERS*SIDES*REPEAT_SECTORS
.boot_fields_ready:
%if BAD_BPB
    mov word [es:bx+22],0
%endif
%endif
    pop ax
    pop di
    pop cx
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

check_bulk_bounds:
    push ax
    push dx
    mov ax,es
    cmp ax,4400h
    jb .done                  ; Resident scratch, not the allocated bulk block
    geom_mov dx,SLOT_PARAS,(100h << (REPEAT_SECTORS != 8))
    add ax,dx
    jc bad
    cmp ax,4001h+MEMSIZE
    ja bad
.done:
    pop dx
    pop ax
    ret

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
    cmp byte [ss:bp+15],1
    je .count_ready
    geom_cmp byte [ss:bp+15],SECTORS,REPEAT_SECTORS
    jne bad
.count_ready:
    cmp byte [ss:bp+14],1
    ja bad
    cmp word [ss:bp+10],0
    je .sector_ready
    cmp word [ss:bp+10],8
    jne bad
.sector_ready:
    mov dx,[ss:bp+12]
    cmp al,35
    je .physical_track
    cmp al,36
    je .physical_track
    cmp dx,CYLINDERS*2
    jae bad
    mov ch,dl
    xor dh,dh
    cmp ch,CYLINDERS
    jb .track_ready
    mov ch,CYLINDERS*2-1
    sub ch,dl
    inc dh
    jmp .track_ready
.physical_track:
    mov ch,dl
.track_ready:
    mov dl,[ss:bp+14]
    mov cl,[ss:bp+10]
    inc cl
    mov bx,[ss:bp+6]
    mov es,[ss:bp+8]
    cmp al,29
    je .dma_ok
    cmp al,15
    je .dma_ok
    push ax
    mov ax,es
%if REPEAT_SECTORS != SECTORS
    cmp byte [cs:repeated],0
    jne .repeat_alignment_1
%endif
    test ax,SLOT_PARAS-1
%if REPEAT_SECTORS != SECTORS
    jmp .alignment_done_1
.repeat_alignment_1:
    test ax,(100h << (REPEAT_SECTORS != 8))-1
.alignment_done_1:
%endif
    pop ax
    jnz bad
    call check_bulk_bounds
.dma_ok:
%if FAIL_NATIVE
    cmp byte [ss:bp+15],1
    je .failure_done
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
%if EXTENDED || FULL_VERSION == 1441h
    cmp al,35
%endif
%elif FAIL_NATIVE == 3
    cmp al,11
%if EXTENDED || FULL_VERSION == 1441h
    cmp al,36
%endif
%elif FAIL_NATIVE == 4
    cmp al,10
    jne .failure_done
    cmp byte [cs:last_write],1
%else
    cmp al,15
%if EXTENDED || FULL_VERSION == 1441h
    cmp al,29
%endif
%endif
    jne .failure_done
    inc byte [cs:native_failures]
%if FAIL_NATIVE == 4
    ; Destroy scratch on a failed read; retries must still have source data.
    xor di,di
    geom_mov cx,SECTORS*512,REPEAT_SECTORS*512
    mov al,0ffh
    cld
    rep stosb
%endif
    mov ax,NATIVE_STATUS
    jmp .return
.failure_done:
%endif
    cmp al,10
    je .read_request
    cmp al,35
    je .read_request
    cmp al,11
    je .write_request
    cmp al,36
    je .write_request
    cmp al,15
    je .format_request
    cmp al,29
    jne bad
%if SECTORS == 15
    cmp word [ss:bp+16],0f654h
%elif SECTORS == 18
    cmp word [ss:bp+16],0f66ch
%else
    cmp word [ss:bp+16],0f650h
%endif
    jne bad
.format_request:
    mov ah,5
    jmp .set_count
.read_request:
    mov ah,2
    jmp .set_count
.write_request:
    mov ah,3
.set_count:
    mov al,[ss:bp+15]
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
%if EXTENDED
    cmp cx,0
    jne .normal_equipment
    cmp dx,444bh
    jne .normal_equipment
    cmp si,534bh
    jne .normal_equipment
    mov ax,4b44h
    mov dx,0101h
    pop bp
    retf
.normal_equipment:
%endif
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
status_calls db 0
native_failures db 0
invalidated db 0
waiting db 0
flushing db 0
verify_read db 0
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

payload_end:
