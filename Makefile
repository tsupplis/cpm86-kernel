all: cpm.sys cpm816.sys cpmv20.sys cpmexp.sys cpmorg.sys

# 320K disks store side 1 in reverse cylinder order (pcbios.a86 SETUP_INTREG),
# so cpmtools has to work on an untwisted copy that is twisted back at the end.
TWIST = python3 tools/cpm86twist.py

# Tools rebuilt from source. tod has no base/ binary at all, so every image
# takes it from here; the experimental images take the whole reconstructed set.
CMDDIR = commands
ASM86  = $(CMDDIR)/asm86/asm86.cmd
DDT86  = $(CMDDIR)/ddt86/ddt86.cmd
ED     = $(CMDDIR)/ed/ed.cmd
GENCMD = $(CMDDIR)/gencmd/gencmd.cmd
HELP   = $(CMDDIR)/help/help.cmd
PIP    = $(CMDDIR)/pip/pip.cmd
STAT   = $(CMDDIR)/stat/stat.cmd
SUBMIT = $(CMDDIR)/submit/submit.cmd
TOD    = $(CMDDIR)/tod/tod.cmd

# Content sets shared by every image recipe. The feature (720K/1.44M) images
# take everything; the smaller formats take subsets.
ASMTOOLS   = base/asm86.cmd base/ddt86.cmd base/gencmd.cmd base/gendef.cmd
DRTOOLS    = dev/rasm86.cmd dev/link86.cmd dev/lib86.cmd dev/xref86.cmd \
             dev/sid86.cmd
BASICTOOLS = dev/pbasic.cmd dev/cbas86.cmd dev/crun86.cmd dev/mbasic86.cmd
DEVTOOLS   = $(DRTOOLS) $(BASICTOOLS)

# Tools that are the same whichever kernel the image carries.
SHARED     = base/setup.cmd base/dskmaint.cmd base/hdmaint.cmd \
             base/function.cmd base/config.cmd base/assign.cmd base/data.pfk \
             base/help.hlp base/print.cmd base/mform.cmd

CORETOOLS  = base/pip.cmd base/stat.cmd base/submit.cmd base/ed.cmd \
             base/help.cmd $(TOD) $(SHARED)
EXPCORE    = $(PIP) $(STAT) $(SUBMIT) $(ED) $(HELP) $(TOD) $(SHARED)
EXPASM     = $(ASM86) $(DDT86) $(GENCMD) base/gendef.cmd

STOCKTOOLS = $(CORETOOLS) $(ASMTOOLS) $(DEVTOOLS)
EXPTOOLS   = $(EXPCORE) $(EXPASM) $(DEVTOOLS)

# Every image target drives one of the three canned recipes below through
# target-specific FEAT/BASE/KRNL/FTOOLS variables. KRNL is empty on the
# data-only disks, ATSTART is set only on the -at variants.
define flat_image
	cp $(BASE) $@
	$(if $(KRNL),cpmcp -f $(FEAT) $@ $(KRNL) 0:CPM.SYS)
	$(if $(ATSTART),cpmcp -f $(FEAT) $@ extra/atinit.cmd 0:ATINIT.CMD)
	cpmcp -f $(FEAT) $@ $(FTOOLS) 0:
	cpmls -F -f $(FEAT) $@ 0:*.*
endef

# 320K disks need the side-1 reordering, so the work happens on an untwisted
# copy that is twisted back at the end.
define twist_image
	$(TWIST) untwist $(BASE) $@.wrk
	$(if $(KRNL),cpmcp -f $(FEAT) $@.wrk $(KRNL) 0:CPM.SYS)
	$(if $(ATSTART),cpmcp -f $(FEAT) $@.wrk extra/atinit.cmd 0:ATINIT.CMD)
	cpmcp -f $(FEAT) $@.wrk $(FTOOLS) 0:
	cpmls -F -f $(FEAT) $@.wrk 0:*.*
	$(TWIST) twist $@.wrk $@
	rm -f $@.wrk
endef

# V selects the feature build: "2" is the stock one, "x" the expkrnl one.
# The loader keeps its on-disk name either way, since the boot sector's FCB
# searches for that literal.
define feat_image
	cp $(BASE) $@
	-cpmrm -f $(FEAT) $@ 0:144BLDR2.CMD
	cpmcp -f $(FEAT) $@ $(KRNL) 0:CPM.SYS
	cpmcp -f $(FEAT) $@ extra/144bldr$(V).cmd 0:144BLDR2.CMD
	cpmcp -f $(FEAT) $@ extra/144pat$(V).cmd 0:144PAT.CMD
	cpmcp -f $(FEAT) $@ extra/144prep$(V).cmd 0:144PREP.CMD
	cpmcp -f $(FEAT) $@ extra/atinit.cmd 0:ATINIT.CMD
	cpmcp -f $(FEAT) $@ $(FTOOLS) 0:
	cpmls -F -f $(FEAT) $@ 0:*.*
endef

.PHONY: all commands extra clean dist check test test-exp test-320

commands:
	$(MAKE) -C $(CMDDIR)

extra:
	$(MAKE) -C extra

cpmwk.img: base-160.img
	cp base-160.img $@

# The "-at" bases differ from their plain counterparts only by the startup
# command the BIOS stuffs into the keyboard buffer at boot. base-160.img
# already carries a config sector so its settings are preserved; base-320.img
# does not, so one is created.
base-160-at.img: base-160.img
	cp $< $@
	python3 tools/cpm86cfgsec.py $@ atinit

base-320-at.img: base-320.img
	cp $< $@
	python3 tools/cpm86cfgsec.py $@ atinit

# A blank feature disk is just the boot sector plus an erased directory, so
# mkfs.cpm can lay one down directly and 144PREP is only needed on real media.
# mkfs.cpm does not size the image, hence the pre-fill. The boot sector's last
# byte is the media byte (144boot2.asm, cpmedia): 72 = 720K, 144 = 1.44M.
base-720-at.img: MEDIA = 72
base-720-at.img: BYTES = 737280
base-720-at.img: FEAT = cpm86-720feat
base-1440-at.img: MEDIA = 144
base-1440-at.img: BYTES = 1474560
base-1440-at.img: FEAT = cpm86-144feat

base-720-at.img base-1440-at.img: | extra
	python3 -c "b=bytearray(open('extra/144boot2.bin','rb').read()); b[0x1ff]=$(MEDIA); open('$@.boot','wb').write(bytes(b))"
	python3 -c "open('$@','wb').write(bytes([0xE5])*$(BYTES))"
	mkfs.cpm -f $(FEAT) -b $@.boot $@
	python3 tools/cpm86cfgsec.py $@ atinit
	rm -f $@.boot

cpm86-1440-at.img: FEAT = cpm86-144feat
cpm86-1440-at.img: BASE = base-1440-at.img
cpm86-1440-at.img: KRNL = cpm.sys
cpm86-1440-at.img: FTOOLS = $(STOCKTOOLS)
cpm86-1440-at.img: V = 2
cpm86-1440-at.img: cpm.sys base-1440-at.img | commands extra
	$(feat_image)

cpm86-720-at.img: FEAT = cpm86-720feat
cpm86-720-at.img: BASE = base-720-at.img
cpm86-720-at.img: KRNL = cpm.sys
cpm86-720-at.img: FTOOLS = $(STOCKTOOLS)
cpm86-720-at.img: V = 2
cpm86-720-at.img: cpm.sys base-720-at.img | commands extra
	$(feat_image)

# Experimental kernel plus the full commands/ reconstruction. The feature
# loader and patcher must be the expkrnl builds, since cpmexp.sys moves the
# stack patch sites the stock ones verify against.
cpm86-exp-1440-at.img: FEAT = cpm86-144feat
cpm86-exp-1440-at.img: BASE = base-1440-at.img
cpm86-exp-1440-at.img: KRNL = cpmexp.sys
cpm86-exp-1440-at.img: FTOOLS = $(EXPTOOLS)
cpm86-exp-1440-at.img: V = x
cpm86-exp-1440-at.img: cpmexp.sys base-1440-at.img | commands extra
	$(feat_image)

cpm86-exp-720-at.img: FEAT = cpm86-720feat
cpm86-exp-720-at.img: BASE = base-720-at.img
cpm86-exp-720-at.img: KRNL = cpmexp.sys
cpm86-exp-720-at.img: FTOOLS = $(EXPTOOLS)
cpm86-exp-720-at.img: V = x
cpm86-exp-720-at.img: cpmexp.sys base-720-at.img | commands extra
	$(feat_image)

cpm86-320-at.img: FEAT = cpm86-320
cpm86-320-at.img: BASE = base-320-at.img
cpm86-320-at.img: KRNL = cpm.sys
cpm86-320-at.img: ATSTART = 1
cpm86-320-at.img: FTOOLS = $(CORETOOLS) $(ASMTOOLS)
cpm86-320-at.img: cpm.sys base-320-at.img | commands
	$(twist_image)

cpm86-320.img: FEAT = cpm86-320
cpm86-320.img: BASE = base-320.img
cpm86-320.img: KRNL = cpm.sys
cpm86-320.img: FTOOLS = $(CORETOOLS) $(ASMTOOLS)
cpm86-320.img: cpm.sys base-320.img | commands
	$(twist_image)

cpm86-320-dev.img: FEAT = cpm86-320
cpm86-320-dev.img: BASE = base-320.img
cpm86-320-dev.img: FTOOLS = base/pip.cmd base/submit.cmd base/ed.cmd $(DEVTOOLS)
cpm86-320-dev.img: base-320.img
	$(twist_image)

# Experimental kernel plus the commands/ reconstruction in place of base/.
cpm86-exp-160-1-at.img: FEAT = ibmpc-514ss
cpm86-exp-160-1-at.img: BASE = base-160-at.img
cpm86-exp-160-1-at.img: KRNL = cpmexp.sys
cpm86-exp-160-1-at.img: ATSTART = 1
cpm86-exp-160-1-at.img: FTOOLS = $(EXPCORE)
cpm86-exp-160-1-at.img: cpmexp.sys base-160-at.img | commands
	$(flat_image)

cpm86-exp-160-1.img: FEAT = ibmpc-514ss
cpm86-exp-160-1.img: BASE = base-160.img
cpm86-exp-160-1.img: KRNL = cpmexp.sys
cpm86-exp-160-1.img: FTOOLS = $(EXPCORE)
cpm86-exp-160-1.img: cpmexp.sys base-160.img | commands
	$(flat_image)

cpm86-160-1-at.img: FEAT = ibmpc-514ss
cpm86-160-1-at.img: BASE = base-160-at.img
cpm86-160-1-at.img: KRNL = cpm.sys
cpm86-160-1-at.img: ATSTART = 1
cpm86-160-1-at.img: FTOOLS = $(CORETOOLS)
cpm86-160-1-at.img: cpm.sys base-160-at.img | commands
	$(flat_image)

cpm86-160-1.img: FEAT = ibmpc-514ss
cpm86-160-1.img: BASE = base-160.img
cpm86-160-1.img: KRNL = cpm.sys
cpm86-160-1.img: FTOOLS = $(CORETOOLS)
cpm86-160-1.img: cpm.sys base-160.img | commands
	$(flat_image)

cpm86-160-2.img: FEAT = ibmpc-514ss
cpm86-160-2.img: BASE = base-160.img
cpm86-160-2.img: FTOOLS = base/pip.cmd base/submit.cmd base/ed.cmd $(ASMTOOLS)
cpm86-160-2.img: base-160.img
	$(flat_image)

cpm86-160-3.img: FEAT = ibmpc-514ss
cpm86-160-3.img: BASE = base-160.img
cpm86-160-3.img: FTOOLS = $(DRTOOLS)
cpm86-160-3.img: base-160.img
	$(flat_image)

cpm86-160-4.img: FEAT = ibmpc-514ss
cpm86-160-4.img: BASE = base-160.img
cpm86-160-4.img: FTOOLS = $(BASICTOOLS)
cpm86-160-4.img: base-160.img
	$(flat_image)

cpm.sys: cpm86.h86
	cpm_gencmd cpm86.h86 8080 "CODE[A51,M0000]"
	mv cpm86.cmd cpm.sys

cpmorg.sys: cpm86org.h86
	cpm_gencmd cpm86org.h86 8080 "CODE[A51,M0000]"
	mv cpm86org.cmd cpmorg.sys

cpmexp.sys: cpm86exp.h86
	cpm_gencmd cpm86exp.h86 8080 "CODE[A51,M0000]"
	mv cpm86exp.cmd cpmexp.sys

cpmv20.sys: cpmv20.h86
	cpm_gencmd cpmv20.h86 8080 "CODE[A40]"
	mv cpmv20.cmd cpmv20.sys

cpmv20.bin: cpmv20.sys
	dd bs=128 skip=1 if=cpmv20.sys of=cpmv20.bin

cpmv20.h86: cpm.h86 mbcv20.h86 
	doscat cpm.h86 > cpmv20.h86
	cat mbcv20.h86 >> cpmv20.h86

cpm816.bin: cpm816.sys
	dd bs=128 skip=1 if=cpm816.sys of=cpm816.bin

cpm816.sys: cpm816.h86
	cpm_gencmd cpm816.h86 8080 "CODE[A40]"
	mv cpm816.cmd cpm816.sys

cpm816.h86: cpm.h86 mbc816.h86 
	doscat cpm.h86 > cpm816.h86
	cat mbc816.h86 >> cpm816.h86

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
	cpm_asm86 $<

clean:
	$(MAKE) -C $(CMDDIR) clean
	$(MAKE) -C extra clean
	rm -rf *.h86 *.lst *.sym *.log
	rm -rf cpm86.cmd cpm.sys 
	rm -rf cpm86exp.cmd cpmexp.sys 
	rm -rf cpm86org.cmd cpmorg.sys
	rm -rf cpm86-160-1-at.img cpm86-160-1.img \
        cpm86-160-2.img cpm86-160-3.img cpm86-160-4.img
	rm -rf cpm86-exp-160-1-at.img cpm86-exp-160-1.img
	rm -rf cpm86-720-at.img cpm86-exp-720-at.img base-720-at.img
	rm -rf cpm86-1440-at.img cpm86-exp-1440-at.img base-1440-at.img
	rm -rf cpm86-320-at.img cpm86-320.img cpm86-320-dev.img 
	rm -rf *.img.wrk
	rm -rf cpm816.sys cpmv20.sys cpm816.bin cpmv20.bin
	rm -rf *.xxd

dist: cpm86-160-1-at.img cpm86-160-1.img cpm86-160-2.img cpm86-160-3.img cpm86-160-4.img \
    cpm86-320.img cpm86-320-at.img cpm86-320-dev.img cpm86-1440-at.img \
	cpm86-exp-160-1.img cpm86-exp-160-1-at.img cpm86-exp-1440-at.img \
	cpm86-720-at.img cpm86-exp-720-at.img

# Verify cpm.sys and cpmorg.sys are binary-identical.
# Run after any change to pcbios.a86 to confirm parity with pcbioorg.a86.
check: cpm.sys cpmorg.sys
	cmp cpm.sys cpmorg.sys && echo "OK: cpm.sys and cpmorg.sys are identical" || \
	  { echo "FAIL: cpm.sys and cpmorg.sys differ"; exit 1; }

test: dist
	./cpm86

test-exp: dist
	./cpm86-exp

test-320: dist
	./cpm86-320
