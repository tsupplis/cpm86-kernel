#!/usr/bin/env python3
"""Validate the maintained TOD calendar routine with NASM and emu2."""
from datetime import date
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent


def execute(folder, code):
    (folder / "test.asm").write_text("bits 16\ncpu 8086\norg 100h\n" + code)
    subprocess.run(["nasm", "-f", "bin", "test.asm", "-o", "test.com"],
                   cwd=folder, check=True)
    result = subprocess.run(["emu2", "test.com"], cwd=folder,
                            capture_output=True, timeout=15)
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)


EXIT = """
ok: mov ax,4c00h
 int 21h
failed: mov ax,4c01h
 int 21h
"""


def tod(folder, source_path=ROOT / "tod.a86"):
    source = source_path.read_text()
    body = source[source.index("check_date:"):source.index("cpm_set_time:")]
    body = re.sub(r"\b(byte|word) ptr ([\w+]+)", r"\1 [\2]", body)
    body = body.replace("ptr ", "")
    body = body.replace("offset ", "")
    table = source[source.index("month_siz       db"):].splitlines()[0]
    cases = []
    for year in range(100):
        for month in range(1, 13):
            for day in (0, 28, 29, 30, 31):
                try:
                    date(2000 + year, month, day)
                    invalid = 0
                except ValueError:
                    invalid = 1
                cases.append(f' db "{month:02}/{day:02}/{year:02}",{invalid}')
    execute(folder, """
 mov si,cases
 mov bp,6000
next_case:
 mov di,tmz_date
 mov cx,8
 cld
 rep movsb
 lodsb
 xor ah,ah
 push ax
 call check_date
 pop dx
 cmp ax,dx
 jne failed
 cmp byte [month_siz+3],31
 jne failed
 dec bp
 jnz next_case
 jmp ok
""" + EXIT + body + "\n" + table + """
tmz_date times 8 db 0
tmz_time db "23:59:59"
cases:
""" + "\n".join(cases))
    print("PASS: 6000 TOD date checks, years 2000-2099, month boundaries and repeated calls")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="tod-test-") as td:
        tod(Path(td))
