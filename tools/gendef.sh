#!/bin/sh
# Run base/gendef.cmd (DRI DISKDEF table generator) under emu2.
# Usage: tools/gendef.sh <name> [$<options>]   reads name.DEF, writes name.LIB
emu2=`dirname "$(command -v cpm86_asm86)"`/emu2
root=`cd "$(dirname "$0")/.." && pwd`
EMU2_DRIVE_D="$root/base"
export EMU2_DRIVE_D
EMU2_PROGNAME="D:GENDEF.CMD"
export EMU2_PROGNAME
exec "$emu2" "$root/base/gendef.cmd" "$@"
