"""Rebuild-and-verify: every mutating command goes through here."""

import os
import re
import shutil
import subprocess
import sys

from .text import write_text


def checked_sources(d):
    """The .a86 files `make check` assembles in `d`, from a dry run.

    -B so the answer does not depend on which objects happen to be up to date.
    """
    r = subprocess.run(['make', '-n', '-B', 'check'], cwd=d,
                       capture_output=True, text=True)
    return set(re.findall(r'[\w.\-]+\.a86\b', r.stdout))


def require_covered(a86):
    """Refuse to 'verify' a file that `make check` never assembles.

    The *org.a86 / working-copy split makes this easy to get wrong: editing the
    working copy while check builds the org file reports byte-identical without
    having assembled a single changed line.
    """
    d = os.path.dirname(a86) or '.'
    name = os.path.basename(a86)
    covered = checked_sources(d)
    if name in covered:
        return
    if covered:
        sys.exit('%s is not built by `make check` in %s (it builds: %s), so a '
                 'pass would prove nothing.\nRun the tool on one of those, or '
                 'pass --no-verify.' % (name, d, ', '.join(sorted(covered))))
    sys.exit('`make check` in %s assembles no .a86 file, so nothing could be '
             'verified.' % d)


def rebuild(d):
    """Rebuild from scratch and report success.

    `make clean` first: make compares mtimes to the second, so a file written
    and built in the same second can be judged up to date and the stale object
    linked instead - which silently validates a broken source.
    """
    subprocess.run(['make', 'clean'], cwd=d, capture_output=True)
    return subprocess.run(['make', 'check'], cwd=d, capture_output=True,
                          text=True)


def trial(a86, lines):
    """True if this source builds byte-identical.  The file is left as it was.

    For searching: try a candidate edit without committing to it.
    """
    with open(a86, 'rb') as f:
        original = f.read()
    try:
        write_text(a86, '\n'.join(lines))
        return rebuild(os.path.dirname(a86) or '.').returncode == 0
    finally:
        with open(a86, 'wb') as f:
            f.write(original)


def verified_write(a86, lines, verify=True, what='change', ok=None, tail=6):
    """Write the source, rebuild, and put the original back if it broke.

    Every mutating command shares this: a pattern match that looked right can
    still shift an encoding, so nothing is kept unless the binary still
    matches.  Returns True, or exits non-zero after restoring the backup.
    """
    body = '\n'.join(lines) if isinstance(lines, list) else lines
    if verify:
        require_covered(a86)
    backup = a86 + '.bak'
    shutil.copy2(a86, backup)
    write_text(a86, body)
    if not verify:
        os.remove(backup)
        return True
    r = rebuild(os.path.dirname(a86) or '.')
    if r.returncode == 0:
        os.remove(backup)
        if ok:
            print(ok)
        return True
    shutil.move(backup, a86)
    msg = (r.stdout + r.stderr).strip().splitlines()[-tail:]
    print('FAIL %s - reverted:\n  %s' % (what, '\n  '.join(msg)))
    sys.exit(1)
