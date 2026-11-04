"""Check the compiled command's parameter rejection before disk access."""
from pathlib import Path
import subprocess

command = Path(__file__).resolve().parents[1]
name = command.name.upper()
usage = (f"USAGE: {name} drive: [FV]\n"
         "  drive: A:..P:\n"
         "  F      repair (not implemented)\n"
         "  V      verbose\n")
cases = [([], None)]
for tail in ("A", "Q:", "1:", "AA:", "/V A:", "[F] A:", "4A:"):
    cases.append((tail.split(), "Invalid command line."))
for tail in ("A: B:", "A: [HELP]", "A: /D", "A: /L", "A: /R", "A: /B",
             "A: [", "A: []", "A: /", "A: /F]", "A: [FV]X",
             "A: /V /F", "A: [FV] B:", "A: 4", "A: [USER=4]"):
    cases.append((tail.split(), "Invalid command option."))
for tail in ("A: [F]", "A: [FV]", "A: [VF]", "A: [F",
             "a: [fv]", "A: /F", "a: /fv"):
    cases.append((tail.split(), "Requested option is not implemented yet."))
for args, error in cases:
    result = subprocess.run(["emu2", str(command / (name.lower()+".cmd")), *args],
                            capture_output=True, timeout=5)
    output = result.stdout.decode(errors="replace").replace("\r", "")
    assert usage in output, (args, output)
    if error:
        assert "ERROR: " + error in output, (args, output)
    assert "Scans ordinary" not in output and "data clusters" not in output, (args, output)
print(f"PASS: {len(cases)} {name} compiled parameter cases")
