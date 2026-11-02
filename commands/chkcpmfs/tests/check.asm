; Run the linked checker with deterministic BDOS directory and DMA services.
bits 16
cpu 8086
org 100h
%include "case.inc"

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
    jmp 2000h:0

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
    cli
    mov ax,cs
    mov ss,ax
    mov sp,0ff00h
    mov ds,ax
    sti
    mov al,[exit_code]
    mov ah,4ch
    int 21h

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
    dw 32
    db BSH, ((1 << BSH)-1) & 0ffh, EXM
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
