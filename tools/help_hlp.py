#!/usr/bin/env python3
"""
help_hlp.py - Build help.hlp from help.dat for CP/M-86 HELP utility.

Reimplements the create$index procedure from help.plm exactly.

The .hlp file format (128-byte CP/M records throughout):
  Records 0..N-1: index table
    Each 128-byte record holds 8 entries of 16 bytes:
      [0:12]  subject: topic name, space-padded, ASCII uppercase
      [12:14] record: 2-byte LE CP/M record# in this file where content starts
      [14]    rec_offset: byte offset within that record of the CR at the end
              of the ///Nlevel<name>\r\n marker line (i.e. where 'i' is in the
              PLM after the name-scanning while loop stops at CR)
      [15]    level: 1 = top-level topic, 2 = subtopic
    The first entry whose subject[0] = '$' terminates the index.
    Unused bytes in index records are padded with 0x1A.
  Records N..: verbatim copy of help.dat (CRLF), last record padded 0x1A.

Usage:
  python3 help_hlp.py help.dat help.hlp   (build)
  python3 help_hlp.py help.hlp            (dump index)
"""

import sys, struct

SECTOR  = 128
ENTRY   = 16
NAME_W  = 12
PER_REC = SECTOR // ENTRY   # 8 entries per record


def pad_sector(data):
    """Pad bytes to next sector boundary with 0x1A."""
    r = len(data) % SECTOR
    if r:
        data += b'\x1a' * (SECTOR - r)
    return data


def build_hlp(dat_path, hlp_path):
    src = open(dat_path, 'rb').read()
    # Normalise to CRLF
    src = src.replace(b'\r\n', b'\n').replace(b'\r', b'\n').replace(b'\n', b'\r\n')
    src_padded = pad_sector(src)

    # --- Pass 1: find all ///N markers in the flat source ---
    # For each marker, record the position of the CR at the end of the
    # ///Nlevel<name>\r line. Names and markers can span sector boundaries.
    entries = []   # (name_str, src_byte_of_CR, level)

    pos = 0
    while pos < len(src_padded):
        if src_padded[pos] == 0x1a:
            pos += 1
            continue
        if src_padded[pos:pos+3] == b'///':
            j = pos + 3
            if j < len(src_padded):
                level = src_padded[j] - ord('0')
                j += 1
                # read name until CR, up to 12 chars, uppercase
                name_bytes = bytearray()
                while j < len(src_padded) and src_padded[j] != 0x0d and len(name_bytes) < 12:
                    ch = src_padded[j]
                    if 0x61 <= ch <= 0x7a:
                        ch -= 0x20
                    name_bytes.append(ch)
                    j += 1
                # j now points at the CR at end of the ///N<name> line
                entries.append((name_bytes.decode('ascii'), j, level))
                pos = j
                continue
        pos += 1

    if not entries:
        print("ERROR: no ///1 or ///2 markers found", file=sys.stderr)
        sys.exit(1)

    # --- number of index records (8 entries per record, +1 sentinel) ---
    num_idx_recs = (len(entries) + PER_REC) // PER_REC
    if len(entries) % PER_REC == 0:
        num_idx_recs += 1

    # --- adjust: src_byte_of_CR is relative to body start (byte 0 of src_padded)
    # In the final file, body starts at record num_idx_recs.
    # Final absolute byte of CR = num_idx_recs*SECTOR + src_byte_of_CR
    # record = final_abs // SECTOR,  offset = final_abs % SECTOR
    adjusted = []
    for name, src_cr_byte, lvl in entries:
        final_abs = num_idx_recs * SECTOR + src_cr_byte
        adjusted.append((name, final_abs // SECTOR, final_abs % SECTOR, lvl))

    # --- build index bytes ---
    idx = bytearray()
    for name, record, rec_off, level in adjusted:
        idx += name.encode('ascii')[:NAME_W].ljust(NAME_W, b' ')
        idx += struct.pack('<H', record)
        idx += bytes([rec_off, level])

    # sentinel + up to 7 more '$' entries to pad to full index records
    # (per spec: "There may be up to seven further '$' entries to pad
    #  the index out to a multiple of 128 bytes")
    dollar_entry = b'$' + b' ' * (NAME_W - 1) + b'\x00\x00\x00\x00'
    entries_written = len(entries)
    entries_needed  = num_idx_recs * PER_REC
    for _ in range(entries_needed - entries_written):
        idx += dollar_entry

    idx_section = bytes(idx)

    # Body: CRLF content terminated with a single 0x1A (not padded to full sector)
    body = src.rstrip(b'\x1a') + b'\x1a'
    out = idx_section + body
    open(hlp_path, 'wb').write(out)
    print(f"Written {len(out)} bytes ({len(out)//SECTOR} records) to {hlp_path} "
          f"({len(entries)} topics, {num_idx_recs} index records)")


def dump_index(hlp_path):
    d = open(hlp_path, 'rb').read()
    print(f"File: {len(d)} bytes, {len(d)//SECTOR} records")
    i = 0
    while i + ENTRY <= len(d):
        if d[i] == 0x24:   # '$'
            print(f"  END-OF-INDEX at entry {i//ENTRY} (byte {i})")
            break
        if d[i] == 0x1a:
            break
        name   = d[i:i+12].decode('ascii', errors='replace').rstrip()
        record = struct.unpack_from('<H', d, i+12)[0]
        offset = d[i+14]
        level  = d[i+15]
        content_abs = record * SECTOR + offset
        snippet = d[content_abs:content_abs+30].replace(b'\r\n', b' ')
        print(f"  {name!r:16s}  rec={record:4d} off={offset:3d}  "
              f"abs={content_abs:#07x}  lvl={level}  {snippet!r}")
        i += ENTRY


if __name__ == '__main__':
    if len(sys.argv) == 3:
        build_hlp(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1].endswith(('.hlp', '.org')):
        dump_index(sys.argv[1])
    else:
        print(f"Usage: {sys.argv[0]} help.dat help.hlp   (build)")
        print(f"       {sys.argv[0]} help.hlp             (dump index)")
        sys.exit(1)
