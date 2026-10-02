"""Control-flow discovery: which bytes are code, and where the code ends.

A linear sweep decodes strings as instructions and invents branch targets.
Following the branches from the entry point only visits what can run.
"""

from .disasm import BRANCH, disasm

CODE_START = 0x100
TERMINATORS = {'ret', 'retf', 'retn', 'iret', 'hlt', 'jmp'}


def direct_target(text):
    """Branch target of a direct jump/call/loop, else None (indirect, far)."""
    parts = text.split(None, 1)
    if parts[0] not in BRANCH or len(parts) < 2:
        return None
    op = parts[1].strip()
    for pre in ('short ', 'near '):
        if op.startswith(pre):
            op = op[len(pre):]
    if op.startswith('0x') and ':' not in op and '[' not in op:
        try:
            return int(op, 16)
        except ValueError:
            return None
    return None


def analyse(binf, base, end, entry=CODE_START, roots=()):
    """({addr: (size, text)}, {branch targets}) for everything reachable."""
    seen, targets, todo = {}, set(), [entry, *roots]
    while todo:
        a = todo.pop()
        if a in seen or not CODE_START <= a < end:
            continue
        for addr, hexb, text in disasm(binf, a, end, base):
            if addr in seen:
                break
            seen[addr] = (len(hexb) // 2, text)
            t = direct_target(text)
            if t is not None and CODE_START <= t < end:
                targets.add(t)
                todo.append(t)
            if text.split(None, 1)[0] in TERMINATORS:
                break
    return seen, targets


def holes(seen, lo, hi):
    """Byte ranges in [lo, hi) that no reached instruction covers."""
    out, pos = [], lo
    for a, e in sorted((a, a + s) for a, (s, _) in seen.items()):
        if a > pos:
            out.append((pos, a))
        pos = max(pos, e)
    if pos < hi:
        out.append((pos, hi))
    return out


def code_end(seen):
    return max(a + s for a, (s, _) in seen.items())


def runs(seen):
    """[(start, end)] of contiguous reached code; the edges need labels."""
    out = []
    for a, e in sorted((a, a + s) for a, (s, _) in seen.items()):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((a, e))
    return out
