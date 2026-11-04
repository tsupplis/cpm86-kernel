; Run the linked checker with deterministic BDOS directory and DMA services.
bits 16
cpu 8086
org 100h
%include "case.inc"
%ifndef REPAIR_FIXTURE
%define REPAIR_FIXTURE 0
%endif
%ifndef SPT
%define SPT 32
%endif
%ifndef BLM
%define BLM ((1 << BSH)-1) & 0ffh
%endif
%if REPAIR_FIXTURE
%include "raw.inc"
%endif

start:
    cld
    push cs
    pop ds
    mov dx,bdos
    mov ax,25e0h
    int 21h

    mov ax,2000h
    mov es,ax
    xor di,di
    mov si,code_image
    mov cx,code_end-code_image
    rep movsb

%if REPAIR_FIXTURE
    mov bx,RAWOPEN
    mov dx,raw_open_stub
    call patch_raw
    mov bx,RAWREAD
    mov dx,raw_read_stub
    call patch_raw
    mov bx,RAWWRITE
    mov dx,raw_write_stub
    call patch_raw
    mov bx,RAWCLOSE
    mov dx,raw_close_stub
    call patch_raw
    mov bx,RAWARM
    mov dx,raw_arm_stub
    call patch_raw
%endif
    mov ax,3000h
    mov es,ax
    xor ax,ax
    xor di,di
    mov cx,8000h
    rep stosw
    xor di,di
    mov si,data_image
    mov cx,data_end-data_image
    rep movsb
    mov ax,3000h
    mov ds,ax
    mov es,ax
    mov byte [80h],tail_end-tail
    push ds
    pop es
    push ds
    push cs
    pop ds
    mov si,tail
    mov di,81h
    mov cx,tail_end-tail
    rep movsb
    pop ds
    jmp 2000h:0

%if REPAIR_FIXTURE
patch_raw:
    mov byte [es:bx],09ah
    mov [es:bx+1],dx
    mov ax,cs
    mov [es:bx+3],ax
    mov byte [es:bx+5],0c2h
    mov word [es:bx+6],0
    cmp bx,RAWOPEN
    je patch_six
    cmp bx,RAWWRITE
    je patch_six
    cmp bx,RAWREAD
    jne patch_done
    mov word [es:bx+6],4
    ret
patch_six:
    mov word [es:bx+6],6
patch_done:
    ret

raw_open_stub:
    mov byte [cs:raw_held],0
    mov ax,RAW_OPEN_FAIL
    or ax,ax
    jnz raw_open_return
    mov byte [cs:raw_held],1
raw_open_return:
    retf
raw_close_stub:
    mov byte [cs:raw_held],0
    mov byte [cs:raw_armed],0
    retf
raw_arm_stub:
    mov byte [cs:raw_armed],1
    xor ax,ax
    retf
raw_read_stub:
    push bp
    mov bp,sp
    push ds
    push es
    push si
    push di
    push cx
    inc word [cs:raw_reads]
    mov ax,[cs:raw_reads]
    cmp ax,RAW_READ_FAIL
    je raw_read_bad
    push ds
    pop es
    push cs
    pop ds
    mov ax,[ss:bp+10]
    cmp ax,(DRM/4)
    ja raw_read_bad
    mov cl,7
    shl ax,cl
    mov si,directory
    add si,ax
    mov di,[ss:bp+8]
    mov cx,128
    cld
    rep movsb
    xor ax,ax
    jmp raw_read_done
raw_read_bad:
    mov ax,1
raw_read_done:
    pop cx
    pop di
    pop si
    pop es
    pop ds
    pop bp
    retf
raw_write_stub:
    push bp
    mov bp,sp
    push ds
    push es
    push si
    push di
    push cx
    cmp byte [cs:raw_armed],1
    jne raw_write_bad
    inc word [cs:raw_writes]
    mov ax,[cs:raw_writes]
    cmp ax,RAW_WRITE_FAIL
    je raw_write_bad
    push cs
    pop es
    mov ax,[ss:bp+12]
    cmp ax,(DRM/4)
    ja raw_write_bad
    mov cl,7
    shl ax,cl
    mov di,directory
    add di,ax
    push di
    mov si,[ss:bp+10]
    mov cx,128
    cld
    repe cmpsb
    pop di
    jne raw_write_bad
    mov si,[ss:bp+8]
    mov cx,128
    rep movsb
    mov ax,[cs:raw_writes]
    cmp ax,RAW_VERIFY_FAIL
    je raw_write_bad
    xor ax,ax
    jmp raw_write_done
raw_write_bad:
    mov ax,1
raw_write_done:
    pop cx
    pop di
    pop si
    pop es
    pop ds
    pop bp
    retf
%endif

bdos:
    push bp
    mov bp,sp
    push bx
    push cx
    push dx
    push si
    push di
    push ds
    push es
    cld
    cmp cl,0
    je finished
    cmp cl,2
    je console
%if REPAIR_FIXTURE
    cmp cl,6
    je raw_answer
    cmp cl,142
    je raw_yield
%endif
    cmp cl,12
    je get_version
    cmp cl,17
    je search_first
    cmp cl,18
    je search_next
    cmp cl,25
    je drive
    cmp cl,26
    je set_dma
    cmp cl,28
    je protect_drive
    cmp cl,29
    je get_ro_vector
    cmp cl,31
    je get_dpb
    cmp cl,32
    je set_get_user
    cmp cl,37
    je reset_drive
    cmp cl,52
    je get_dma
    jmp failed

done:
    pop es
    pop ds
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop bp
    iret

%if REPAIR_FIXTURE
raw_answer:
    mov ax,ANSWER
    jmp done
raw_yield:
    xor ax,ax
    jmp done
%endif
console:
    mov ah,2
    int 21h
    xor ax,ax
    jmp done

drive:
    xor ax,ax
    jmp done

get_version:
    mov ax,BDOS_VERSION
    jmp done

set_dma:
    mov [cs:dma],dx
    inc byte [cs:dma_sets]
    xor ax,ax
    jmp done

get_dma:
    mov ax,[cs:dma]
    mov [bp-2],ax
    mov word [bp-14],3000h
    jmp done

get_dpb:
    mov word [bp-2],dpb
    mov ax,cs
    mov [bp-14],ax
    jmp done

set_get_user:
    cmp dl,0ffh
    je get_user
    inc byte [cs:user_set_count]
    mov [cs:current_user],dl
    cmp dl,16
    jae user_set_done
    mov cl,dl
    mov ax,1
    shl ax,cl
    or [cs:user_mask],ax
user_set_done:
    xor ax,ax
    jmp done
get_user:
    mov al,[cs:current_user]
    xor ah,ah
    jmp done

protect_drive:
    inc byte [cs:protect_count]
    cmp byte [cs:protect_fail],0
    je protection_succeeds
    cmp byte [cs:protect_fail],2
    jne protection_fails
protection_succeeds:
    or word [cs:ro_vector],1
    cmp byte [cs:protect_fail],2
    je protection_fails
    xor ax,ax
    jmp done
protection_fails:
    mov ax,00ffh
    jmp done

get_ro_vector:
    inc byte [cs:ro_query_count]
    mov ax,[cs:ro_vector]
    mov [bp-2],ax
    jmp done

reset_drive:
    inc byte [cs:reset_count]
    cmp dx,1
    jne failed
    cmp byte [cs:restore_fail],0
    jne reset_fails
    and word [cs:ro_vector],0fffeh
    xor ax,ax
    jmp done
reset_fails:
    mov ax,00ffh
    jmp done

search_first:
    inc byte [cs:first_count]
    cmp byte [cs:first_count],17
    ja failed
    mov si,dx
    mov [cs:search_offset],dx
    cmp byte [si],'?'
    jne normal_search
%if (BDOS_VERSION & 0ffh) < 041h
    jmp failed
%endif
    cmp byte [cs:first_count],1
    jne failed
    mov word [cs:source],probe
    call copy_search_result
    xor ax,ax
    jmp done

normal_search:
    cmp byte [si],0
    jne failed
    cmp byte [si+12],'?'
    jne failed
    mov byte [cs:scan_started],1
    mov word [cs:cursor],0
    jmp search_entry

search_next:
    cmp byte [cs:first_count],17
    ja failed
    cmp byte [cs:scan_started],0
    je failed
    inc word [cs:cursor]
search_entry:
    mov ax,[cs:cursor]
    cmp ax,DIR_ENTRIES
    jae no_match
    and ax,0fffch
    mov cl,5
    shl ax,cl
    add ax,directory
    mov [cs:source],ax
    mov si,ax
    mov bx,[cs:cursor]
    and bx,3
    mov cl,5
    shl bx,cl
    add si,bx
    mov al,[si]
    cmp al,[cs:current_user]
    je matching_user
    inc word [cs:cursor]
    jmp search_entry
matching_user:
    call copy_search_result
    mov ax,[cs:cursor]
    and ax,3
    jmp done
no_match:
    mov ax,0ffh
    jmp done

; Real BDOS saves 33 FCB bytes, fills the DMA record, then copies the FCB back.
copy_search_result:
    mov si,[cs:search_offset]
    push cs
    pop es
    mov di,fcb_copy
    mov cx,33
    rep movsb
    push ds
    push cs
    pop ds
    mov es,[bp-12]
    mov di,[cs:dma]
    mov si,[cs:source]
    mov cx,128
    rep movsb
    mov si,fcb_copy
    mov di,[cs:search_offset]
    mov cx,33
    rep movsb
    pop ds
    ret

failed:
    mov byte [cs:exit_code],1
finished:
    cmp word [cs:dma],INITIAL_DMA
    jne failed_exit
    cmp byte [cs:dma_sets],EXPECTED_DMA_SETS
    jne failed_exit
    cmp byte [cs:first_count],EXPECTED_SEARCHES
    jne failed_exit
    cmp byte [cs:ro_query_count],EXPECTED_RO_QUERIES
    jne failed_exit
    cmp byte [cs:protect_count],EXPECTED_PROTECTS
    jne failed_exit
    cmp byte [cs:reset_count],EXPECTED_RESETS
    jne failed_exit
    cmp word [cs:ro_vector],EXPECTED_FINAL_RO
    jne failed_exit
    cmp byte [cs:user_set_count],EXPECTED_USER_SETS
    jne failed_exit
    cmp word [cs:user_mask],EXPECTED_USER_MASK
    jne failed_exit
    cmp byte [cs:current_user],INITIAL_USER
    jne failed_exit
    jmp exit
failed_exit:
    mov byte [cs:exit_code],1
exit:
%if REPAIR_FIXTURE
    cmp byte [cs:raw_held],0
    jne failed_exit
    push cs
    pop ds
    mov dx,after_name
    xor cx,cx
    mov ah,3ch
    int 21h
    jc failed_exit
    mov bx,ax
    mov dx,directory
    mov cx,((DRM+4)/4)*128
    mov ah,40h
    int 21h
    jc failed_exit
    mov ah,3eh
    int 21h
%endif
    cli
    mov ax,cs
    mov ss,ax
    mov sp,0ff00h
    mov ds,ax
    sti
    mov al,[exit_code]
    mov ah,4ch
    int 21h

%if REPAIR_FIXTURE
raw_held: db 0
raw_armed: db 0
raw_reads: dw 0
raw_writes: dw 0
after_name: db 'after.bin',0
%endif
dma: dw INITIAL_DMA
dma_sets: db 0
first_count: db 0
ro_query_count: db 0
protect_count: db 0
reset_count: db 0
user_set_count: db 0
current_user: db INITIAL_USER
user_mask: dw 0
search_offset: dw 0
scan_started: db 0
cursor: dw 0
source: dw 0
exit_code: db 0
fcb_copy: times 33 db 0
ro_vector: dw INITIAL_RO
protect_fail: db PROTECT_FAIL
restore_fail: db RESTORE_FAIL
dpb:
    dw SPT
    db BSH, BLM, EXM
    dw DSM, DRM
    db AL0, AL1
    dw 0, 1
probe:
%if DOS_MEDIA
    db 20h
    times 14 db 0
    db 80h
    times 112 db 0
%else
    db 0e5h
    times 127 db 0
%endif
directory: incbin "directory.bin"
code_image: incbin "code.bin"
code_end:
data_image: incbin "data.bin"
data_end:

%ifndef TAIL
%define TAIL "A:"
%endif
tail: db TAIL
tail_end:
