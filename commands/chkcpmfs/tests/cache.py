"""Physical read counts and fresh repair I/O through the actual linked adapter."""
from pathlib import Path
import re,struct,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
image=(root/'chkcpmfs.cmd').read_bytes()
code=struct.unpack_from('<H',image,1)[0]*16
data=struct.unpack_from('<H',image,10)[0]*16
mapping=(root/'chkcpmfs.mp2').read_text(errors='replace')
public={name:int(off,16) for off,name in re.findall(r'0000H\s+([0-9A-F]+)H\s+PUB\s+(RAW\w+)',mapping)}
with tempfile.TemporaryDirectory(prefix='raw-cache-') as tmp:
    tmp=Path(tmp)
    (tmp/'code.bin').write_bytes(image[128:128+code])
    (tmp/'data.bin').write_bytes(image[128+code:128+code+data])
    (tmp/'raw.inc').write_text(''.join(f'%define {name} {off}\n' for name,off in public.items()))
    for version,shift in ((0x1431,2),(0x1431,4),(0x1441,2)):
        subprocess.run(['nasm','-f','bin',str(root/'tests/cache.asm'),'-I',str(tmp)+'/',
                        f'-DOSVER={version}',f'-DPHYSHIFT={shift}','-o',str(tmp/'cache.com')],cwd=tmp,check=True)
        p=subprocess.run(['emu2',str(tmp/'cache.com')],capture_output=True,timeout=15)
        assert p.returncode==0,(version,shift,p.returncode,p.stdout,p.stderr)
print('PASS: native cache counts, reopen invalidation, fresh repair/verification and failed fills (512-byte and 2K sectors)')
