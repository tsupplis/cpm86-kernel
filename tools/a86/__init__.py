"""Reconstruct DRI RASM-86 sources from shipped CP/M-86 .CMD binaries.

The workflow is always: scaffold the directory from the shipped binary, then
splice labels at every branch target, then convert the raw `db` blocks to
instructions a region at a time, checking after each step that the rebuilt
binary is still byte-identical to the original.

  a86tool.py scaffold <name> [--cmd ../../base/<name>.cmd]
      Create commands/<name>/ with a Makefile and a dummy <name>.a86: the
      first instruction decoded for real, the rest of the image as a raw `db`
      dump.  Runs `make check` once to prove the skeleton is byte-identical
      before any real reconstruction work starts.

  a86tool.py usedata <a86> [--no-verify]
      Refer to data by label instead of by number in the code: absolute
      operands, indexed operands and `mov si,addr` pointer loads, only where
      a data label sits at that exact address and the width fits.  Every
      candidate is checked by the assembler; lines that do not build stay
      numeric.

  a86tool.py typedata <bin> <a86> [--no-verify]
      Type and label the data area from the datamap classification: variables
      as db/dw with their initial value, strings quoted, zeros and binary as
      db.  Only segments whose lines are still raw scaffold dumps are touched;
      labels (dXXXX) only where something points.  Verified byte-identical.

  a86tool.py datamap <bin> <a86>
      Classify the data area (text, zero runs, evidenced tables, binary) and
      show which addresses the code points at.  Flags binary blobs that hold
      BIOS interrupt opcodes (embedded boot code).  Read-only.

  a86tool.py annotate <bin> <a86> [text|tables] [--no-verify]
      Quote strings and turn jump tables into dw, only where there is
      evidence: text of 8+ printable bytes on plain db lines, and tables that
      reached code indexes through an indirect jmp/call with every entry
      already labelled.  Otherwise it changes nothing and says why.

  a86tool.py holes <bin> <a86>
      Classify the unreached bytes in the code (text, word tables, unknown)
      and follow table entries as new entry points.  Read-only.

  a86tool.py decode <bin> <a86>
      Convert every reached db region to instructions in one go.  Instructions
      the assembler rejects or encodes differently are demoted to db, one
      build each, until the result is byte-identical.  Restores the source if
      it cannot finish.

  a86tool.py boundary <bin> <a86> [--set [ADDR]] [--no-verify]
      Follow the branches from the entry point and report where the code
      ends (the proposed data_org) and which ranges inside it are unreached.
      With --set, move everything from ADDR (default: the proposal) into a
      dseg and record data_org.  Verified byte-identical.

  a86tool.py labels <bin> <a86> [--no-verify]
      Splice an lXXXX: label at every reached branch target and every edge of
      a code run, splitting db lines as needed.  Verified byte-identical.

  a86tool.py gen <bin> <a86> <start> <end>
      Print the converted source for a range (does not modify anything).

  a86tool.py patch <bin> <a86> <start> <end> [--no-verify]
      Convert a range and splice it into the .a86 in place, replacing the `db`
      block between the bounding labels.  Runs `make check` afterwards and
      restores the original file if it fails.

Addresses are hex.  Names are taken from the `name equ 0xxxxh` block in the
.a86, so adding an equate there is enough to have it used everywhere after.
"""
