# DSKMAINT

`make` builds DSKMAINT, its frozen reference `dskmorg`, and the shared boot
images. The standalone [DFORM command](../dform/README.md) has its own build
and tests. Both consume boot images generated here from `bootsect.a86` and
`loader.a86`. The frozen reference extracts its original images from
`base/dskmaint.cmd`.

The menu offers 160K/320K and native CP/M 720K/1440K formatting. The generic
loader supports all four, using 16 KiB of temporary workspace and restoring
INT 1Eh before entering the kernel. The 1200K menu entry is an inactive
placeholder with no function key.

`make check` compares the frozen reference with the original binary.
From the repository root, `make check-floppy-live` checks both BIOSes on all
four formats, including kernels above allocation block 255 on side two,
persisted writes and unchanged system files.

Live format, verify, copy and comparison checks use disposable images:

```
python3 tools/disk_live_check.py --capacity 320 --sectors 8 --dskmaint
python3 tools/disk_live_check.py --capacity 720 --dskmaint
python3 tools/disk_live_check.py --capacity 1440 --dskmaint
```

Run these from the repository root after building the commands. Each check
compares every physical byte of the copied image. For the standalone 320K
formatter, replace `--dskmaint` with `--format`.
