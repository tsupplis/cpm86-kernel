"""Call the compiled PL/M error counter at its 16-bit boundary."""
from pathlib import Path
import re,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
mapping=(ROOT/'chkcpmfs.mp2').read_text(errors='replace')
def symbol(base,name):
    m=re.search(base+r'H\s+([0-9A-F]+)H\s+SYM\s+'+name+r'\b',mapping)
    assert m,name
    return int(m[1],16)
code=symbol('0000','COUNTERROR');count=symbol('1000','ERRORCOUNT');block=symbol('1000','REPAIRBLOCKERS')
image=(ROOT/'chkcpmfs.cmd').read_bytes();n=int.from_bytes(image[1:3],'little')*16;d=int.from_bytes(image[10:12],'little')*16
with tempfile.TemporaryDirectory(prefix='chkcpmfs-counter-') as temp:
    p=Path(temp);(p/'code.bin').write_bytes(image[128:128+n]);(p/'data.bin').write_bytes(image[128+n:128+n+d])
    (p/'test.asm').write_text(f'''bits 16
cpu 8086
org 100h
push cs
pop ds
mov ax,2000h
mov es,ax
xor di,di
mov si,code_image
mov cx,code_end-code_image
cld
rep movsb
mov di,7000h
mov si,stub
mov cx,stub_end-stub
rep movsb
mov ax,cs
mov [es:700fh],ax
mov ax,3000h
mov es,ax
xor di,di
mov si,data_image
mov cx,data_end-data_image
rep movsb
mov ds,ax
cli
mov ss,ax
mov sp,0f000h
sti
jmp 2000h:7000h
returned:
mov al,1
cmp word [{count}],0ffffh
jne done
cmp byte [{block}],1
jne done
xor al,al
done:
mov ah,4ch
int 21h
stub:
db 0c7h,06h
dw {count},0fffeh
db 0e8h
dw {code}-(7000h+9)
db 0e8h
dw {code}-(7000h+12)
db 0eah
dw returned,0
stub_end:
code_image: incbin 'code.bin'
code_end:
data_image: incbin 'data.bin'
data_end:
''')
    subprocess.run(['nasm','-f','bin','test.asm','-o','test.com'],cwd=p,check=True,capture_output=True)
    out=subprocess.run(['emu2','test.com'],cwd=p,capture_output=True,timeout=5)
    assert out.returncode==0,(out.returncode,out.stdout,out.stderr)
print('PASS: compiled error counter saturates at 65535 and preserves the repair blocker')
