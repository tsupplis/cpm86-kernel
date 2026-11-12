; Execute the linked native adapter, not replacement RAW* stubs.
bits 16
cpu 8086
org 100h
%include "raw.inc"
start:
 cld
 mov dx,bdos
 mov ax,25e0h
 int 21h
 mov ax,2000h
 mov es,ax
 xor di,di
 mov si,code_image
 mov cx,code_end-code_image
 rep movsb
 mov di,0ff00h
 mov si,wrappers
 mov cx,wrappers_end-wrappers
 rep movsb
 mov ax,3000h
 mov es,ax
 xor di,di
 mov si,data_image
 mov cx,data_end-data_image
 rep movsb
 mov ax,4000h
 mov es,ax
 mov word [es:28h],xios
 mov ax,cs
 mov [es:2ah],ax
 mov word [es:88h],0
 mov word [es:110h],4100h
 mov word [es:106h],0
 mov word [es:0c18h],200h
 mov word [es:208h],300h
 mov byte [es:30fh],2
 mov ax,3000h
 mov ds,ax
 call open
 ; Eight logical records require two physical reads, with correct slices.
 xor si,si
.loop:
 mov ax,si
 call read
 or ax,ax
 jnz bad
 mov ax,si
 cmp [0e000h],al
 jne bad
 cmp [0e07fh],al
 jne bad
 inc si
 cmp si,8
 jne .loop
 cmp word [cs:reads],2
 jne bad
 ; Reopen must invalidate a previously cached sector.
 mov bx,RAWCLOSE
 call far [cs:zero_ptr]
 call open
 mov ax,7
 call read
 cmp word [cs:reads],3
 jne bad
 ; Once armed, same-sector reads must always reach the disk.
 mov bx,RAWARM
 call far [cs:zero_ptr]
 mov ax,7
 call read
 mov ax,7
 call read
 cmp word [cs:reads],5
 jne bad
 ; Fresh expected bytes + replacement, then read/compare/write/read/verify.
 mov di,0e100h
 mov cx,128
 mov al,0a5h
 push ds
 pop es
 rep stosb
 mov ax,7
 mov dx,0e000h
 mov cx,0e100h
 mov bx,RAWWRITE
 call far [cs:three_ptr]
 or ax,ax
 jnz bad
 cmp word [cs:reads],7
 jne bad
 cmp word [cs:writes],1
 jne bad
 ; A disk change since before-buffer capture must refuse a second write.
 mov byte [cs:changed],1
 mov ax,7
 mov dx,0e100h
 mov cx,0e000h
 mov bx,RAWWRITE
 call far [cs:three_ptr]
 or ax,ax
 jz bad
 cmp word [cs:writes],1
 jne bad
 mov bx,RAWCLOSE
 call far [cs:zero_ptr]
 call open
 ; Failed fills never become cache hits; failure remains latched.
 mov byte [cs:failread],1
 mov ax,0
 call read
 or ax,ax
 jz bad
 mov bp,[cs:reads]
 mov ax,0
 call read
 or ax,ax
 jz bad
 cmp bp,[cs:reads]
 jne bad
 mov bx,RAWCLOSE
 call far [cs:zero_ptr]
 mov ax,4c00h
 int 21h
bad:
 mov ax,4c01h
 int 21h
open:
 xor ax,ax
 mov dx,8
 mov cx,2
 mov bx,RAWOPEN
 call far [cs:three_ptr]
 or ax,ax
 jnz bad
 ret
read:
 mov dx,0e000h
 mov bx,RAWREAD
 call far [cs:two_ptr]
 ret
bdos:
 cmp cx,12
 je .version
 cmp cx,154
 je .system
 cmp cx,156
 je .process
 xor ax,ax
 iret
.version:
 mov ax,OSVER
 iret
.system:
 mov ax,4000h
 mov es,ax
 iret
.process:
 mov ax,4000h
 mov es,ax
 mov bx,100h
 iret
xios:
 push bp
 mov bp,sp
 push ds
 push es
 push si
 push di
 push cx
 cmp word [ss:bp+12],2
 jne bad
 cmp word [ss:bp+14],100h
 jne bad
 mov es,[ss:bp+8]
 mov di,[ss:bp+6]
 cmp al,11
 je .write
 inc word [cs:reads]
 cmp byte [cs:failread],0
 jne .failed
 mov ax,[ss:bp+10]
 shl ax,1
 shl ax,1
 mov si,4
.fill_records:
 mov cx,128
 rep stosb
 inc al
 dec si
 jnz .fill_records
 cmp word [cs:writes],0
 je .ok
 cmp word [ss:bp+10],1
 jne .ok
 mov di,[ss:bp+6]
 add di,384
 mov al,0a5h
 cmp byte [cs:changed],0
 je .fill
 inc al
.fill:
 mov cx,128
 rep stosb
 jmp .ok
.write:
 inc word [cs:writes]
 cmp byte [es:di],4
 jne bad
 cmp byte [es:di+383],6
 jne bad
 cmp byte [es:di+384],0a5h
 jne bad
 cmp byte [es:di+511],0a5h
 jne bad
.ok:
 xor ax,ax
 jmp .done
.failed:
 mov ax,1
.done:
 pop cx
 pop di
 pop si
 pop es
 pop ds
 pop bp
 retf
reads dw 0
writes dw 0
changed db 0
failread db 0
zero_ptr dw 0ff00h+wzero-wrappers,2000h
two_ptr dw 0ff00h+wtwo-wrappers,2000h
three_ptr dw 0ff00h+wthree-wrappers,2000h
wrappers:
wzero: call bx
 retf
wtwo: push ax
 push dx
 call bx
 retf
wthree: push ax
 push dx
 push cx
 call bx
 retf
wrappers_end:
code_image: incbin "code.bin"
code_end:
data_image: incbin "data.bin"
data_end:
