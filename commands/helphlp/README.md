# HELPHLP

The CP/M-86 help database. `help.dat` is the editable text; `make` indexes it
into `help.hlp` with the native `[C]` indexer of `../help/help.cmd` under
emu2, using a temporary CRLF copy. The HELP program is built in `../help`;
its sources are shared between CCP/M and CP/M-86.
