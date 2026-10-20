; *-------------------------------------------------------------------------
; DISKCOMP.ASM - PC DOS 1.10 Diskette Compare Utility
;
; Build: make diskcomp.com     Verify: make check-utilities
; Original: reference/diskcomp.com, 1640 bytes; COM load address 0100h.
; Comments describe intent and register/state contracts.
; Exact addresses and bytes are kept in mappings/ and verified on rebuild.
; Reassembly is exact; runtime testing is a separate verification step.
;
; Layout:
; 0100h-0102h  code
; 01A6h-048Ah  code
; 0619h-0716h  code
; All remaining image bytes are initialized data, messages, or tables.
; The disk utilities reuse their initialization area as transfer storage.
; -------------------------------------------------------------------------

program         segment
                assume  cs:program, ds:program
                org     100h

; Preserve near jumps even when the target is in short range.
jmpn            macro   target
                db      0E9h
                dw      target - $ - 2
                endm

; Exact 8086 encodings: MASM normalizes 82h byte operations to 80h.
; Names show the operation/operand; each macro preserves the original
; encoding.

cmp82_ch                macro   imm
                db      82h,0FDh,imm
                endm

cmp82_mem               macro   addr, imm
                db      82h,3Eh
                dw      addr
                db      imm
                endm

cmp82_dh                macro   imm
                db      82h,0FEh,imm
                endm

add82_mem               macro   addr, imm
                db      82h,6h
                dw      addr
                db      imm
                endm

cmp82_ah                macro   imm
                db      82h,0FCh,imm
                endm

sub82_ah                macro   imm
                db      82h,0ECh,imm
                endm

cmp82_dl                macro   imm
                db      82h,0FAh,imm
                endm

sub82_dl                macro   imm
                db      82h,0EAh,imm
                endm

cmp82_bl                macro   imm
                db      82h,0FBh,imm
                endm

cmp82_di                macro   imm
                db      82h,3Dh,imm
                endm

; Floppy geometry and BIOS requests (eight 512-byte sectors per head).
cylinder_limit           equ     40
bios_read_track          equ     0208h
bios_write_track         equ     0308h
bios_verify_track        equ     0408h
bios_format_track        equ     0508h

; State bits carried across the buffer and disk-swap loops.
flag_one_drive           equ     1
flag_one_side            equ     2
flag_mismatch_seen       equ     4
flag_geometry_known      equ     16
flag_two_heads           equ     64

; PSP fields and fixed data addresses (equates do not emit bytes).
second_drive             equ     fcb1_name       ; Reused after drive-only argument checks.

; External memory fields and resident patch locations; image data is labeled
; below.
psp_end_segment          equ     2h
first_drive              equ     5Ch
fcb1_name                equ     5Dh
fcb2_drive               equ     6Ch
fcb2_name                equ     6Dh
command_length           equ     80h
command_tail             equ     81h

; ------------------------------------------------------------------------
; Code and initialized data in original file order
; ------------------------------------------------------------------------

; ------------------------------------------------------------------------
; COM entry point. DOS supplies the PSP and parsed default FCBs.
; ------------------------------------------------------------------------

start:
                jmpn    init
                db      "The IBM Personal Computer Diskette Compare Utility Version "
                db      "1.10 (C)Copyright IBM Corp 1981, 1982 Licensed Material - "
                db      "Program Property of IBM Author - David Litton "

; ------------------------------------------------------------------------
; Read both diskettes in buffered batches and report track/side mismatches.
; ------------------------------------------------------------------------

; Alternate which disk occupies the large buffer to reduce swaps on a
; single-drive system.
compare_again:
                mov     dx,offset msg_insert_first
                mov     ah,9h
                int     21h
                test    byte ptr ds:[compare_flags],flag_one_drive
                jz      prompt_initial_second
                mov     dx,offset msg_press_key
                int     21h
                call    wait_key
                jmpn    buffer_first_diskette

; On two drives prompt for the second disk once; single-drive use prompts at
; each swap.
prompt_initial_second:
                call    prompt_second

; Fill the large buffer from the first disk and remember its exclusive
; ending cylinder.
buffer_first_diskette:
                mov     es,word ptr ds:[bulk_buffer_segment]
; Restart comparisons at the beginning of the newly filled large buffer.
                mov     word ptr ds:[bulk_compare_segment],es
                mov     dl,ds:[first_drive]
                mov     dh,ds:[cylinders_per_buffer]
                call    read_tracks
; Small reads must stop at this same exclusive cylinder boundary.
                mov     ds:[bulk_end_cylinder],ch
                test    byte ptr ds:[compare_flags],flag_one_drive
                jz      compare_second_diskette
                call    prompt_second

; Read a small batch from disk two, then compare it against the matching
; large-buffer span.
compare_second_diskette:
                mov     es,word ptr ds:[small_buffer_segment]
; The second drive was stored in this PSP byte during initialization.
                mov     dl,ds:[second_drive]
; Two single-sided cylinders or one double-sided cylinder fit the small
; buffer.
                mov     dh,ds:[small_buffer_cylinders]
                call    read_tracks                     ; Read the next 8 KiB span from the second diskette.
                call    compare_buffers                 ; Compare that span with its corresponding part of disk one.
; Continue at the first cylinder not yet read into the small buffer.
                mov     ch,ds:[batch_end_cylinder]
; Forty cylinders exhaust the disk; no further swap is needed.
                cmp82_ch cylinder_limit
                jz      comparison_complete
                mov     ds:[current_cylinder],ch
                cmp     ch,ds:[bulk_end_cylinder]
; Consume the remainder of the large buffer before swapping its disk.
                jnz     compare_second_diskette
; The next large batch comes from disk two, reversing comparison roles.
                mov     es,word ptr ds:[bulk_buffer_segment]
                mov     word ptr ds:[bulk_compare_segment],es
                mov     dl,ds:[second_drive]
                mov     dh,ds:[cylinders_per_buffer]
                call    read_tracks
                mov     ds:[bulk_end_cylinder],ch
                test    byte ptr ds:[compare_flags],flag_one_drive
                jz      compare_first_diskette
                call    prompt_first

; After buffering disk two, reverse the roles: small reads now come from
; disk one.
compare_first_diskette:
                mov     es,word ptr ds:[small_buffer_segment]
                mov     dl,ds:[first_drive]
                mov     dh,ds:[small_buffer_cylinders]
                call    read_tracks
                call    compare_buffers
                mov     ch,ds:[batch_end_cylinder]
                cmp82_ch cylinder_limit
                jz      comparison_complete
                mov     ds:[current_cylinder],ch
                cmp     ch,ds:[bulk_end_cylinder]
                jnz     compare_first_diskette
                jmpn    buffer_first_diskette

; Only report success if no mismatch was recorded anywhere on either disk.
comparison_complete:
                test    byte ptr ds:[compare_flags],flag_mismatch_seen
                jnz     ask_compare_another
                mov     dx,offset msg_compare_ok

show_compare_status:
                mov     ah,9h
                int     21h

ask_compare_another:
                mov     dx,offset msg_compare_another
                mov     ah,9h
                int     21h
                mov     ax,0C01h
                int     21h
                or      al,20h
                cmp     al,6Eh
                jnz     check_compare_yes
                int     20h

check_compare_yes:
                cmp     al,79h
                jnz     ask_compare_another
                mov     byte ptr ds:[current_cylinder],0h
                test    byte ptr ds:[compare_flags],flag_one_side
                jnz     reset_compare_flags
                mov     byte ptr ds:[next_head],1h
                test    byte ptr ds:[compare_flags],flag_two_heads
                jz      reset_compare_flags
                mov     al,ds:[cylinders_per_buffer]
                shl     al,1
                mov     ds:[cylinders_per_buffer],al
                inc     byte ptr ds:[small_buffer_cylinders]

; Keep drive selection and /1; clear mismatch and geometry state before the
; next pair.
reset_compare_flags:
                and     byte ptr ds:[compare_flags],3h
                mov     sp,100h
                jmpn    compare_again

; ------------------------------------------------------------------------
; Display first diskette insertion prompt; enter common prompt code.
; ------------------------------------------------------------------------

prompt_first:
                mov     dx,offset msg_insert_first
                jmpn    show_insert_and_wait

; ------------------------------------------------------------------------
; Display second diskette insertion prompt, then wait for a fresh keypress.
; ------------------------------------------------------------------------

prompt_second:
                mov     dx,offset msg_insert_second

show_insert_and_wait:
                mov     ah,9h
                int     21h
                mov     dx,offset msg_press_key
                int     21h

; ------------------------------------------------------------------------
; DOS AH=0Ch / AL=01h: flush keyboard input and read a key with echo.
; ------------------------------------------------------------------------

wait_key:
                mov     ah,0Ch
                mov     al,1h
                int     21h
                ret

; ------------------------------------------------------------------------
; ES=buffer, DL=drive, DH=track count. Read tracks and probe diskette
; geometry.
; ------------------------------------------------------------------------

; DH is a cylinder count on entry, then becomes the BIOS head number. CH
; returns the exclusive end.
read_tracks:
                mov     byte ptr ds:[read_retries],0h
                mov     bp,es
                mov     cl,1h
                mov     ch,ds:[current_cylinder]
                add     ch,dh
                mov     ds:[batch_end_cylinder],ch
                sub     ch,dh
                xor     dh,dh
                cmp82_mem batch_end_cylinder, cylinder_limit
                jna     read_track_attempt
                mov     byte ptr ds:[batch_end_cylinder],cylinder_limit

read_track_attempt:
                xor     bx,bx
                mov     ax,bios_read_track
                int     13h
                jc      read_track_failed

read_track_succeeded:
                mov     byte ptr ds:[read_retries],0h
                test    byte ptr ds:[compare_flags],flag_geometry_known
                jnz     advance_read_buffer
                test    byte ptr ds:[compare_flags],flag_one_side
                jz      probe_second_side
                jmpn    select_single_sided

; A successful read of cylinder zero/head one establishes double-sided
; media.
probe_second_side:
                or      ch,ch
                jnz     advance_read_buffer
                cmp82_dh 1h
                jnz     advance_read_buffer
                or      byte ptr ds:[compare_flags],flag_geometry_known + flag_two_heads
                mov     ah,ds:[cylinders_per_buffer]
                shr     ah,1                            ; Double-sided cylinders occupy two 4 KiB head buffers.
                mov     ds:[cylinders_per_buffer],ah
                mov     ds:[batch_end_cylinder],ah
; The small buffer now contains one cylinder instead of two.
                dec     byte ptr ds:[small_buffer_cylinders]
                mov     byte ptr ds:[compare_side_count_char],32h
                call    show_sides

; Eight 512-byte sectors consume 100h paragraphs; increment the cylinder
; when heads wrap.
advance_read_buffer:
                add     bp,100h
                mov     es,bp
                xchg    dh,ds:[next_head]
                or      dh,dh
                jnz     read_track_attempt
                inc     ch
                cmp     ch,ds:[batch_end_cylinder]
                jnz     read_track_attempt
                ret

; Preserve the BIOS status over reset; retry four times before classifying
; the failure.
read_track_failed:
                push    ax
                xor     ax,ax
                int     13h
                pop     ax
                cmp     ah,80h
                jz      retry_disk_not_ready
                inc     byte ptr ds:[read_retries]
                cmp82_mem read_retries, 4h
                jnz     read_track_attempt
                call    check_geometry_error
                jnc     report_read_error
                test    byte ptr ds:[compare_flags],flag_geometry_known
                jz      discard_side_probe_buffer
                mov     dx,offset msg_incompatible_disks
                jmpn    show_compare_status

retry_disk_not_ready:
                push    dx
                mov     ds:[error_drive_char],dl
                add82_mem error_drive_char, 41h
                mov     dx,offset msg_not_ready
                mov     ah,9h
                int     21h
                mov     dx,offset error_drive_char
                int     21h
                mov     dx,offset msg_correct_then_key
                int     21h
                mov     ax,0C01h
                int     21h
                pop     dx
                jmpn    read_track_attempt

discard_side_probe_buffer:
                sub     bp,100h
                mov     es,bp

; Skip head-one reads and keep the small buffer covering two single-sided
; cylinders.
select_single_sided:
                or      byte ptr ds:[compare_flags],flag_geometry_known
                xor     dh,dh
                mov     byte ptr ds:[read_retries],0h
                mov     byte ptr ds:[compare_side_count_char],31h
                call    show_sides
                jmp     short advance_read_buffer

report_read_error:
                mov     ds:[error_drive_char],dl
                add82_mem error_drive_char, 41h
                mov     ds:[side_digit_char],dh
                or      byte ptr ds:[side_digit_char],30h
                mov     word ptr ds:[track_tens_char],3030h
                mov     ah,ch

read_error_track_tens:
                cmp82_ah 0Ah
                jc      show_read_error_location
                inc     byte ptr ds:[track_tens_char]
                sub82_ah 0Ah
                jmp     short read_error_track_tens

show_read_error_location:
                or      ds:[track_units_char],ah
                push    dx
                mov     dx,offset msg_read_error
                mov     ah,9h
                int     21h
                mov     dx,offset msg_track_side
                int     21h
                pop     dx
                jmpn    read_track_succeeded

; ------------------------------------------------------------------------
; CH=track, DH=side, AH=BIOS status. CF marks a possible single-sided
; diskette.
; ------------------------------------------------------------------------

check_geometry_error:
                or      ch,ch
                jnz     other_geometry_error_ret
                cmp82_dh 1h
                jnz     other_geometry_error_ret
                cmp82_ah 2h
                jz      possible_single_side_ret
                cmp82_ah 4h
                jnz     other_geometry_error_ret

possible_single_side_ret:
                stc
                ret

other_geometry_error_ret:
                clc
                ret

; ------------------------------------------------------------------------
; Print the current one/two-side status message; preserve DX.
; ------------------------------------------------------------------------

show_sides:
                push    dx
                mov     dx,offset msg_comparing_sides
                mov     ah,9h
                int     21h
                pop     dx
                ret

; ------------------------------------------------------------------------
; Compare buffered bytes with REPE CMPSB and report differences.
; ------------------------------------------------------------------------

; DS:SI selects the small buffer; ES:DI selects the matching 8 KiB large-
; buffer span.
compare_buffers:
                mov     si,word ptr ds:[small_buffer_offset]
                mov     es,word ptr ds:[bulk_compare_segment]
                xor     di,di
                mov     cx,2000h                        ; Each small-buffer comparison covers 8 KiB.

compare_next_span:
                jcxz    advance_compare_buffer
                repe    cmpsb
                jz      advance_compare_buffer
                call    report_mismatch
                jmp     short compare_next_span

; The caller consumed one 8 KiB span regardless of how many mismatches it
; contained.
advance_compare_buffer:
                mov     ax,word ptr ds:[bulk_compare_segment]
                add     ax,200h                         ; Advance the large-buffer cursor by one 8 KiB span.
                mov     word ptr ds:[bulk_compare_segment],ax
                ret

; ------------------------------------------------------------------------
; Report the track/side of a mismatch; adjust the remaining comparison span.
; ------------------------------------------------------------------------

report_mismatch:
                or      byte ptr ds:[compare_flags],flag_mismatch_seen
                mov     dl,ds:[current_cylinder]
                mov     dh,30h
                cmp     cx,0FFFh
                ja      mismatch_first_span
; A mismatch in the second span completes this small-buffer comparison.
                xor     cx,cx
                test    byte ptr ds:[compare_flags],flag_two_heads
                jz      mismatch_next_cylinder
                inc     dh                              ; For double-sided media this span belongs to head one.
                jmp     short format_mismatch_location

; The second 4 KiB is head one on a double-sided disk, or the next cylinder
; on a single-sided disk.
mismatch_next_cylinder:
                inc     dl
                jmp     short format_mismatch_location

; After reporting a mismatch in the first 4 KiB, skip to the second span to
; avoid duplicate reports.
mismatch_first_span:
                mov     bp,word ptr ds:[bulk_compare_segment]
                add     bp,100h
                mov     es,bp
                add     si,cx
; Skip the remainder of the first span after reporting its first mismatch.
                mov     cx,1000h
                sub     si,cx
                xor     di,di

format_mismatch_location:
                mov     ds:[side_digit_char],dh
                mov     word ptr ds:[track_tens_char],3030h

mismatch_track_tens:
                cmp82_dl 0Ah
                jc      show_mismatch_location
                inc     byte ptr ds:[track_tens_char]
                sub82_dl 0Ah
                jmp     short mismatch_track_tens

show_mismatch_location:
                mov     ds:[track_units_char],dl
                or      byte ptr ds:[track_units_char],30h
                mov     dx,offset msg_compare_errors
                mov     ah,9h
                int     21h
                mov     dx,offset msg_track_side
                int     21h
                ret

bulk_buffer_segment      label   word
                dw      0

bulk_compare_segment     label   word
                dw      0

small_buffer_segment     label   word
                dw      0

small_buffer_offset      label   word
                dw      0

current_cylinder         label   byte
                db      0h

; Head to use after the next exchange; zero permanently with /1.
next_head                label   byte
                db      0h

; Whole cylinders that fit; halved when a second head is detected.
cylinders_per_buffer     label   byte
                db      0h

; Exclusive cylinder limit for the current batch; clamped to 40.
batch_end_cylinder       label   byte
                db      0h

; Bits: one drive, /1, mismatch seen, geometry known and two heads.
compare_flags            label   byte
                db      0h

read_retries             label   byte
                db      0h

; 2 for one-sided media, 1 for two-sided media; both occupy 8 KiB.
small_buffer_cylinders   label   byte
                db      0h

bulk_end_cylinder        label   byte
                db      0h

msg_insert_first         label   byte
                db      0Dh,0Ah
                db      "Insert first diskette in drive "

first_prompt_drive       label   byte
                db      "@:"
                db      0Dh,0Ah
                db      "$"

msg_insert_second        label   byte
                db      0Dh,0Ah
                db      "Insert second diskette in drive "

second_prompt_drive      label   byte
                db      "@:"
                db      0Dh,0Ah
                db      "$"

msg_press_key            label   byte
                db      0Dh,0Ah
                db      "Strike any key when ready"
                db      0Dh,0Ah
                db      "$"

msg_compare_ok           label   byte
                db      0Dh,0Ah
                db      "Diskettes compare ok"
                db      0Dh,0Ah
                db      "$"

msg_read_error           label   byte
                db      0Dh,0Ah
                db      "Unrecoverable read error on drive "

error_drive_char         label   byte
                db      "@"
                db      0Dh,0Ah
                db      "$"

msg_track_side           label   byte
                db      "Track "

track_tens_char          label   byte
                db      0h

track_units_char         label   byte
                db      0h
                db      ", Side "

side_digit_char          label   byte
                db      0h,0Dh,0Ah,7h
                db      "$"

msg_compare_errors       label   byte
                db      0Dh,0Ah
                db      "Compare error(s) on "
                db      0Dh,0Ah
                db      "$"

msg_compare_another      label   byte
                db      0Dh,0Ah
                db      "Compare more diskettes (Y/N)?$"

msg_comparing_sides      label   byte
                db      0Dh,0Ah
                db      "Comparing "

compare_side_count_char  label   byte
                db      0h
                db      " side(s)"
                db      0Dh,0Ah
                db      "$"

msg_incompatible_disks   label   byte
                db      0Dh,0Ah
                db      "Incompatible diskette or drive types"
                db      0Dh,0Ah,7h
                db      "$"

msg_not_ready            label   byte
                db      0Dh,0Ah
                db      "Not ready error reading drive $"

msg_correct_then_key     label   byte
                db      0Dh,0Ah
                db      "Correct, then strike any key"
                db      0Dh,0Ah,7h
                db      "$"

; ------------------------------------------------------------------------
; Initialize drive selection and buffer allocation; parse the /1 option.
; ------------------------------------------------------------------------

init:
                cld
                mov     byte ptr ds:[compare_flags],0h
                mov     byte ptr ds:[next_head],1h
                mov     sp,100h
                xor     dx,dx
                push    dx
                or      ah,al
                cmp82_ah 0FFh
                jz      invalid_drive_exit
                mov     dx,offset msg_invalid_parameter
                cmp82_mem fcb1_name, 20h
                jnz     print_init_error_exit
                cmp82_mem fcb2_name, 20h
                jnz     print_init_error_exit
                mov     ah,ds:[fcb2_drive]
                mov     ds:[second_drive],ah
                int     11h
                mov     cl,6h
                shr     al,cl
                and     al,3h
                inc     al
                mov     bl,al
                mov     ah,19h
                int     21h
                inc     al
                cmp82_bl 1h
                jnz     default_first_drive
                mov     byte ptr ds:[first_drive],1h
                mov     byte ptr ds:[second_drive],1h
                jmp     short encode_drive_letters

default_first_drive:
                test    byte ptr ds:[first_drive],0FFh
                jnz     default_second_drive
                mov     ds:[first_drive],al
                jmp     short default_second_drive

invalid_drive_exit:
                mov     dx,offset msg_invalid_drive

print_init_error_exit:
                mov     ah,9h
                int     21h
                int     20h

default_second_drive:
                test    byte ptr ds:[second_drive],0FFh
                jnz     encode_drive_letters
                mov     ds:[second_drive],al

; The second drive reuses the first FCB name byte after filename validation
; has finished.
encode_drive_letters:
                mov     al,ds:[first_drive]
                or      ds:[first_prompt_drive],al
                dec     al
                mov     ds:[first_drive],al
                mov     ah,al
                mov     al,ds:[second_drive]
                or      ds:[second_prompt_drive],al
                dec     al
                mov     ds:[second_drive],al
                cmp     al,ah
                jnz     allocate_compare_buffers
                or      byte ptr ds:[compare_flags],flag_one_drive

; Reserve 8 KiB for small reads and use the remaining whole-cylinder space
; for the large buffer.
allocate_compare_buffers:
                mov     dx,offset init
                mov     cl,4h
                shr     dx,cl
                mov     ax,cs
                add     dx,ax
                xor     dl,dl
                inc     dh
                mov     word ptr ds:[small_buffer_segment],dx
                mov     bx,dx
                sub     bx,ax
                mov     cl,4h
                shl     bx,cl
                mov     word ptr ds:[small_buffer_offset],bx
                mov     ax,ds:[psp_end_segment]
                sub     ax,dx
                mov     cl,8h
                shr     ax,cl
                and     al,0FEh
; Reserve the fixed 8 KiB small-buffer span before sizing the large buffer.
                add     dx,200h
                mov     word ptr ds:[bulk_buffer_segment],dx
                mov     dx,offset msg_insufficient_memory
                cmp     ax,4h
                jc      print_init_error_exit
                sub     ax,2h
                mov     ds:[cylinders_per_buffer],al
                xor     ch,ch
                mov     cl,ds:[command_length]
                jcxz    begin_comparison
                mov     di,81h
                mov     al,2Fh
                repne   scasb
                jnz     begin_comparison
                cmp82_di 31h
                jnz     begin_comparison
                or      byte ptr ds:[compare_flags],flag_one_side
                mov     byte ptr ds:[next_head],0h

begin_comparison:
                mov     byte ptr ds:[small_buffer_cylinders],2h
                jmpn    compare_again

msg_invalid_drive        label   byte
                db      0Dh,0Ah
                db      "Invalid drive specification"
                db      7h,0Dh,0Ah
                db      "$"

msg_insufficient_memory  label   byte
                db      0Dh,0Ah
                db      "Insufficient memory"
                db      7h,0Dh,0Ah
                db      "$"

msg_invalid_parameter    label   byte
                db      0Dh,0Ah
                db      "Invalid parameter"
                db      7h,0Dh,0Ah
                db      "$"

program         ends
                end     start
