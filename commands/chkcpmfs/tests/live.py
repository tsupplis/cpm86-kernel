"""Exercise the shared CHKCPMFS on disposable disks under the local OS."""
from pathlib import Path
import argparse
import re
import shutil
import subprocess
import sys
import tempfile

COMMAND = Path(__file__).resolve().parents[1]
ROOT = COMMAND.parents[1]
MEDIA = ROOT / "media"
DIRECTORY = 4096
KEEP = {"CCPM.SYS", "SET.CMD", "SHOW.CMD"}


def local_system():
    markers = {
        "cpm86": ROOT / "cpm86-320.cfg",
        "ccpm86": MEDIA / "ccpm86.cfg",
        "cdos": MEDIA / "cdos86.cfg",
    }
    matches = [name for name, marker in markers.items() if marker.is_file()]
    if len(matches) != 1:
        raise RuntimeError(f"expected one CHKCPMFS test system, found {matches}")
    return matches[0]


def run(*args, cwd):
    subprocess.run(args, cwd=cwd, check=True)


def convert(source, target, direction, cwd):
    if source.stat().st_size != 320 * 1024:
        target.write_bytes(source.read_bytes())
        return
    run(sys.executable, str(ROOT / "tools/cpm86twist.py"),
        direction, str(source), str(target), cwd=cwd)


def geometry(image):
    """Directory offset/count and allocation-pointer width for tested formats."""
    return {
        320: (4096, 64, 1),
        720: (9216, 256, 2),
        1200: (15360, 256, 2),
        1440: (18432, 256, 2),
    }[image.stat().st_size // 1024]


def directory_slots(image):
    """Physical offsets; large raw images retain the BIOS's reversed side two."""
    start, count, _ = geometry(image)
    size = image.stat().st_size // 1024
    for logical in range(start, start + count * 32, 32):
        if size == 320:
            yield logical  # Callers untwist legacy images before inspection.
        else:
            track_bytes = {720: 9, 1200: 15, 1440: 18}[size] * 512
            track, offset = divmod(logical, track_bytes)
            slot = track * 2 if track < 80 else (159 - track) * 2 + 1
            yield slot * track_bytes + offset


def directory_entries(image):
    data = image.read_bytes()
    return [(at, data[at:at + 32]) for at in directory_slots(image)
            if data[at] <= 15]


def blocks(record, width):
    return [int.from_bytes(record[at:at + width], 'little')
            for at in range(16, 32, width)]


def prepare_empty(folder, system, cwd, size=320):
    """Create disposable local fixtures using the maintained boot sources."""
    logical = folder / f'empty-{size}-logical.img'
    if size != 320:
        logical.write_bytes(bytes([0xe5]) * (size * 1024))
        run('mkfs.cpm', '-f', f'cpm86-{size}', str(logical), cwd=cwd)
        # Native format marker at the end of the first physical sector.
        marker = size // 10
        data = bytearray(logical.read_bytes())
        data[510] = 1
        data[511] = marker
        logical.write_bytes(data)
    else:
        fmt = 'cpm86-320' if system == 'cpm86' else 'ccpm86-320'
        run(sys.executable, str(ROOT / 'tools/mk320.py'), str(logical),
            '--format', fmt, '--boot', str(ROOT / 'commands/dskmaint/bootsect.bin'),
            '--loader', str(ROOT / 'commands/dskmaint/loader.bin'),
            *(['--label', 'CCPM86  31'] if system == 'ccpm86' else []), cwd=cwd)
    image = folder / f'empty-{size}.img'
    convert(logical, image, 'twist', cwd)
    return image


def filename(record):
    name = bytes(value & 0x7f for value in record[1:12])
    stem = name[:8].decode("ascii").rstrip()
    suffix = name[8:11].decode("ascii").rstrip()
    return stem + ("." + suffix if suffix else "")


def prepare_system(folder, system, disk_format, cwd):
    # Assemble a disposable test disk from this project's own built outputs.
    # No dependency on an already packaged distribution or another project.
    logical=folder/'system-logical.img'
    base=prepare_empty(folder, system, cwd)
    convert(base,logical,'untwist',cwd)
    if system=='cpm86':
        sources=[ROOT/'cpm.sys',COMMAND/'chkcpmfs.cmd',ROOT/'commands/stat/stat.cmd']
    else:
        sources=[ROOT/'kernel/sysgen/ccpm.sys',COMMAND/'chkcpmfs.cmd',
                 ROOT/'commands/set/set.cmd',ROOT/'commands/show/show.cmd']
    run('cpmcp', '-T', 'raw','-f',disk_format,str(logical),*[str(p) for p in sources],'0:',cwd=cwd)
    entries=directory_entries(logical)
    if system!='cpm86':
        system_entries=[record for _,record in entries if filename(record)=='CCPM.SYS']
        assert system_entries and any(any(record[16:32]) for record in system_entries)
    references=sum(sum(block!=0 for block in record[16:32]) for _,record in entries)
    image=folder/'system-source.img';convert(logical,image,'twist',cwd)
    return image,(len(entries),references)


def prepare_data(folder, empty, disk_format, cwd):
    logical = folder / "data-logical.img"
    convert(empty, logical, "untwist", cwd)
    _, _, width = geometry(logical)
    if width == 2:
        # Force allocated blocks above 255, exercising both pointer bytes.
        filler = folder / 'FILLER.DAT'
        filler.write_bytes(bytes(1040 * 1024 if logical.stat().st_size > 720 * 1024 else 520 * 1024))
        run('cpmcp', '-T', 'raw', '-f', disk_format, str(logical), str(filler), '0:FILLER.DAT', cwd=cwd)
    for user, name in ((0, "FIRST.DAT"), (1, "SECOND.DAT"), (15, "THIRD.DAT")):
        source = folder / name
        source.write_bytes((name + "\r\n").encode("ascii") * 12)
        run("cpmcp", "-T", "raw", "-f", disk_format, str(logical), str(source),
            f"{user}:{name}", cwd=cwd)
    large = folder / "MULTI.DAT"
    large.write_bytes(bytes(index & 0xff for index in range(40000)))
    run("cpmcp", "-T", "raw", "-f", disk_format, str(logical), str(large),
        "0:MULTI.DAT", cwd=cwd)

    entries = directory_entries(logical)
    multi_extents = [record for _, record in entries if record[1:12] == b"MULTI   DAT"]
    assert len(multi_extents) > 1
    first = next((at, record) for at, record in entries
                 if record[0] == 0 and record[1:12] == b"FIRST   DAT")
    second = next((at, record) for at, record in entries
                  if record[0] == 1 and record[1:12] == b"SECOND  DAT")
    shared = blocks(first[1], width)[0]
    assert shared and shared != blocks(second[1], width)[0]
    if width == 2:
        assert shared > 255

    clean = folder / "clean.img"
    convert(logical, clean, "twist", cwd)
    damaged = bytearray(logical.read_bytes())
    damaged[second[0] + 16:second[0] + 16 + width] = first[1][16:16 + width]
    logical.write_bytes(damaged)
    bad = folder / "crosslink.img"
    convert(logical, bad, "twist", cwd)
    references = sum(sum(block != 0 for block in blocks(record, width))
                     for _, record in entries)
    return clean, bad, shared, len(entries), references


def prepare_fat(folder, name, *, label=False, sentinel=False):
    image = folder / f"{name}.img"
    args = ["mformat", "-C", "-i", str(image), "-t", "40", "-h", "2",
            "-n", "8", "-c", "2"]
    if label:
        args.extend(["-v", "CHECKDISK"])
    run(*args, "::", cwd=folder)
    if sentinel:
        source = folder / "sentinel.txt"
        source.write_bytes(b"untouched FAT sentinel\r\n")
        run("mcopy", "-i", str(image), str(source), "::SENTINEL.TXT", cwd=folder)
    return image


def replace_required(text, old, new):
    if old not in text:
        raise RuntimeError(f"PCE configuration is missing {old!r}")
    return text.replace(old, new)


def read_screen(path):
    video = path.read_bytes()
    assert len(video) == 4000
    return "\n".join(video[at:at + 160:2].decode("cp437").rstrip()
                     for at in range(0, 4000, 160))


def boot(folder, system, system_image, target, drive="B", *, initially_read_only=False, repair=False, answer="y", expected_target=None):
    shutil.copyfile(system_image, folder / "system.img")
    shutil.copyfile(target, folder / "second.img")
    before_system = (folder / "system.img").read_bytes()
    before_target = (folder / "second.img").read_bytes()

    if system == "cpm86":
        config = (ROOT / "cpm86-320.cfg").read_text()
        config = replace_required(config, 'path = "rom"', f'path = "{ROOT / "rom"}"')
        system_name, target_name = "cpm86-320-at.img", "cpm86-320-dev.img"
    else:
        config_name = "cdos86.cfg" if system == "cdos" else "ccpm86.cfg"
        config = (MEDIA / config_name).read_text()
        config = replace_required(config, 'path = "rom"', f'path = "{MEDIA / "rom"}"')
        system_name = "cdos86.img" if system == "cdos" else "ccpm86.img"
        target_name = "cdostools.img" if system == "cdos" else "ccpmtools.img"
    config = replace_required(config, f'"{system_name}"', '"system.img"')
    config = replace_required(config, f'"{target_name}"', '"second.img"')
    config = re.sub(r'speed\s*=\s*\d+', 'speed = 64', config)
    config = config.replace('driver = "sdl"', 'driver = "null"')
    config = config.replace('driver      = "sdl:lowpass=5000"', 'driver      = "null"')
    (folder / "test.cfg").write_text(config)

    commands = ["c f000000"]
    keys = {
        " ": "Space", ":": "+Shift Semicolon -Shift", "=": "Equal",
        "[": "LeftBracket", "]": "RightBracket",
    }

    def type_command(text):
        for character in text:
            commands.extend(["key " + keys.get(character, character), "c 200000"])
        commands.extend(["key Return", "c 20000000"])

    if drive == "B":
        type_command("b:")
        if system == "cdos":
            type_command("cls")
    if initially_read_only:
        if system == "cpm86":
            type_command(f"a:stat {drive.lower()}:=ro")
        else:
            type_command(f"a:set {drive.lower()}: [ro]")
    type_command(f"a:chkcpmfs {drive.lower()}:" + (" [f]" if repair else ""))
    if repair:
        commands.append('save "repair-prompt.bin" bin b800:0000 fa0')
        commands.extend(["key "+answer,"c 10000000"])
        commands.append('save "repair-result.bin" bin b800:0000 fa0')
        type_command(f"a:chkcpmfs {drive.lower()}:")
    commands.append('save "scan-screen.bin" bin b800:0000 fa0')
    if system == "cpm86":
        type_command(f"a:stat {drive.lower()}:dsk:")
        type_command("a:stat")
    else:
        type_command(f"a:show {drive.lower()}:")
    commands.extend(['save "status-screen.bin" bin b800:0000 fa0', "q"])
    with (folder/'pce.log').open('wb') as log:
        result = subprocess.run(
            ["pce-ibmpc", "-c", "test.cfg", "-t", "null", "-g", "vga"],
            cwd=folder, input=("\n".join(commands) + "\n").encode(),
            stdout=log,stderr=log,timeout=90,
        )
    if result.returncode != 0:
        raise AssertionError((result.returncode,(folder/'pce.log').read_text(errors='replace')[-4000:]))
    screen = read_screen(folder / "scan-screen.bin")
    status = read_screen(folder / "status-screen.bin")
    assert (folder / "system.img").read_bytes() == before_system, screen
    assert (folder / "second.img").read_bytes() == (before_target if expected_target is None else expected_target), screen
    return screen, status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--formats', nargs='+', type=int,
                        choices=(320, 720, 1200, 1440))
    args = parser.parse_args()
    system = local_system()
    if args.formats is None:
        args.formats = [320, 720, 1200, 1440]
    cwd = ROOT if system == "cpm86" else MEDIA
    disk_format = "cpm86-320" if system == "cpm86" else "ccpm86-320"
    private = ROOT / 'private'
    private.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"chkcpmfs-{system}-", dir=private) as directory:
        folder = Path(directory)
        empty = prepare_empty(folder, system, cwd)
        system_image, system_counts = prepare_system(folder, system, disk_format, cwd)
        for size in args.formats:
            empty = prepare_empty(folder, system, cwd, size)
            data_format = disk_format if size == 320 else f'cpm86-{size}'
            clean, bad, shared, entries, references = prepare_data(folder, empty, data_format, cwd)

            if system == "cdos":
                screen, status = boot(folder, system, system_image, clean, "A")
                assert system_counts is not None
                assert "Drive A  DPB block shift" in screen, screen
                assert (f"Directory entries scanned: {system_counts[0]}  "
                        f"block references checked: {system_counts[1]}") in screen, screen
                assert "Consistency errors: 0" in screen and "ERROR:" not in screen, screen
                assert "A: RW" in status, status

            screen, status = boot(folder, system, system_image, empty)
            assert "Drive B  DPB block shift" in screen, screen
            assert "Directory entries scanned: 0  block references checked: 0" in screen, screen
            assert "Consistency errors: 0" in screen and "ERROR:" not in screen, screen
            assert "B: RW" in status, status

            screen, status = boot(folder, system, system_image, clean)
            assert "Drive B  DPB block shift" in screen, screen
            assert (f"Directory entries scanned: {entries}  "
                    f"block references checked: {references}") in screen, screen
            assert "Consistency errors: 0" in screen and "ERROR:" not in screen, screen
            assert "No inconsistencies found in checked entries." in screen, screen
            assert "B: RW" in status, status

            screen, status = boot(folder, system, system_image, clean, initially_read_only=True)
            assert "Drive was already read-only; preserving its RO state." in screen, screen
            assert "Consistency errors: 0" in screen and "ERROR:" not in screen, screen
            assert "B: RO" in status, status

            screen, status = boot(folder, system, system_image, bad)
            assert re.search(r"USER 1 FILE SECOND\s+\.DAT: BLOCK "
                             + str(shared) + r" IS REFERENCED MORE THAN ONCE", screen), screen
            assert "Consistency errors: 1" in screen, screen
            assert "Review the reported directory-entry errors." in screen, screen
            assert "B: RW" in status, status

            if system == "cdos":
                fats = (prepare_fat(folder, "fat-empty"),
                        prepare_fat(folder, "fat-label", label=True),
                        prepare_fat(folder, "fat-file", sentinel=True))
                for fat in fats:
                    screen, status = boot(folder, system, system_image, fat)
                    assert "DOS media detected; no CP/M filesystem scan performed." in screen, screen
                    assert "Directory entries scanned:" not in screen, screen
                    assert "B: RW" in status, status
            cases = 8 if system == "cdos" else 4
            print(f"PASS: {system} {size}K: {cases} scan cases; images unchanged", flush=True)
    print(f"PASS: live {system} empty/multi-user/multi-extent/cross-linked scans, "
          "RO preservation and restoration"
          + (", FAT refusal" if system == "cdos" else "")
          + "; images unchanged")


if __name__ == "__main__":
    main()
