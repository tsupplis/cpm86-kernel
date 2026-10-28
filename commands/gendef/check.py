"""Compare generated LIB records with the shipped GENDEF under emu2."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
emu = shutil.which('emu2')
if not emu:
    asm = shutil.which('cpm86_asm86')
    if asm:
        emu = str(Path(asm).parent / 'emu2')
if not emu:
    raise SystemExit('emu2 or cpm86_asm86 must be on PATH')
with tempfile.TemporaryDirectory(prefix='gendef-check-') as tmp:
    outputs = {}
    for version, binary in [('rebuilt', HERE / 'gendef.cmd'),
                            ('original', ROOT / 'base/gendef.cmd')]:
        for option in ['', '$C', '$O', '$Z', '$COZ']:
            work = Path(tmp) / (version + option.replace('$', '_'))
            work.mkdir()
            program = work / 'gendef.cmd'
            shutil.copyfile(binary, program)
            shutil.copyfile(ROOT / 'pcdisks.def', work / 'sample.def')
            env = dict(os.environ, EMU2_DRIVE_D=str(work),
                       EMU2_PROGNAME='D:GENDEF.CMD')
            result = subprocess.run([emu, str(program), 'sample'] +
                                    ([option] if option else []), cwd=work,
                                    env=env, capture_output=True, timeout=20)
            result.check_returncode()
            outputs[version, option] = (work / 'sample.lib').read_bytes()
    for option in ['', '$C', '$O', '$Z', '$COZ']:
        assert outputs['rebuilt', option] == outputs['original', option], option
        print('PASS: identical LIB records:', option or 'default')
    assert outputs['rebuilt', ''] != outputs['rebuilt', '$C']
    assert outputs['rebuilt', ''] != outputs['rebuilt', '$O']
    assert outputs['rebuilt', ''] != outputs['rebuilt', '$Z']
