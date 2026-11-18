all: cpm.sys mbc816.sys mbcv20.sys ad88.sys cpmexp.sys cpmorg.sys commands extra

# 320K disks store side 1 in reverse cylinder order (pcbios.a86 SETUP_INTREG),
# so cpmtools has to work on an untwisted copy that is twisted back at the end.
TWIST = python3 tools/cpm86twist.py

# Every distribution uses rebuilt tools wherever a commands/ counterpart exists.
CMDDIR   = commands
ASM86    = $(CMDDIR)/asm86/asm86.cmd
DDT86    = $(CMDDIR)/ddt86/ddt86.cmd
ED       = $(CMDDIR)/ed/ed.cmd
GENCMD   = $(CMDDIR)/gencmd/gencmd.cmd
GENDEF   = $(CMDDIR)/gendef/gendef.cmd
HELP     = $(CMDDIR)/help/help.cmd
HLP      = $(CMDDIR)/helphlp/help.hlp
PIP      = $(CMDDIR)/pip/pip.cmd
PRINT    = $(CMDDIR)/print/print.cmd
STAT     = $(CMDDIR)/stat/stat.cmd
SUBMIT   = $(CMDDIR)/submit/submit.cmd
TOD      = $(CMDDIR)/tod/tod.cmd
ASSIGN   = $(CMDDIR)/assign/assign.cmd
DSKMAINT = $(CMDDIR)/dskmaint/dskmaint.cmd
FUNCTION = $(CMDDIR)/function/function.cmd
HDMAINT  = $(CMDDIR)/hdmaint/hdmaint.cmd
CONFIG   = $(CMDDIR)/config/config.cmd
SETUP    = $(CMDDIR)/setup/setup.cmd
MFORM    = $(CMDDIR)/mform/mform.cmd
DFORM    = $(CMDDIR)/dskmaint/dform.cmd
DCOPY    = $(CMDDIR)/disk/dcopy.cmd
DCOMP    = $(CMDDIR)/disk/dcomp.cmd
TESTSUB  = $(CMDDIR)/submit/testcpm.sub
DATPFK   = $(CMDDIR)/function/data.pfk

# Content sets shared by every image recipe. The feature (720K/1.44M) images
# take everything; the 320K images take subsets.
ASMTOOLS   = $(ASM86) $(DDT86) $(GENCMD) $(GENDEF)
DRTOOLS    = dev/rasm86.cmd dev/link86.cmd dev/lib86.cmd dev/xref86.cmd \
             dev/sid86.cmd
BASICTOOLS = dev/pbasic.cmd dev/cbas86.cmd dev/crun86.cmd dev/mbasic86.cmd
DEVTOOLS   = $(DRTOOLS) $(BASICTOOLS)
EXTTOOLS   = $(DFORM) $(DCOPY) $(DCOMP)
CHKCPMFS   = $(CMDDIR)/chkcpmfs/chkcpmfs.cmd
CPM80FILES = $(wildcard cpm80/*)

DIST_DISKS = cpm86-8080.img cpm86-320.img cpm86-320-at.img cpm86-exp-320-at.img cpm86-exp-320.img cpm86-320-dev.img \
    cpm86-chkcpmfs.img cpm86-1440-at.img cpm86-exp-1440-at.img \
    cpm86-720-at.img cpm86-exp-720-at.img

# Tools that are the same whichever kernel the image carries.
SHARED     = $(SETUP) $(HDMAINT) \
             $(CONFIG) $(PRINT) 

CORETOOLS  = $(PIP) $(STAT) $(SUBMIT) $(ED) $(FUNCTION) \
             $(HELP) $(ASSIGN) $(MFORM) \
             $(HLP) $(DSKMAINT) $(DATPFK) \
             $(TOD) $(SHARED)
EXPCORE    = $(PIP) $(STAT) $(SUBMIT) $(ED) $(HELP) $(TOD) $(ASSIGN) \
             $(MFORM) $(FUNCTION) $(SHARED) $(DSKMAINT) $(HLP) $(TESTSUB) \
             $(DATPFK)
EXPASM     = $(ASM86) $(DDT86) $(GENCMD) $(GENDEF)

STOCKTOOLS = $(CORETOOLS) $(ASMTOOLS) $(DEVTOOLS) $(EXTTOOLS)
EXPTOOLS   = $(EXPCORE) $(EXPASM) $(DEVTOOLS) $(EXTTOOLS)
FEATURETOOLS = $(STOCKTOOLS) $(CHKCPMFS)
EXPFEATURETOOLS = $(EXPTOOLS) $(CHKCPMFS)

.PHONY: all commands extra clean dist check test test-exp test-320

commands:
	$(MAKE) -C $(CMDDIR)

extra: extra/144feat.inc
	$(MAKE) -C extra

cpm86-1440-at.img: commands extra cpm.sys Makefile diskdefs \
    extra/144pat2.cmd extra/144prep2.cmd extra/atinit.cmd tools/cpm86cfgsec.py
	python3 -c "b=bytearray(open('extra/144boot2.bin','rb').read()); b[511]=144; open('$@.boot','wb').write(b)"
	python3 -c "open('$@','wb').write(bytes([0xE5])*1474560)"
	mkfs.cpm -f cpm86-144feat -b $@.boot $@
	python3 tools/cpm86cfgsec.py $@ atinit
	rm -f $@.boot
	cpmcp -f cpm86-144feat $@ cpm.sys 0:CPM.SYS
	cpmcp -f cpm86-144feat $@ extra/144bldr2.cmd 0:144BLDR2.CMD
	cpmcp -f cpm86-144feat $@ extra/144pat2.cmd 0:144PAT2.CMD
	cpmcp -f cpm86-144feat $@ extra/144prep2.cmd 0:144PREP2.CMD
	cpmcp -f cpm86-144feat $@ extra/atinit.cmd 0:ATINIT.CMD
	cpmcp -f cpm86-144feat $@ $(FEATURETOOLS) 0:
	cpmls -F -f cpm86-144feat $@ '0:*.*'

cpm86-720-at.img: commands extra cpm.sys Makefile diskdefs \
    extra/144pat2.cmd extra/144prep2.cmd extra/atinit.cmd tools/cpm86cfgsec.py
	python3 -c "b=bytearray(open('extra/144boot2.bin','rb').read()); b[511]=72; open('$@.boot','wb').write(b)"
	python3 -c "open('$@','wb').write(bytes([0xE5])*737280)"
	mkfs.cpm -f cpm86-720feat -b $@.boot $@
	python3 tools/cpm86cfgsec.py $@ atinit
	rm -f $@.boot
	cpmcp -f cpm86-720feat $@ cpm.sys 0:CPM.SYS
	cpmcp -f cpm86-720feat $@ extra/144bldr2.cmd 0:144BLDR2.CMD
	cpmcp -f cpm86-720feat $@ extra/144pat2.cmd 0:144PAT2.CMD
	cpmcp -f cpm86-720feat $@ extra/144prep2.cmd 0:144PREP2.CMD
	cpmcp -f cpm86-720feat $@ extra/atinit.cmd 0:ATINIT.CMD
	cpmcp -f cpm86-720feat $@ $(FEATURETOOLS) 0:
	cpmls -F -f cpm86-720feat $@ '0:*.*'

cpm86-exp-1440-at.img: commands extra cpmexp.sys Makefile diskdefs \
    extra/144bldr2.cmd extra/144pat2.cmd extra/144prep2.cmd extra/atinit.cmd tools/cpm86cfgsec.py
	python3 -c "b=bytearray(open('extra/144boot2.bin','rb').read()); b[511]=144; open('$@.boot','wb').write(b)"
	python3 -c "open('$@','wb').write(bytes([0xE5])*1474560)"
	mkfs.cpm -f cpm86-144feat -b $@.boot $@
	python3 tools/cpm86cfgsec.py $@ atinit
	rm -f $@.boot
	cpmcp -f cpm86-144feat $@ cpmexp.sys 0:CPM.SYS
	cpmcp -f cpm86-144feat $@ extra/144bldr2.cmd 0:144BLDR2.CMD
	cpmcp -f cpm86-144feat $@ extra/144pat2.cmd 0:144PAT2.CMD
	cpmcp -f cpm86-144feat $@ extra/144prep2.cmd 0:144PREP2.CMD
	cpmcp -f cpm86-144feat $@ extra/atinit.cmd 0:ATINIT.CMD
	cpmcp -f cpm86-144feat $@ $(EXPFEATURETOOLS) 0:
	cpmls -F -f cpm86-144feat $@ '0:*.*'

cpm86-exp-720-at.img: commands extra cpmexp.sys Makefile diskdefs \
    extra/144bldr2.cmd extra/144pat2.cmd extra/144prep2.cmd extra/atinit.cmd tools/cpm86cfgsec.py
	python3 -c "b=bytearray(open('extra/144boot2.bin','rb').read()); b[511]=72; open('$@.boot','wb').write(b)"
	python3 -c "open('$@','wb').write(bytes([0xE5])*737280)"
	mkfs.cpm -f cpm86-720feat -b $@.boot $@
	python3 tools/cpm86cfgsec.py $@ atinit
	rm -f $@.boot
	cpmcp -f cpm86-720feat $@ cpmexp.sys 0:CPM.SYS
	cpmcp -f cpm86-720feat $@ extra/144bldr2.cmd 0:144BLDR2.CMD
	cpmcp -f cpm86-720feat $@ extra/144pat2.cmd 0:144PAT2.CMD
	cpmcp -f cpm86-720feat $@ extra/144prep2.cmd 0:144PREP2.CMD
	cpmcp -f cpm86-720feat $@ extra/atinit.cmd 0:ATINIT.CMD
	cpmcp -f cpm86-720feat $@ $(EXPFEATURETOOLS) 0:
	cpmls -F -f cpm86-720feat $@ '0:*.*'

cpm86-320-at.img: commands extra cpm.sys Makefile diskdefs tools/mk320.py \
    commands/dskmaint/bootsect.bin commands/dskmaint/loader.bin tools/cpm86twist.py extra/atinit.cmd \
    tools/cpm86cfgsec.py
	python3 tools/mk320.py $@.wrk --format cpm86-320 \
	    --boot commands/dskmaint/bootsect.bin --loader commands/dskmaint/loader.bin
	python3 tools/cpm86cfgsec.py $@.wrk atinit
	cpmcp -f cpm86-320 $@.wrk cpm.sys 0:CPM.SYS
	cpmcp -f cpm86-320 $@.wrk extra/atinit.cmd 0:ATINIT.CMD
	cpmcp -f cpm86-320 $@.wrk $(CORETOOLS) $(ASMTOOLS) $(EXTTOOLS) 0:
	cpmls -F -f cpm86-320 $@.wrk '0:*.*'
	$(TWIST) twist $@.wrk $@
	rm -f $@.wrk

cpm86-exp-320-at.img: commands extra cpmexp.sys Makefile diskdefs tools/mk320.py \
    commands/dskmaint/bootsect.bin commands/dskmaint/loader.bin tools/cpm86twist.py \
    extra/atinit.cmd tools/cpm86cfgsec.py
	python3 tools/mk320.py $@.wrk --format cpm86-320 \
	    --boot commands/dskmaint/bootsect.bin --loader commands/dskmaint/loader.bin
	python3 tools/cpm86cfgsec.py $@.wrk atinit
	cpmcp -f cpm86-320 $@.wrk cpmexp.sys 0:CPM.SYS
	cpmcp -f cpm86-320 $@.wrk extra/atinit.cmd 0:ATINIT.CMD
	cpmcp -f cpm86-320 $@.wrk $(CORETOOLS) $(ASMTOOLS) $(EXTTOOLS) 0:
	cpmls -F -f cpm86-320 $@.wrk '0:*.*'
	$(TWIST) twist $@.wrk $@
	rm -f $@.wrk

cpm86-320.img: commands cpm.sys Makefile diskdefs tools/mk320.py \
    commands/dskmaint/bootsect.bin commands/dskmaint/loader.bin tools/cpm86twist.py
	python3 tools/mk320.py $@.wrk --format cpm86-320 \
	    --boot commands/dskmaint/bootsect.bin --loader commands/dskmaint/loader.bin
	cpmcp -f cpm86-320 $@.wrk cpm.sys 0:CPM.SYS
	cpmcp -f cpm86-320 $@.wrk $(CORETOOLS) $(ASMTOOLS) $(EXTTOOLS) 0:
	cpmls -F -f cpm86-320 $@.wrk '0:*.*'
	$(TWIST) twist $@.wrk $@
	rm -f $@.wrk

cpm86-exp-320.img: commands cpmexp.sys Makefile diskdefs tools/mk320.py \
    commands/dskmaint/bootsect.bin commands/dskmaint/loader.bin tools/cpm86twist.py
	python3 tools/mk320.py $@.wrk --format cpm86-320 \
	    --boot commands/dskmaint/bootsect.bin --loader commands/dskmaint/loader.bin
	cpmcp -f cpm86-320 $@.wrk cpmexp.sys 0:CPM.SYS
	cpmcp -f cpm86-320 $@.wrk $(CORETOOLS) $(ASMTOOLS) $(EXTTOOLS) 0:
	cpmls -F -f cpm86-320 $@.wrk '0:*.*'
	$(TWIST) twist $@.wrk $@
	rm -f $@.wrk

cpm86-320-dev.img: commands Makefile diskdefs tools/mk320.py \
    commands/dskmaint/bootsect.bin commands/dskmaint/loader.bin tools/cpm86twist.py
	python3 tools/mk320.py $@.wrk --format cpm86-320 \
	    --boot commands/dskmaint/bootsect.bin --loader commands/dskmaint/loader.bin
	cpmcp -f cpm86-320 $@.wrk $(PIP) $(SUBMIT) $(ED) $(DEVTOOLS) 0:
	cpmls -F -f cpm86-320 $@.wrk '0:*.*'
	$(TWIST) twist $@.wrk $@
	rm -f $@.wrk

cpm86-8080.img: commands $(CPM80FILES) Makefile diskdefs tools/mk320.py \
    commands/dskmaint/loader.bin tools/cpm86twist.py cpm80/
	python3 tools/mk320.py $@.wrk --format cpm86-320 \
	    --boot commands/dskmaint/bootsect.bin --loader commands/dskmaint/loader.bin
	cpmcp -f cpm86-320 $@.wrk $(CPM80FILES) 0:
	cpmls -F -f cpm86-320 $@.wrk '0:*.*'
	$(TWIST) twist $@.wrk $@
	rm -f $@.wrk

cpm86-chkcpmfs.img: commands cpm.sys Makefile diskdefs tools/mk320.py \
    commands/dskmaint/bootsect.bin commands/dskmaint/loader.bin tools/cpm86twist.py
	python3 tools/mk320.py $@.wrk --format cpm86-320 \
	    --boot commands/dskmaint/bootsect.bin --loader commands/dskmaint/loader.bin
	cpmcp -f cpm86-320 $@.wrk cpm.sys 0:CPM.SYS
	cpmcp -f cpm86-320 $@.wrk $(PIP) $(STAT) $(CHKCPMFS) 0:
	cpmls -F -f cpm86-320 $@.wrk '0:*.*'
	$(TWIST) twist $@.wrk $@
	rm -f $@.wrk

.PHONY: chkcpmfs-live-images
chkcpmfs-live-images: cpm86-chkcpmfs.img

# Track the generated file, rather than an alias that never exists.
extra/144feat.inc: cpm.sys cpmexp.sys tools/gen_144feat_inc.py
	python3 tools/gen_144feat_inc.py $@

.PHONY: 144feat-map
144feat-map: extra/144feat.inc

cpm.sys: cpm86.h86
	cpm86_gencmd cpm86.h86 8080 "CODE[A51,M0000]"
	mv cpm86.cmd cpm.sys


cpmorg.sys: cpm86org.h86
	cpm86_gencmd cpm86org.h86 8080 "CODE[A51,M0000]"
	mv cpm86org.cmd cpmorg.sys

cpmexp.sys: cpm86exp.h86
	cpm86_gencmd cpm86exp.h86 8080 "CODE[A51,M0000]"
	mv cpm86exp.cmd cpmexp.sys

# BIOS-only objects keep their source basenames. The *k intermediates contain
# CCP + BDOS + BIOS, and must never overwrite mbcv20.h86 or mbc816.h86.
mbcv20.sys: mbcv20k.h86
	cpm86_gencmd $< 8080 "CODE[A40]"
	mv mbcv20k.cmd $@

mbcv20.bin: mbcv20.sys
	dd bs=128 skip=1 if=$< of=$@

mbcv20k.h86: cpm.h86 mbcv20.h86
	doscat cpm.h86 > $@
	cat mbcv20.h86 >> $@

mbc816.sys: mbc816k.h86
	cpm86_gencmd $< 8080 "CODE[A40]"
	mv mbc816k.cmd $@

mbc816.bin: mbc816.sys
	dd bs=128 skip=1 if=$< of=$@

mbc816k.h86: cpm.h86 mbc816.h86
	doscat cpm.h86 > $@
	cat mbc816.h86 >> $@

# AD8088 Card for Apple II: upstream mksys.sub specifies segment 4000h.
ad88.sys: ad88.h86
	cpm86_gencmd $< 8080 "CODE[A4000]"
	mv ad88.cmd $@

ad88.h86: cpm.h86 ad88bios.h86
	doscat cpm.h86 > $@
	cat ad88bios.h86 >> $@

ad88bios.h86: apdisk.lib

apdisk.lib: apdisk.def tools/gendef.sh $(GENDEF)
	sh tools/gendef.sh apdisk '$$C'

cpm86.h86: cpm.h86 pcbios.h86
	doscat cpm.h86 > cpm86.h86
	cat pcbios.h86 >> cpm86.h86

cpm86exp.h86: cpmexp.h86 pcbioexp.h86
	doscat cpmexp.h86 > cpm86exp.h86
	cat pcbioexp.h86 >> cpm86exp.h86

cpm86org.h86: cpmorg.h86 pcbioorg.h86
	doscat cpmorg.h86 > cpm86org.h86
	cat pcbioorg.h86 >> cpm86org.h86

cpm.h86: ccp.h86 bdos.h86
	doscat ccp.h86 > cpm.h86
	cat bdos.h86  >> cpm.h86

cpmorg.h86: ccporg.h86 bdosorg.h86
	doscat ccporg.h86 > cpmorg.h86
	cat bdosorg.h86  >> cpmorg.h86

cpmexp.h86: ccpexp.h86 bdosexp.h86
	doscat ccpexp.h86 > cpmexp.h86
	cat bdosexp.h86  >> cpmexp.h86

%.h86: %.a86
	cpm86_asm86 $<

clean:
	$(MAKE) -C $(CMDDIR) clean
	$(MAKE) -C extra clean
	rm -rf *.h86 *.lst *.sym *.log
	rm -f bdosbind.equ ccpexp.equ
	rm -rf cpm86.cmd cpm.sys 
	rm -rf cpm86exp.cmd cpmexp.sys 
	rm -rf cpm86org.cmd cpmorg.sys
	rm -rf cpm86-720-at.img cpm86-exp-720-at.img
	rm -rf cpm86-1440-at.img cpm86-exp-1440-at.img
	rm -rf cpm86-exp-320.img cpm86-exp-320-at.img cpm86-320-at.img cpm86-320.img cpm86-320-dev.img cpm86-chkcpmfs.img cpm86-8080.img
	rm -rf *.img.wrk
	rm -f mbc816.sys mbcv20.sys mbc816.bin mbcv20.bin ad88.sys apdisk.lib
	rm -f mbc816k.cmd mbcv20k.cmd ad88.cmd
	# Remove outputs left by the former MBC target names.
	rm -f cpm816.sys cpmv20.sys cpm816.bin cpmv20.bin
	rm -rf *.xxd

clean-images:
	rm -rf cpm86-720-at.img cpm86-exp-720-at.img
	rm -rf cpm86-1440-at.img cpm86-exp-1440-at.img
	rm -rf cpm86-exp-320.img cpm86-exp-320-at.img cpm86-320-at.img cpm86-320.img cpm86-320-dev.img cpm86-chkcpmfs.img cpm86-8080.img

dist: disks.zip

disks.zip: Makefile $(DIST_DISKS) README.md LICENSE.md LICENSE-bis.md diskdefs tools/cpm86twist.py
	$(RM) $@.tmp.zip
	zip -j $@.tmp.zip $(DIST_DISKS) README.md LICENSE.md LICENSE-bis.md diskdefs tools/cpm86twist.py
	mv $@.tmp.zip $@
    

# Frozen references and pinned hashes guard source cleanup against code drift.
.PHONY: check
check: cpm.sys cpmorg.sys cpmexp.sys commands tools/kernel_check.py tools/kernel_check_test.py \
    tools/kernel-baseline.json
	$(MAKE) -C commands/disk check
	python3 tools/kernel_check.py
	python3 tools/feature_compat_check.py
	python3 tools/rtc_check.py
	python3 -B tools/century_check.py
	python3 -B tools/edittest.py
	python3 tools/kernel_check_test.py
	$(MAKE) -C commands/chkcpmfs check-bdos

test: dist
	./cpm86-320

test-exp: dist
	./cpm86-exp

test-320: dist
	./cpm86-320

# Raw floppy maintenance checks; live tests use disposable images only.
.PHONY: check-disk check-disk-live
check-disk:
	$(MAKE) -C commands/disk check

check-disk-live: all
	python3 tools/disk_live_check.py

# Execute built hard-disk capacity/addressing routines; no physical disks.
.PHONY: check-hd-capacity
check-hd-capacity: cpm.sys cpmexp.sys
	$(MAKE) -C commands/hdmaint check
	python3 tools/hd_capacity_check.py

# EXP-only 8080 bridge: bindings follow the assembled CCP; no runtime patches.
ccpexp.equ: ccpexp.h86 tools/expbind.py
	python3 -B tools/expbind.py

bdosbind.equ: bdosexp.h86 tools/editbind.py
	python3 -B tools/editbind.py

pcbioexp.h86: pc816.lib ccpexp.equ bdosbind.equ lineedit.lib
