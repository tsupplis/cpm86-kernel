# CALLCOMPAT — CP/M-86 1.1 commands

2026-11-05. Source/API review of all 35 executable artifacts in the distribution
recipe. This is not a cross-version runtime certification.

**1.1**: native CP/M-86 baseline (BDOS 2.2 and the original IBM PC BIOS).
**Degraded**: works without enhanced behaviour. **Specific**: no working fallback
without the required extension. Preserved binaries are classified as 1.1.
The inventory includes the feature-disk boot helper; shell built-ins and tools
not packaged by the distribution recipe are outside this table.

**Adaptive**: deliberately detects the OS version or available services and selects
a supported path; unavailable optional features do not prevent normal use.

| Command | Status | Comment |
| --- | --- | --- |
| 144BLDR2.CMD <!-- extra/144bldr2.cmd --> | 1.1 |  |
| 144PAT2.CMD <!-- extra/144pat2.cmd --> | 1.1 |  |
| 144PREP2.CMD <!-- extra/144prep2.cmd --> | Specific | 1.1 baseline. Requires the active 1.44 MB Feature driver; without it, disk preparation is refused. |
| ASM86.CMD <!-- commands/asm86/asm86.cmd --> | Adaptive | 1.1 baseline. Version-gated BDOS 108 exit-status reporting; normal operation does not require it. |
| ASSIGN.CMD <!-- commands/assign/assign.cmd --> | 1.1 |  |
| ATINIT.CMD <!-- extra/atinit.cmd --> | 1.1 |  |
| CBAS86.CMD <!-- dev/cbas86.cmd --> | 1.1 |  |
| CHKCPMFS.CMD <!-- commands/chkcpmfs/chkcpmfs.cmd --> | 1.1 |  |
| CONFIG.CMD <!-- commands/config/config.cmd --> | 1.1 |  |
| CRUN86.CMD <!-- dev/crun86.cmd --> | 1.1 |  |
| DCOMP.CMD <!-- commands/disk/dcomp.cmd --> | Specific | Vanilla CP/M-86 1.1, specific CCP/M-86 3.1 and specific CDOS 4.1 only. |
| DCOPY.CMD <!-- commands/disk/dcopy.cmd --> | Specific | Vanilla CP/M-86 1.1, specific CCP/M-86 3.1 and specific CDOS 4.1 only. |
| DDT86.CMD <!-- commands/ddt86/ddt86.cmd --> | 1.1 |  |
| DFORM.CMD <!-- commands/dskmaint/dform.cmd --> | Specific | Vanilla CP/M-86 1.1 and specific CCP/M-86 3.1 only. |
| DSKMAINT.CMD <!-- commands/dskmaint/dskmaint.cmd --> | 1.1 |  |
| ED.CMD <!-- commands/ed/ed.cmd --> | Adaptive |  |
| FUNCTION.CMD <!-- commands/function/function.cmd --> | 1.1 |  |
| GENCMD.CMD <!-- commands/gencmd/gencmd.cmd --> | Adaptive | 1.1 baseline. Version-gated BDOS 108 exit-status reporting; normal operation does not require it. |
| GENDEF.CMD <!-- commands/gendef/gendef.cmd --> | 1.1 |  |
| HDMAINT.CMD <!-- commands/hdmaint/hdmaint.cmd --> | 1.1 |  |
| HELP.CMD <!-- commands/help/help.cmd --> | 1.1 |  |
| LIB86.CMD <!-- dev/lib86.cmd --> | 1.1 |  |
| LINK86.CMD <!-- dev/link86.cmd --> | 1.1 |  |
| MBASIC86.CMD <!-- dev/mbasic86.cmd --> | 1.1 |  |
| MFORM.CMD <!-- commands/mform/mform.cmd --> | 1.1 |  |
| PBASIC.CMD <!-- dev/pbasic.cmd --> | 1.1 |  |
| PIP.CMD <!-- commands/pip/pip.cmd --> | Adaptive |  |
| PRINT.CMD <!-- commands/print/print.cmd --> | 1.1 |  |
| RASM86.CMD <!-- dev/rasm86.cmd --> | 1.1 |  |
| SETUP.CMD <!-- commands/setup/setup.cmd --> | 1.1 |  |
| SID86.CMD <!-- dev/sid86.cmd --> | 1.1 |  |
| STAT.CMD <!-- commands/stat/stat.cmd --> | 1.1 |  |
| SUBMIT.CMD <!-- commands/submit/submit.cmd --> | 1.1 |  |
| TOD.CMD <!-- commands/tod/tod.cmd --> | 1.1 |  |
| XREF86.CMD <!-- dev/xref86.cmd --> | 1.1 |  |
