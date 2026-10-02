"""Line and number formatting helpers shared by the whole package."""


def num(v):
    s = format(v, 'x')
    if len(s) % 2:
        s = '0' + s
    if s[0] not in '0123456789':
        s = '0' + s
    return s + 'h'


def lbl(v):
    return 'l%04x' % v


def read_text(path):
    with open(path, newline='') as f:
        return f.read().replace('\r\n', '\n')


def write_text(path, text):
    with open(path, 'w', newline='\n') as f:
        f.write(text)


def split_operands(ops):
    """Split a db/dw operand list on commas that are outside quotes."""
    out, cur, q = [], '', False
    for ch in ops:
        if ch == "'":
            q = not q
        if ch == ',' and not q:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def strip_comment(s):
    """Drop a trailing `;` comment, ignoring semicolons inside quotes.

    The data really does contain strings like ';<=>?@ABCD' (PC scan codes), so
    a plain regex mistakes them for comments and undercounts the line.
    """
    q = False
    for i, ch in enumerate(s):
        if ch == "'":
            q = not q
        elif ch == ';' and not q:
            return s[:i]
    return s
