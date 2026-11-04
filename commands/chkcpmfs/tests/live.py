"""Exercise the shared CHKCPMFS on disposable disks under the local OS."""
from pathlib import Path
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
    run(sys.executable, str(ROOT / "tools/cpm86twist.py"),
        direction, str(source), str(target), cwd=cwd)


def directory_entries(image):
    data = image.read_bytes()
    return [(at, data[at:at + 32])
            for at in range(DIRECTORY, DIRECTORY + 64 * 32, 32)
            if data[at] <= 15]


def filename(record):
    name = bytes(value & 0x7f for value in record[1:12])
    stem = name[:8].decode("ascii").rstrip()
    suffix = name[8:11].decode("ascii").rstrip()
    return stem + ("." + suffix if suffix else "")


def prepare_system(folder, system, disk_format, cwd):
    if system == "cpm86":
        return ROOT / "cpm86-chkcpmfs.img", None

    image_name = "cdos86.img" if system == "cdos" else "ccpm86.img"
    logical = folder / "system-logical.img"
    convert(MEDIA / image_name, logical, "untwist", cwd)
    removed = set()
    for _, record in directory_entries(logical):
        if record[0] != 0:
            continue
        name = filename(record)
        if name not in KEEP and name not in removed:
            run("cpmrm", "-f", disk_format, str(logical), f"0:{name}", cwd=cwd)
            removed.add(name)
    run("cpmcp", "-f", disk_format, str(logical),
        str(COMMAND / "chkcpmfs.cmd"), "0:CHKCPMFS.CMD", cwd=cwd)
    entries = directory_entries(logical)
    system_entries = [record for _, record in entries if filename(record) == "CCPM.SYS"]
    assert system_entries and any(any(record[16:32]) for record in system_entries)
    references = sum(sum(block != 0 for block in record[16:32])
                     for _, record in entries)
    image = folder / "system-source.img"
    convert(logical, image, "twist", cwd)
    return image, (len(entries), references)


def prepare_data(folder, empty, disk_format, cwd):
    logical = folder / "data-logical.img"
    convert(empty, logical, "untwist", cwd)
    for user, name in ((0, "FIRST.DAT"), (1, "SECOND.DAT"), (15, "THIRD.DAT")):
        source = folder / name
        source.write_bytes((name + "\r\n").encode("ascii") * 12)
        run("cpmcp", "-f", disk_format, str(logical), str(source),
            f"{user}:{name}", cwd=cwd)
    large = folder / "MULTI.DAT"
    large.write_bytes(bytes(index & 0xff for index in range(40000)))
    run("cpmcp", "-f", disk_format, str(logical), str(large),
        "0:MULTI.DAT", cwd=cwd)

    entries = directory_entries(logical)
    multi_extents = [record for _, record in entries if record[1:12] == b"MULTI   DAT"]
    assert len(multi_extents) > 1
    first = next((at, record) for at, record in entries
                 if record[0] == 0 and record[1:12] == b"FIRST   DAT")
    second = next((at, record) for at, record in entries
                  if record[0] == 1 and record[1:12] == b"SECOND  DAT")
    assert first[1][16] and second[1][16]
    assert first[1][16] != second[1][16]

    clean = folder / "clean.img"
    convert(logical, clean, "twist", cwd)
    damaged = bytearray(logical.read_bytes())
    damaged[second[0] + 16] = first[1][16]
    logical.write_bytes(damaged)
    bad = folder / "crosslink.img"
    convert(logical, bad, "twist", cwd)
    references = sum(sum(block != 0 for block in record[16:32])
                     for _, record in entries)
    return clean, bad, first[1][16], len(entries), references


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


def boot(folder, system, system_image, target, drive="B", *, initially_read_only=False):
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
        system_name = "cdos86.img" if system == "cdos" else "ccpm86.img"
        target_name = "cdostools.img" if system == "cdos" else "ccpmtools.img"
    config = replace_required(config, f'"{system_name}"', '"system.img"')
    config = replace_required(config, f'"{target_name}"', '"second.img"')
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
        commands.extend(["key Return", "c 4000000"])

    if drive == "B":
        type_command("b:")
        if system == "cdos":
            type_command("cls")
    if initially_read_only:
        if system == "cpm86":
            type_command(f"a:stat {drive.lower()}:=ro")
        else:
            type_command(f"a:set {drive.lower()}: [ro]")
    type_command(f"a:chkcpmfs {drive.lower()}:")
    commands.append('save "scan-screen.bin" bin b800:0000 fa0')
    if system == "cpm86":
        type_command(f"a:stat {drive.lower()}:dsk:")
        type_command("a:stat")
    else:
        type_command(f"a:show {drive.lower()}:")
    commands.extend(['save "status-screen.bin" bin b800:0000 fa0', "q"])
    result = subprocess.run(
        ["pce-ibmpc", "-c", "test.cfg", "-t", "null", "-g", "vga"],
        cwd=folder, input=("\n".join(commands) + "\n").encode(),
        capture_output=True, timeout=180,
    )
    if result.returncode != 0:
        raise AssertionError((result.returncode,
                              result.stdout.decode(errors="replace")[-4000:],
                              result.stderr.decode(errors="replace")[-4000:]))
    screen = read_screen(folder / "scan-screen.bin")
    status = read_screen(folder / "status-screen.bin")
    assert (folder / "system.img").read_bytes() == before_system, screen
    assert (folder / "second.img").read_bytes() == before_target, screen
    return screen, status


def main():
    system = local_system()
    cwd = ROOT if system == "cpm86" else MEDIA
    disk_format = "cpm86-320" if system == "cpm86" else "ccpm86-320"
    empty = (ROOT / "base-320.img" if system == "cpm86" else
             MEDIA / ("cdos86base.img" if system == "cdos" else "ccpm86base.img"))
    with tempfile.TemporaryDirectory(prefix=f"chkcpmfs-{system}-") as directory:
        folder = Path(directory)
        system_image, system_counts = prepare_system(folder, system, disk_format, cwd)
        clean, bad, shared, entries, references = prepare_data(folder, empty, disk_format, cwd)

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
    print(f"PASS: live {system} empty/multi-user/multi-extent/cross-linked scans, "
          "RO preservation and restoration"
          + (", FAT refusal" if system == "cdos" else "")
          + "; images unchanged")


if __name__ == "__main__":
    main()
