all: cpm.sys cpm816.sys cpmv20.sys

cpmwk.img: base.img
	cp base.img $@

cpm86-at-large.img: cpm.sys base-large.img 
	cp base-large.img $@
	cpmcp -f ibmpc-514ds $@ cpm.sys 0:CPM.SYS
	cpmcp -f ibmpc-514ds $@ extra/atinit.cmd 0:ATINIT.CMD
	cpmcp -f ibmpc-514ds $@ base/pip.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/stat.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/submit.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/setup.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/dskmaint.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/hdmaint.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/function.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/config.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/assign.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/data.pfk 0:
	cpmcp -f ibmpc-514ds $@ base/ed.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/tod.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/help.* 0:
	cpmcp -f ibmpc-514ds $@ base/print.* 0:
	cpmcp -f ibmpc-514ds $@ base/mform.* 0:
	cpmcp -f ibmpc-514ds $@ base/ddt86.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/asm86.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/gencmd.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/gendef.cmd 0:
	cpmls -F -f ibmpc-514ds $@ 0:*.*

cpm86-large.img: cpm.sys base-large.img 
	cp base-large.img $@
	cpmcp -f ibmpc-514ds $@ cpm.sys 0:CPM.SYS
	cpmcp -f ibmpc-514ds $@ base/pip.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/stat.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/submit.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/setup.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/dskmaint.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/hdmaint.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/function.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/config.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/assign.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/data.pfk 0:
	cpmcp -f ibmpc-514ds $@ base/ed.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/tod.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/help.* 0:
	cpmcp -f ibmpc-514ds $@ base/print.* 0:
	cpmcp -f ibmpc-514ds $@ base/mform.* 0:
	cpmcp -f ibmpc-514ds $@ base/ddt86.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/asm86.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/gencmd.cmd 0:
	cpmcp -f ibmpc-514ds $@ base/gendef.cmd 0:
	cpmls -F -f ibmpc-514ds $@ 0:*.*

cpm86-at-1.img: cpm.sys base.img 
	cp base-at.img $@
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
	cpmcp -f ibmpc-514ss $@ base/tod.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/help.* 0:
	cpmcp -f ibmpc-514ss $@ base/print.* 0:
	cpmcp -f ibmpc-514ss $@ base/mform.* 0:
	cpmls -F -f ibmpc-514ss $@ 0:*.*

cpm86-1.img: cpm.sys base.img 
	cp base.img $@
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
	cpmcp -f ibmpc-514ss $@ base/tod.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/help.* 0:
	cpmcp -f ibmpc-514ss $@ base/print.* 0:
	cpmcp -f ibmpc-514ss $@ base/mform.* 0:
	cpmls -F -f ibmpc-514ss $@ 0:*.*

cpm86-2.img: base.img 
	cp base.img $@
	cpmcp -f ibmpc-514ss $@ base/pip.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/submit.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/ed.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/ddt86.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/asm86.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/gencmd.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/gendef.cmd 0:
	cpmls -F -f ibmpc-514ss $@ 0:*.*

cpm86-3.img: cpm.sys base.img 
	cp base.img $@
	cpmcp -f ibmpc-514ss $@ dev/rasm86.cmd 0:
	cpmcp -f ibmpc-514ss $@ dev/link86.cmd 0:
	cpmcp -f ibmpc-514ss $@ dev/lib86.cmd 0:
	cpmcp -f ibmpc-514ss $@ dev/xref86.cmd 0:
	cpmcp -f ibmpc-514ss $@ dev/sid86.cmd 0:
	cpmls -F -f ibmpc-514ss $@ 0:*.*

cpm86-4.img: cpm.sys base.img 
	cp base.img $@
	cpmcp -f ibmpc-514ss $@ dev/pbasic.cmd 0:
	cpmcp -f ibmpc-514ss $@ dev/cbas86.cmd 0:
	cpmcp -f ibmpc-514ss $@ dev/crun86.cmd 0:
	cpmcp -f ibmpc-514ss $@ dev/mbasic86.cmd 0:
	cpmls -F -f ibmpc-514ss $@ 0:*.*

cpm.sys: cpm86.h86
	cpm_gencmd cpm86.h86 8080 "CODE[A51,M0000]"
	mv cpm86.cmd cpm.sys

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

cpm.h86: ccp.h86 bdos.h86
	doscat ccp.h86 > cpm.h86
	cat bdos.h86  >> cpm.h86

%.h86: %.a86
	cpm_asm86 $<

cpmnew: cpm.sys
	cpmrm -f ibmpc-514ss cpm86-1.img 0:cpm.sys
	cpmcp -f ibmpc-514ss cpm86-1.img cpm.sys 0:cpm.sys
	cpmrm -f ibmpc-514ss cpm86-at-1.img 0:cpm.sys
	cpmcp -f ibmpc-514ss cpm86-at-1.img cpm.sys 0:cpm.sys

clean:
	rm -rf *.h86 *.lst *.sym *.log
	rm -rf cpm86.cmd cpm.sys 
	rm -rf cpm86-at-1.img cpm86-1.img cpm86-2.img cpm86-3.img cpm86-4.img
	rm -rf cpm86-at-large.img cpm86-large.img
	rm -rf cpm816.sys cpmv20.sys cpm816.bin cpmv20.bin
	rm -rf *.xxd

dist: cpm86-at-1.img cpm86-1.img cpm86-2.img cpm86-3.img cpm86-4.img \
    cpm86-large.img cpm86-at-large.img

test: dist
	./cpm86
