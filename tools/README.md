# Host tools

Run from the repository root. These are host build and maintenance tools,
not commands installed on the CP/M disks. No emulator tests run implicitly
in `make check`.

## Build helpers

| Files | Consumer / purpose |
| --- | --- |
| `gendef.sh` | Makefile: run native GENDEF to generate disk tables |
| `expbind.py`, `editbind.py` | Makefile: generate EXP bindings from assembled symbol maps |
| `mk320.py` | Image recipes: create the empty 320K filesystem and install boot inputs |
| `cpm86cfgsec.py` | AT image recipes: initialize the BIOS configuration sector |
| `cpm86twist.py` | 320K physical/logical image conversion; also shipped in disks.zip |
| `help_tabs.py`, `help_style.py` | HELPHLP Makefile: compact index input and check documentation style |

## Regression checks

| Files | Entry point / distinct coverage |
| --- | --- |
| `kernel_check.py`, `kernel-baseline.json`, `kernel_check_test.py` | `make check`: frozen references, byte-drift guards and guard self-tests |
| `bioschk.py` | `make check`: preserved BIOS sites, native hooks and module boundaries |
| `fdcheck.py` | `make check`: execute floppy record/cache/CHS mapping |
| `rtc_check.py`, `century_check.py`, `edittest.py` | `make check`: RTC conversion, century display and EXP line editor |
| `dsktest.py` | `make check-disk`: execute DCOPY/DCOMP with synthetic devices |
| `../commands/dform/tests/check.py` | `make -C commands/dform check`: execute DFORM with synthetic devices |
| `disk_live_check.py` | `make check-disk-live`: guest copy/compare of nine physical sectors |
| `fdboot.py` | `make check-floppy-live`: both BIOSes, four formats, boot and persisted writes |
| `hd_capacity_check.py` | `make check-hd-capacity`: execute HD capacity/address calculations |
| `pc816chk.py`, `editlive.py` | `make check-exp-live`: 8080 execution and keyboard/display checks; script options select CPU/media |
| `hd_volume_check.py` | Manual: occupied HD, disk-full writes/readback and partition guards |
| `hd_followup_check.py` | Manual: cold boot and metadata repair using an HD-volume fixture |
| `hdmaint_live_check.py` | Manual: guest partition creation, MBR preservation and volume geometry |
| `hdmaint_mbr_check.py` | Manual: boot selection/deletion and DOS/CP/M boot; requires a DOS source disk |
| `hdfloppy.py` | Manual: production 720K/1440K images with an occupied HD fixture; checks combined media access |

For HD fixture creation and maintenance commands see
[HDMAINT validation](../commands/hdmaint/README.md). The combined-media check is:

```
python3 tools/hdfloppy.py --fixture /absolute/path/to/hd-volume-fixture
```

Build the four standard/EXP 720K/1440K AT images first. The fixture must contain
`hard.img` and `hdtest.cmd` from `hd_volume_check.py`; private copies are used.
These HD checks are not replacements for the native floppy or command tests.

## Manual source maintenance

| Files | Purpose / entry point |
| --- | --- |
| `a86tool.py`, `a86/` (19 modules) | One binary-reconstruction suite; `python3 tools/a86tool.py` lists operations |
| `a86selftest.py` | `make check-reconstruction`: reconstruction checks in disposable copies |
| `h862bin.py` | Local hex converter exercised by reconstruction self-tests; production Makefiles use the installed `h862bin` tool |
| `a86style.py` | Explicit assembly formatting tool; not invoked by builds |
| `mapping_data.py` | `python3 tools/mapping_data.py`: resolve mapping.md references against EXP symbol maps; diagnostic report, not a pass/fail test |

`help_hlp.py` was retired: the HELP database is built by the native HELP indexer.
