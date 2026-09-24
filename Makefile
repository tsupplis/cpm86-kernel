all: cpm.sys cpm816.sys cpmv20.sys cpmexp.sys cpmorg.sys

# 320K disks store side 1 in reverse cylinder order (pcbios.a86 SETUP_INTREG),
# so cpmtools has to work on an untwisted copy that is twisted back at the end.
TWIST = python3 tools/cpm86twist.py
CP320 = cpmcp -f cpm86-320

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

.PHONY: all commands extra clean dist check test test-exp test-320

commands:
	$(MAKE) -C $(CMDDIR)

extra:
	$(MAKE) -C extra

cpmwk.img: base-160.img
	cp base-160.img $@

cpm86-1440-at.img: cpm.sys base-1440-at.img | commands extra
	cp base-1440-at.img $@
	cpmrm -f cpm86-144feat $@ 0:144BLDR2.CMD
	cpmcp -f cpm86-144feat $@ cpm.sys 0:CPM.SYS
	cpmcp -f cpm86-144feat $@ extra/144bldr2.cmd 0:144BLDR2.CMD
	cpmcp -f cpm86-144feat $@ extra/144pat2.cmd 0:144PAT.CMD
	cpmcp -f cpm86-144feat $@ extra/144prep2.cmd 0:144PREP.CMD
	cpmcp -f cpm86-144feat $@ extra/atinit.cmd 0:ATINIT.CMD
	cpmcp -f cpm86-144feat $@ base/pip.cmd 0:
	cpmcp -f cpm86-144feat $@ base/stat.cmd 0:
	cpmcp -f cpm86-144feat $@ base/submit.cmd 0:
	cpmcp -f cpm86-144feat $@ base/setup.cmd 0:
	cpmcp -f cpm86-144feat $@ base/dskmaint.cmd 0:
	cpmcp -f cpm86-144feat $@ base/hdmaint.cmd 0:
	cpmcp -f cpm86-144feat $@ base/function.cmd 0:
	cpmcp -f cpm86-144feat $@ base/config.cmd 0:
	cpmcp -f cpm86-144feat $@ base/assign.cmd 0:
	cpmcp -f cpm86-144feat $@ base/data.pfk 0:
	cpmcp -f cpm86-144feat $@ base/ed.cmd 0:
	cpmcp -f cpm86-144feat $@ $(TOD) 0:
	cpmcp -f cpm86-144feat $@ base/help.* 0:
	cpmcp -f cpm86-144feat $@ base/print.* 0:
	cpmcp -f cpm86-144feat $@ base/mform.* 0:
	cpmcp -f cpm86-144feat $@ base/ddt86.cmd 0:
	cpmcp -f cpm86-144feat $@ base/asm86.cmd 0:
	cpmcp -f cpm86-144feat $@ base/gencmd.cmd 0:
	cpmcp -f cpm86-144feat $@ base/gendef.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/rasm86.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/link86.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/lib86.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/xref86.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/sid86.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/pbasic.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/cbas86.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/crun86.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/mbasic86.cmd 0:
	cpmls -F -f cpm86-144feat $@ 0:*.*

# Experimental kernel plus the full commands/ reconstruction. The 1.44M loader
# and patcher must be the expkrnl builds, since cpmexp.sys moves the stack
# patch sites the stock ones verify against.
cpm86-exp-1440-at.img: cpmexp.sys base-1440-at.img | commands extra
	cp base-1440-at.img $@
	cpmrm -f cpm86-144feat $@ 0:144BLDR2.CMD
	cpmcp -f cpm86-144feat $@ cpmexp.sys 0:CPM.SYS
	cpmcp -f cpm86-144feat $@ extra/144bldrx.cmd 0:144BLDR2.CMD
	cpmcp -f cpm86-144feat $@ extra/144patx.cmd 0:144PAT.CMD
	cpmcp -f cpm86-144feat $@ extra/144prepx.cmd 0:144PREP.CMD
	cpmcp -f cpm86-144feat $@ extra/atinit.cmd 0:ATINIT.CMD
	cpmcp -f cpm86-144feat $@ $(ASM86) 0:
	cpmcp -f cpm86-144feat $@ $(DDT86) 0:
	cpmcp -f cpm86-144feat $@ $(ED) 0:
	cpmcp -f cpm86-144feat $@ $(GENCMD) 0:
	cpmcp -f cpm86-144feat $@ $(HELP) 0:
	cpmcp -f cpm86-144feat $@ $(PIP) 0:
	cpmcp -f cpm86-144feat $@ $(STAT) 0:
	cpmcp -f cpm86-144feat $@ $(SUBMIT) 0:
	cpmcp -f cpm86-144feat $@ $(TOD) 0:
	cpmcp -f cpm86-144feat $@ base/setup.cmd 0:
	cpmcp -f cpm86-144feat $@ base/dskmaint.cmd 0:
	cpmcp -f cpm86-144feat $@ base/hdmaint.cmd 0:
	cpmcp -f cpm86-144feat $@ base/function.cmd 0:
	cpmcp -f cpm86-144feat $@ base/config.cmd 0:
	cpmcp -f cpm86-144feat $@ base/assign.cmd 0:
	cpmcp -f cpm86-144feat $@ base/data.pfk 0:
	cpmcp -f cpm86-144feat $@ base/help.hlp 0:
	cpmcp -f cpm86-144feat $@ base/print.* 0:
	cpmcp -f cpm86-144feat $@ base/mform.* 0:
	cpmcp -f cpm86-144feat $@ base/gendef.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/rasm86.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/link86.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/lib86.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/xref86.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/sid86.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/pbasic.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/cbas86.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/crun86.cmd 0:
	cpmcp -f cpm86-144feat $@ dev/mbasic86.cmd 0:
	cpmls -F -f cpm86-144feat $@ 0:*.*

cpm86-320-at.img: cpm.sys base-320-at.img | commands
	$(TWIST) untwist base-320-at.img $@.wrk
	$(CP320) $@.wrk cpm.sys 0:CPM.SYS
	$(CP320) $@.wrk extra/atinit.cmd 0:ATINIT.CMD
	$(CP320) $@.wrk base/pip.cmd 0:
	$(CP320) $@.wrk base/stat.cmd 0:
	$(CP320) $@.wrk base/submit.cmd 0:
	$(CP320) $@.wrk base/setup.cmd 0:
	$(CP320) $@.wrk base/dskmaint.cmd 0:
	$(CP320) $@.wrk base/hdmaint.cmd 0:
	$(CP320) $@.wrk base/function.cmd 0:
	$(CP320) $@.wrk base/config.cmd 0:
	$(CP320) $@.wrk base/assign.cmd 0:
	$(CP320) $@.wrk base/data.pfk 0:
	$(CP320) $@.wrk base/ed.cmd 0:
	$(CP320) $@.wrk $(TOD) 0:
	$(CP320) $@.wrk base/help.* 0:
	$(CP320) $@.wrk base/print.* 0:
	$(CP320) $@.wrk base/mform.* 0:
	$(CP320) $@.wrk base/ddt86.cmd 0:
	$(CP320) $@.wrk base/asm86.cmd 0:
	$(CP320) $@.wrk base/gencmd.cmd 0:
	$(CP320) $@.wrk base/gendef.cmd 0:
	cpmls -F -f cpm86-320 $@.wrk 0:*.*
	$(TWIST) twist $@.wrk $@
	rm -f $@.wrk

cpm86-320.img: cpm.sys base-320.img | commands
	$(TWIST) untwist base-320.img $@.wrk
	$(CP320) $@.wrk cpm.sys 0:CPM.SYS
	$(CP320) $@.wrk base/pip.cmd 0:
	$(CP320) $@.wrk base/stat.cmd 0:
	$(CP320) $@.wrk base/submit.cmd 0:
	$(CP320) $@.wrk base/setup.cmd 0:
	$(CP320) $@.wrk base/dskmaint.cmd 0:
	$(CP320) $@.wrk base/hdmaint.cmd 0:
	$(CP320) $@.wrk base/function.cmd 0:
	$(CP320) $@.wrk base/config.cmd 0:
	$(CP320) $@.wrk base/assign.cmd 0:
	$(CP320) $@.wrk base/data.pfk 0:
	$(CP320) $@.wrk base/ed.cmd 0:
	$(CP320) $@.wrk $(TOD) 0:
	$(CP320) $@.wrk base/help.* 0:
	$(CP320) $@.wrk base/print.* 0:
	$(CP320) $@.wrk base/mform.* 0:
	$(CP320) $@.wrk base/ddt86.cmd 0:
	$(CP320) $@.wrk base/asm86.cmd 0:
	$(CP320) $@.wrk base/gencmd.cmd 0:
	$(CP320) $@.wrk base/gendef.cmd 0:
	cpmls -F -f cpm86-320 $@.wrk 0:*.*
	$(TWIST) twist $@.wrk $@
	rm -f $@.wrk

cpm86-320-dev.img: base-320.img 
	$(TWIST) untwist base-320.img $@.wrk
	$(CP320) $@.wrk base/pip.cmd 0:
	$(CP320) $@.wrk base/submit.cmd 0:
	$(CP320) $@.wrk base/ed.cmd 0:
	$(CP320) $@.wrk dev/rasm86.cmd 0:
	$(CP320) $@.wrk dev/link86.cmd 0:
	$(CP320) $@.wrk dev/lib86.cmd 0:
	$(CP320) $@.wrk dev/xref86.cmd 0:
	$(CP320) $@.wrk dev/sid86.cmd 0:
	$(CP320) $@.wrk dev/pbasic.cmd 0:
	$(CP320) $@.wrk dev/cbas86.cmd 0:
	$(CP320) $@.wrk dev/crun86.cmd 0:
	$(CP320) $@.wrk dev/mbasic86.cmd 0:
	cpmls -F -f cpm86-320 $@.wrk 0:*.*
	$(TWIST) twist $@.wrk $@
	rm -f $@.wrk

# Experimental kernel plus the commands/ reconstruction in place of base/.
cpm86-exp-160-1-at.img: cpmexp.sys base-160.img | commands
	cp base-160-at.img $@
	cpmcp -f ibmpc-514ss $@ cpmexp.sys 0:CPM.SYS
	cpmcp -f ibmpc-514ss $@ extra/atinit.cmd 0:ATINIT.CMD
	cpmcp -f ibmpc-514ss $@ $(PIP) 0:
	cpmcp -f ibmpc-514ss $@ $(STAT) 0:
	cpmcp -f ibmpc-514ss $@ $(SUBMIT) 0:
	cpmcp -f ibmpc-514ss $@ $(ED) 0:
	cpmcp -f ibmpc-514ss $@ $(HELP) 0:
	cpmcp -f ibmpc-514ss $@ $(TOD) 0:
	cpmcp -f ibmpc-514ss $@ base/setup.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/dskmaint.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/hdmaint.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/function.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/config.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/assign.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/data.pfk 0:
	cpmcp -f ibmpc-514ss $@ base/help.hlp 0:
	cpmcp -f ibmpc-514ss $@ base/print.* 0:
	cpmcp -f ibmpc-514ss $@ base/mform.* 0:
	cpmls -F -f ibmpc-514ss $@ 0:*.*

cpm86-160-1-at.img: cpm.sys base-160.img | commands
	cp base-160-at.img $@
	cpmcp -f ibmpc-514ss $@ cpm.sys 0:CPM.SYS
	cpmcp -f ibmpc-514ss $@ extra/atinit.cmd 0:ATINIT.CMD
	cpmcp -f ibmpc-514ss $@ base/pip.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/stat.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/submit.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/setup.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/dskmaint.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/hdmaint.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/function.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/config.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/assign.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/data.pfk 0:
	cpmcp -f ibmpc-514ss $@ base/ed.cmd 0:
	cpmcp -f ibmpc-514ss $@ $(TOD) 0:
	cpmcp -f ibmpc-514ss $@ base/help.* 0:
	cpmcp -f ibmpc-514ss $@ base/print.* 0:
	cpmcp -f ibmpc-514ss $@ base/mform.* 0:
	cpmls -F -f ibmpc-514ss $@ 0:*.*

cpm86-160-1.img: cpm.sys base-160.img | commands
	cp base-160.img $@
	cpmcp -f ibmpc-514ss $@ cpm.sys 0:CPM.SYS
	cpmcp -f ibmpc-514ss $@ base/pip.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/stat.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/submit.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/setup.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/dskmaint.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/hdmaint.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/function.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/config.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/assign.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/data.pfk 0:
	cpmcp -f ibmpc-514ss $@ base/ed.cmd 0:
	cpmcp -f ibmpc-514ss $@ $(TOD) 0:
	cpmcp -f ibmpc-514ss $@ base/help.* 0:
	cpmcp -f ibmpc-514ss $@ base/print.* 0:
	cpmcp -f ibmpc-514ss $@ base/mform.* 0:
	cpmls -F -f ibmpc-514ss $@ 0:*.*

cpm86-exp-160-1.img: cpmexp.sys base-160.img | commands
	cp base-160.img $@
	cpmcp -f ibmpc-514ss $@ cpmexp.sys 0:CPM.SYS
	cpmcp -f ibmpc-514ss $@ $(PIP) 0:
	cpmcp -f ibmpc-514ss $@ $(STAT) 0:
	cpmcp -f ibmpc-514ss $@ $(SUBMIT) 0:
	cpmcp -f ibmpc-514ss $@ $(ED) 0:
	cpmcp -f ibmpc-514ss $@ $(HELP) 0:
	cpmcp -f ibmpc-514ss $@ $(TOD) 0:
	cpmcp -f ibmpc-514ss $@ base/setup.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/dskmaint.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/hdmaint.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/function.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/config.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/assign.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/data.pfk 0:
	cpmcp -f ibmpc-514ss $@ base/help.hlp 0:
	cpmcp -f ibmpc-514ss $@ base/print.* 0:
	cpmcp -f ibmpc-514ss $@ base/mform.* 0:
	cpmls -F -f ibmpc-514ss $@ 0:*.*

cpm86-160-2.img: base-160.img 
	cp base-160.img $@
	cpmcp -f ibmpc-514ss $@ base/pip.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/submit.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/ed.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/ddt86.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/asm86.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/gencmd.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/gendef.cmd 0:
	cpmls -F -f ibmpc-514ss $@ 0:*.*

cpm86-160-3.img: cpm.sys base-160.img 
	cp base-160.img $@
	cpmcp -f ibmpc-514ss $@ dev/rasm86.cmd 0:
	cpmcp -f ibmpc-514ss $@ dev/link86.cmd 0:
	cpmcp -f ibmpc-514ss $@ dev/lib86.cmd 0:
	cpmcp -f ibmpc-514ss $@ dev/xref86.cmd 0:
	cpmcp -f ibmpc-514ss $@ dev/sid86.cmd 0:
	cpmls -F -f ibmpc-514ss $@ 0:*.*

cpm86-160-4.img: cpm.sys base-160.img 
	cp base-160.img $@
	cpmcp -f ibmpc-514ss $@ dev/pbasic.cmd 0:
	cpmcp -f ibmpc-514ss $@ dev/cbas86.cmd 0:
	cpmcp -f ibmpc-514ss $@ dev/crun86.cmd 0:
	cpmcp -f ibmpc-514ss $@ dev/mbasic86.cmd 0:
	cpmls -F -f ibmpc-514ss $@ 0:*.*

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
	rm -rf cpm86-exp-160-1-at.img cpm86-exp-160-1.img cpm86-exp-1440-at.img
	rm -rf cpm86-320-at.img cpm86-320.img cpm86-320-dev.img cpm86-1440-at.img
	rm -rf *.img.wrk
	rm -rf cpm816.sys cpmv20.sys cpm816.bin cpmv20.bin
	rm -rf *.xxd

dist: cpm86-160-1-at.img cpm86-160-1.img cpm86-160-2.img cpm86-160-3.img cpm86-160-4.img \
    cpm86-320.img cpm86-320-at.img cpm86-320-dev.img cpm86-1440-at.img \
	cpm86-exp-160-1.img cpm86-exp-160-1-at.img cpm86-exp-1440-at.img

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
