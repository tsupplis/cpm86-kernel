; *-------------------------------------------------------------------------
; DISKCOPY.ASM - PC DOS 1.10 Diskette Copier
;
; Build: make diskcopy.com     Verify: make check-utilities
; Original: reference/diskcopy.com, 2008 bytes; COM load address 0100h.
; Comments describe intent and register/state contracts.
; Exact addresses and bytes are kept in mappings/ and verified on rebuild.
; Reassembly is exact; runtime testing is a separate verification step.
;
; Layout:
; 0100h-0102h  code
; 019Dh-0534h  code
; 07ACh-0886h  code
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

cmp82_mem               macro   addr, imm
                db      82h,3Eh
                dw      addr
                db      imm
                endm

cmp82_dh                macro   imm
                db      82h,0FEh,imm
                endm

cmp82_ah                macro   imm
                db      82h,0FCh,imm
                endm

cmp82_bxdisp            macro   disp, imm
                db      82h,7Fh,disp,imm
                endm

sub82_ah                macro   imm
                db      82h,0ECh,imm
                endm

add82_dl                macro   imm
                db      82h,0C2h,imm
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
flag_writing             equ     8
flag_geometry_known      equ     16
flag_errors_seen         equ     32
flag_two_heads           equ     64
flag_format_target       equ     128

; PSP fields and fixed data addresses (equates do not emit bytes).
target_drive             equ     fcb1_name       ; Reused after drive-only argument checks.

; External memory fields and resident patch locations; image data is labeled
; below.
psp_end_segment          equ     2h
source_drive             equ     5Ch
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
                db      "The IBM Personal Computer Diskette Copier Version 1.10 "
                db      "(C)Copyright IBM Corp 1981, 1982 Licensed Material - "
                db      "Program Property of IBM Author - David Litton "

; ------------------------------------------------------------------------
; Prompt, read source tracks, write/verify target tracks, then offer another
; copy.
; ------------------------------------------------------------------------

; With two drives both disks stay inserted. A one-drive copy prompts before
; each swap.
copy_again:
                mov     dx,offset msg_insert_source
                mov     ah,9h
                int     21h
                test    byte ptr ds:[copy_flags],flag_one_drive
                jz      prompt_initial_target
                mov     dx,offset msg_press_key
                int     21h
                call    wait_key
                jmp     short copy_buffer_batch

prompt_initial_target:
                call    prompt_target

; Keep this source batch in memory while the same cylinders are written to
; the target.
copy_buffer_batch:
                call    read_source_tracks
                test    byte ptr ds:[copy_flags],flag_one_drive
                jz      write_buffer_batch
                call    prompt_target

; A cylinder is complete only after every selected head has been written and
; verified.
write_buffer_batch:
                call    write_target_tracks
                cmp82_mem current_cylinder, cylinder_limit
                jnz     prompt_source_if_needed
                mov     dx,offset msg_target_maybe_unusable
                test    byte ptr ds:[copy_flags],flag_errors_seen
                jnz     show_completion_status
                mov     dx,offset msg_copy_complete

show_completion_status:
                mov     ah,9h
                int     21h

; Flush queued keystrokes so the key used for the disk swap cannot answer
; this prompt.
ask_copy_another:
                mov     dx,offset msg_copy_another
                mov     ah,9h
                int     21h
                mov     ax,0C01h
                int     21h
                or      al,20h
                cmp     al,6Eh
                jnz     check_copy_yes
                int     20h

check_copy_yes:
                cmp     al,79h
                jnz     ask_copy_another
                mov     sp,100h
                mov     byte ptr ds:[current_cylinder],0h
                test    byte ptr ds:[copy_flags],flag_one_side
                jnz     reset_copy_flags
                mov     byte ptr ds:[next_head],1h
                test    byte ptr ds:[copy_flags],flag_two_heads
                jz      reset_copy_flags
                mov     al,ds:[cylinders_per_buffer]
                shl     al,1
                mov     ds:[cylinders_per_buffer],al

; Preserve drive selection and /1; rediscover media geometry for the new
; diskette.
reset_copy_flags:
                and     byte ptr ds:[copy_flags],3h
                jmpn    copy_again

; ------------------------------------------------------------------------
; For one-drive copying, request the source diskette before the next batch.
; ------------------------------------------------------------------------

prompt_source_if_needed:
                test    byte ptr ds:[copy_flags],flag_one_drive
                jz      copy_buffer_batch
                call    prompt_source
                jmp     short copy_buffer_batch

; ------------------------------------------------------------------------
; Display source insertion prompt; continue at the common prompt code.
; ------------------------------------------------------------------------

prompt_source:
                mov     dx,offset msg_insert_source
                jmp     short show_insert_and_wait

; ------------------------------------------------------------------------
; Display target insertion prompt, then wait for a fresh keypress.
; ------------------------------------------------------------------------

prompt_target:
                mov     dx,offset msg_insert_target

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
; Read source tracks through BIOS INT 13h; detect one or two sides and retry
; errors.
; ------------------------------------------------------------------------

; CH is the starting cylinder; the end cylinder is exclusive. Each head
; occupies 4 KiB.
read_source_tracks:
                and     byte ptr ds:[copy_flags],0F7h
                mov     byte ptr ds:[read_retries],0h
                mov     dl,ds:[source_drive]
                xor     dh,dh
                mov     cl,1h
                mov     ch,ds:[current_cylinder]
                add     ch,ds:[cylinders_per_buffer]
; Exclusive end of this memory batch; never read beyond cylinder 39.
                mov     ds:[batch_end_cylinder],ch
                sub     ch,ds:[cylinders_per_buffer]
                mov     es,word ptr ds:[buffer_segment]
                mov     bp,es
                cmp82_mem batch_end_cylinder, cylinder_limit
                jna     read_track_attempt
                mov     byte ptr ds:[batch_end_cylinder],cylinder_limit

; BIOS reads eight 512-byte sectors at ES:0000, starting at sector one.
read_track_attempt:
                xor     bx,bx
                mov     ax,bios_read_track
                int     13h
                jc      read_track_failed

; Probe head one only on cylinder zero; subsequent cylinders use the
; detected geometry.
read_track_succeeded:
                mov     byte ptr ds:[read_retries],0h
                test    byte ptr ds:[copy_flags],flag_geometry_known
                jnz     advance_read_buffer
                test    byte ptr ds:[copy_flags],flag_one_side
                jnz     select_single_sided
                or      ch,ch
                jnz     advance_read_buffer
                cmp82_dh 1h
                jnz     advance_read_buffer
                or      byte ptr ds:[copy_flags],flag_geometry_known + flag_two_heads
                mov     ah,ds:[cylinders_per_buffer]
                shr     ah,1                            ; Two heads consume twice the buffer space per cylinder.
                mov     ds:[cylinders_per_buffer],ah
                mov     ds:[batch_end_cylinder],ah
                mov     byte ptr ds:[copy_side_count_char],32h
                call    show_sides

; Advance ES by 100h paragraphs per head; advance CH only when the head
; wraps to zero.
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

; Reset the controller without losing AH, then distinguish not-ready from
; exhausted retries.
read_track_failed:
                push    ax
                xor     ax,ax
                int     13h
                pop     ax
                cmp     ah,80h
                jz      retry_source_not_ready
                inc     byte ptr ds:[read_retries]
                cmp82_mem read_retries, 4h
                jnz     read_track_attempt
                test    byte ptr ds:[copy_flags],flag_geometry_known
                jnz     report_source_read_error
                or      ch,ch
                jnz     report_source_read_error
                cmp82_dh 1h
                jnz     report_source_read_error
                cmp82_ah 2h
                jz      discard_side_probe_buffer
                cmp82_ah 4h
                jnz     report_source_read_error

; Head one failed the geometry probe; undo its buffer advance before
; selecting one side.
discard_side_probe_buffer:
                sub     bp,100h                         ; Undo the advance made before probing head one.
                mov     es,bp

; Do not treat a missing second head as data damage. Keep later reads on
; head zero.
select_single_sided:
                or      byte ptr ds:[copy_flags],flag_geometry_known
                xor     dh,dh
                mov     byte ptr ds:[read_retries],0h
                mov     byte ptr ds:[copy_side_count_char],31h
                call    show_sides
                jmp     short advance_read_buffer

report_source_read_error:
                mov     ax,offset msg_read_error
                call    report_disk_error
                jmpn    read_track_succeeded

retry_source_not_ready:
                call    handle_not_ready
                jmpn    read_track_attempt

; ------------------------------------------------------------------------
; Print the current one/two-side status message; preserve DX.
; ------------------------------------------------------------------------

show_sides:
                push    dx
                mov     dx,offset msg_copying_sides
                mov     ah,9h
                int     21h
                pop     dx
                ret

; ------------------------------------------------------------------------
; Write buffered tracks through INT 13h; format on demand and verify each
; track.
; ------------------------------------------------------------------------

write_target_tracks:
; This PSP byte now holds the target drive, not a filename character.
                mov     dl,ds:[target_drive]
                xor     dh,dh
                mov     cl,1h
                mov     ch,ds:[current_cylinder]
                mov     es,word ptr ds:[buffer_segment]
                mov     bp,es

; Once formatting is enabled, format both target heads before writing the
; next cylinder.
prepare_target_track:
                mov     byte ptr ds:[write_retries],0h
                mov     byte ptr ds:[verify_retries],0h
                test    byte ptr ds:[copy_flags],flag_format_target
                jz      write_track_attempt
                or      dh,dh
                jnz     write_track_attempt
                call    format_target_track

write_track_attempt:
                or      byte ptr ds:[copy_flags],flag_writing
                xor     bx,bx
                mov     ax,bios_write_track
                int     13h
                jc      write_track_failed
                call    verify_target_track
                cmp82_mem verify_retries, 0h
; Verification failed: rewrite the same buffered track before advancing.
                jnz     write_track_attempt

; The buffer advances once per head; the cylinder advances after the final
; selected head.
advance_target_side:
                xchg    dh,ds:[next_head]
                or      dh,dh
                jnz     advance_write_buffer
                inc     ch

advance_write_buffer:
                add     bp,100h
                mov     es,bp
                cmp     ch,ds:[batch_end_cylinder]
                jnz     prepare_target_track
                mov     ah,ds:[batch_end_cylinder]
                mov     ds:[current_cylinder],ah
                ret

; Write protection and not-ready remain retryable after the user corrects
; the disk.
write_track_failed:
                push    ax
                xor     ax,ax
                int     13h
                pop     ax
                cmp     ah,80h
                jz      retry_target_not_ready
                cmp82_ah 3h
                jz      retry_write_protected
                inc     byte ptr ds:[write_retries]
                cmp82_mem write_retries, 4h
                jnz     write_track_attempt
                cmp82_ah 2h
                jz      try_formatting_target
                cmp82_ah 4h
                jnz     report_target_write_error

; A missing address mark or sector may mean an unformatted target; try
; formatting it once.
try_formatting_target:
                test    byte ptr ds:[copy_flags],flag_format_target
                jnz     check_incompatible_target
                or      byte ptr ds:[copy_flags],flag_format_target
                mov     ax,offset msg_formatting_copy
                call    report_disk_error
                or      dh,dh
                jnz     rewind_target_to_side_zero
                jmpn    prepare_target_track

; Formatting starts with head zero, so rewind the buffered head when the
; failure was on head one.
rewind_target_to_side_zero:
                sub     bp,100h
                mov     es,bp
                xchg    dh,ds:[next_head]
                jmpn    prepare_target_track

report_target_write_error:
                mov     ax,offset msg_write_error
                call    report_disk_error
                jmp     short advance_target_side

retry_target_not_ready:
                call    handle_not_ready
                jmpn    write_track_attempt

retry_write_protected:
                mov     ax,offset msg_write_protected
                call    report_disk_error
                jmpn    write_track_attempt

; Failure specifically on cylinder zero, head one can indicate an
; incompatible target drive.
check_incompatible_target:
                or      ch,ch
                jnz     report_target_write_error
                cmp82_dh 1h
                jnz     report_target_write_error
                mov     dx,offset msg_incompatible_drives
                mov     ah,9h
                int     21h
                mov     dx,offset msg_target_unusable
                jmpn    show_completion_status

; ------------------------------------------------------------------------
; BIOS verify (AH=04h), with retry and not-ready handling.
; ------------------------------------------------------------------------

verify_target_track:
                and     byte ptr ds:[copy_flags],0F7h
                xor     bx,bx
                mov     ax,bios_verify_track
                int     13h
                jc      verify_track_failed
                mov     byte ptr ds:[verify_retries],0h

verify_track_ret:
                ret

; Return with the retry counter nonzero to make the caller rewrite this
; buffered track.
verify_track_failed:
                push    ax
                xor     ax,ax
                int     13h
                pop     ax
                cmp     ah,80h
                jz      retry_verify_not_ready
                inc     byte ptr ds:[verify_retries]
                cmp82_mem verify_retries, 4h
                jnz     verify_track_ret
                mov     ax,offset msg_verify_error
                call    report_disk_error
; Drop verify caller return; resume the outer write loop at the next head.
                pop     ax
                jmpn    advance_target_side

retry_verify_not_ready:
                call    handle_not_ready
                jmp     short verify_target_track

; ------------------------------------------------------------------------
; Build cylinder/head fields in the sector-ID table and call BIOS format
; (AH=05h).
; ------------------------------------------------------------------------

; The sector-ID table stores cylinder, head, sector number and size for
; eight sectors.
format_target_track:
                or      byte ptr ds:[copy_flags],flag_writing
                push    es
                push    cs
                pop     es                              ; BIOS formatting must read the CHRN table from our segment.
                push    dx
                mov     byte ptr ds:[format_retries],0h
                mov     al,ch
                mov     ah,1h
                test    byte ptr ds:[copy_flags],flag_two_heads
                jnz     set_format_head
                dec     ah

set_format_head:
                mov     dh,ah
                mov     bx,offset buffer_segment

; Replace only cylinder/head; keep each sector number and 512-byte size code
; intact.
fill_format_ids:
                add     bx,4h
                mov     [bx],ax
                cmp82_bxdisp 2h, 8h
                jnz     fill_format_ids

; ES points to the program segment here, because BIOS consumes the sector-ID
; table.
format_track_attempt:
                mov     bx,offset format_id_table
                mov     ax,bios_format_track
                int     13h
                jc      format_track_failed
                mov     byte ptr ds:[format_retries],0h
                mov     ax,word ptr ds:[format_id_table]
                dec     ah
                jz      set_format_head                 ; The first pass formats head one; repeat for head zero.
                pop     dx
                pop     es
                ret

format_track_failed:
                push    ax
                xor     ax,ax
                int     13h
                pop     ax
                cmp     ah,80h
                jz      retry_format_not_ready
                cmp82_ah 3h
                jz      retry_format_write_protect
                inc     byte ptr ds:[format_retries]
                cmp82_mem format_retries, 4h
                jnz     format_track_attempt
                mov     dx,offset msg_format_failed
                jmpn    show_completion_status

retry_format_not_ready:
                call    handle_not_ready
                jmp     short format_track_attempt

retry_format_write_protect:
                mov     ax,offset msg_write_protected
                call    report_disk_error
                jmp     short format_track_attempt

; ------------------------------------------------------------------------
; AX=message, CH=track, DH=side. Print error and track/side context;
; preserve DX.
; ------------------------------------------------------------------------

; A formatting announcement is informational; other errors mark the target
; as possibly unusable.
report_disk_error:
                push    dx
                mov     ds:[side_digit_char],dh
                or      byte ptr ds:[side_digit_char],30h
                mov     dx,ax
                mov     ah,9h
                int     21h
                cmp     dx,offset msg_write_protected
                jz      wait_after_write_protect
                cmp     dx,offset msg_formatting_copy
                jz      report_disk_error_ret
                mov     word ptr ds:[track_tens_char],3030h
                mov     ah,ch

; Build two decimal cylinder digits without a division instruction.
count_track_tens:
                cmp82_ah 0Ah
                jc      show_error_track_side
                inc     byte ptr ds:[track_tens_char]
                sub82_ah 0Ah
                jmp     short count_track_tens

show_error_track_side:
                or      ds:[track_units_char],ah
                mov     dx,offset msg_track_side
                mov     ah,9h
                int     21h
; Remember that the final completion message must warn about target damage.
                or      byte ptr ds:[copy_flags],flag_errors_seen

report_disk_error_ret:
                pop     dx
                ret

wait_after_write_protect:
                mov     ax,0C01h
                int     21h
                pop     dx
                ret

; ------------------------------------------------------------------------
; DL=drive. Request correction of a not-ready error and wait for a key;
; preserve DX.
; ------------------------------------------------------------------------

handle_not_ready:
                push    dx
                add82_dl 41h
                mov     ds:[error_drive_char],dl
                mov     dx,offset msg_not_ready
                mov     ah,9h
                int     21h
                mov     dx,offset msg_reading
                test    byte ptr ds:[copy_flags],flag_writing
                jz      show_not_ready_operation
                mov     dx,offset msg_writing

show_not_ready_operation:
                int     21h
                mov     dx,offset msg_drive_suffix
                int     21h
                mov     dx,offset msg_correct_then_key
                int     21h
                mov     ax,0C01h
                int     21h
                pop     dx
                ret

current_cylinder         label   byte
                db      0h

; Whole cylinders that fit; halved when a second head is detected.
cylinders_per_buffer     label   byte
                db      0h

; Exclusive cylinder limit for the current batch; clamped to 40.
batch_end_cylinder       label   byte
                db      0h

; Bits: one drive, /1, write context, geometry known, errors, two heads,
; format target.
copy_flags               label   byte
                db      0h

read_retries             label   byte
                db      0h

write_retries            label   byte
                db      0h

verify_retries           label   byte
                db      0h

format_retries           label   byte
                db      0h

; Head to use after the next exchange; zero permanently with /1.
next_head                label   byte
                db      0h

buffer_segment           label   word
                db      0h,0h,0h,1h

format_id_table          label   byte
                db      0h,0h,1h,2h,0h,0h,2h,2h,0h,0h,3h,2h
                db      0h,0h,4h,2h,0h,0h,5h,2h,0h,0h,6h,2h
                db      0h,0h,7h,2h,0h,0h,8h,2h

msg_formatting_copy      label   byte
                db      0Dh,0Ah
                db      "Formatting while copying"
                db      0Dh,0Ah
                db      "$"

msg_insert_source        label   byte
                db      0Dh,0Ah
                db      "Insert source diskette in drive "

source_prompt_drive      label   byte
                db      "@:"
                db      0Dh,0Ah
                db      "$"

msg_insert_target        label   byte
                db      0Dh,0Ah
                db      "Insert target diskette in drive "

target_prompt_drive      label   byte
                db      "@:"
                db      0Dh,0Ah
                db      "$"

msg_press_key            label   byte
                db      0Dh,0Ah
                db      "Strike any key when ready"
                db      0Dh,0Ah
                db      "$"

msg_copy_complete        label   byte
                db      0Dh,0Ah
                db      "Copy complete"
                db      0Dh,0Ah
                db      "$"

msg_read_error           label   byte
                db      0Dh,0Ah
                db      "Unrecoverable read error on source$"

msg_write_error          label   byte
                db      0Dh,0Ah
                db      "Unrecoverable write error on target$"

msg_verify_error         label   byte
                db      0Dh,0Ah
                db      "Unrecoverable verify error on target$"

msg_track_side           label   byte
                db      0Dh,0Ah
                db      "Track "

track_tens_char          label   byte
                db      "0"

track_units_char         label   byte
                db      "0, side "

side_digit_char          label   byte
                db      "0"
                db      7h,0Dh,0Ah
                db      "$"

msg_target_maybe_unusable label   byte
                db      0Dh,0Ah
                db      "Target diskette may be unusable"
                db      7h,0Dh,0Ah
                db      "$"

msg_format_failed        label   byte
                db      0Dh,0Ah
                db      "Unrecoverable format error on target"
                db      0Dh,0Ah

msg_target_unusable      label   byte
                db      "Target diskette unusable"
                db      7h,0Dh,0Ah
                db      "$"

msg_write_protected      label   byte
                db      0Dh,0Ah
                db      "Target diskette write protected"
                db      0Dh,0Ah

msg_correct_then_key     label   byte
                db      0Dh,0Ah
                db      "Correct, then strike any key"
                db      7h,0Dh,0Ah
                db      "$"

msg_copy_another         label   byte
                db      0Dh,0Ah
                db      "Copy another (Y/N)?$"

msg_copying_sides        label   byte
                db      0Dh,0Ah
                db      "Copying "

copy_side_count_char     label   byte
                db      0h
                db      " side(s)"
                db      0Dh,0Ah
                db      "$"

msg_incompatible_drives  label   byte
                db      0Dh,0Ah
                db      "Incompatible drive types"
                db      0Dh,0Ah,7h
                db      "$"

msg_not_ready            label   byte
                db      0Dh,0Ah
                db      "Not ready error $"

msg_reading              label   byte
                db      "reading$"

msg_writing              label   byte
                db      "writing$"

msg_drive_suffix         label   byte
                db      " drive "

error_drive_char         label   byte
                db      0h,0Dh,0Ah
                db      "$"
                db      0h

; ------------------------------------------------------------------------
; Initialize drive selection and buffer allocation; parse the /1 option.
; ------------------------------------------------------------------------

init:
                cld
                mov     sp,100h
                xor     dx,dx
                push    dx                              ; A zero return address exits through the PSP INT 20h stub.
                or      ah,al
                cmp82_ah 0FFh
                jz      invalid_drive_exit
                mov     dx,offset msg_invalid_parameter
                cmp82_mem fcb1_name, 20h
                jnz     print_init_error_exit
                cmp82_mem fcb2_name, 20h
                jnz     print_init_error_exit
                mov     ah,ds:[fcb2_drive]
; Reuse the first filename byte only after both drive-only arguments were
; checked.
                mov     ds:[target_drive],ah
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
                jnz     default_source_drive
                mov     byte ptr ds:[source_drive],1h
                mov     byte ptr ds:[target_drive],1h
                jmp     short encode_drive_letters

default_source_drive:
                test    byte ptr ds:[source_drive],0FFh
                jnz     default_target_drive
                mov     ds:[source_drive],al
                jmp     short default_target_drive

invalid_drive_exit:
                mov     dx,offset msg_invalid_drive

print_init_error_exit:
                mov     ah,9h
                int     21h
                int     20h

default_target_drive:
                test    byte ptr ds:[target_drive],0FFh
                jnz     encode_drive_letters
                mov     ds:[target_drive],al

; Patch the prompts while drive numbers are one-based, then keep BIOS zero-
; based numbers.
encode_drive_letters:
                mov     al,ds:[source_drive]
                or      ds:[source_prompt_drive],al
                dec     al
                mov     ds:[source_drive],al
                mov     ah,al
                mov     al,ds:[target_drive]
                or      ds:[target_prompt_drive],al
                dec     al
                mov     ds:[target_drive],al
                cmp     al,ah
                jnz     allocate_copy_buffer
                or      byte ptr ds:[copy_flags],flag_one_drive

; Round above resident code to a 4 KiB boundary; initialization code may be
; overwritten.
allocate_copy_buffer:
                mov     byte ptr ds:[next_head],1h
                mov     dx,offset init
                mov     cl,4h
                shr     dx,cl
                mov     ax,cs
                add     dx,ax
                xor     dl,dl                           ; Round the transfer buffer up to the next 4 KiB boundary.
                inc     dh
                mov     word ptr ds:[buffer_segment],dx
                mov     ax,ds:[psp_end_segment]
                sub     ax,dx
                mov     cl,8h
                shr     ax,cl                           ; Convert free paragraphs to 4 KiB head buffers.
                mov     dx,offset msg_insufficient_memory
                cmp     ax,2h
                jc      print_init_error_exit
                mov     ds:[cylinders_per_buffer],al
                xor     ch,ch
                mov     cl,ds:[command_length]
                jcxz    begin_copy
                mov     di,81h
                mov     al,2Fh
                repne   scasb
                jnz     begin_copy
                cmp82_di 31h
                jnz     begin_copy
                or      byte ptr ds:[copy_flags],flag_one_side
                mov     byte ptr ds:[next_head],0h      ; /1 prevents the head number from toggling to one.

begin_copy:
                jmpn    copy_again

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

msg_invalid_drive        label   byte
                db      0Dh,0Ah
                db      "Invalid drive specification"
                db      7h,0Dh,0Ah
                db      "$"

program         ends
                end     start
