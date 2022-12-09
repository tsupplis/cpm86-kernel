all: cpm86.sys 

cpmwk.img: base.img
	cp base.img $@

cpm86-1.img: cpm86.sys base.img 
	cp base.img $@
	cpmcp -f ibmpc-514ss $@ cpm86.sys 0:CPM.SYS
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

cpm86-2.img: base.img 
	cp base.img $@
	cpmcp -f ibmpc-514ss $@ cpm86.sys 0:CPM.SYS
	cpmcp -f ibmpc-514ss $@ extra/atinit.cmd 0:ATINIT.CMD
	cpmcp -f ibmpc-514ss $@ base/pip.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/stat.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/submit.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/ed.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/ddt86.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/asm86.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/gencmd.cmd 0:
	cpmcp -f ibmpc-514ss $@ base/gendef.cmd 0:
	cpmls -F -f ibmpc-514ss $@ 0:*.*

cpm86.sys: cpm86.h86
	cpm_gencmd cpm86.h86 8080 "CODE[A51,M0000]"
	mv cpm86.cmd cpm86.sys

cpm86.h86: cpm.h86 pcbios.h86
	doscat cpm.h86 > cpm86.h86
	cat pcbios.h86 >> cpm86.h86

cpm.h86: ccp.h86 bdos.h86
	doscat ccp.h86 > cpm.h86
	cat bdos.h86  >> cpm.h86

%.h86: %.a86
	cpm_asm86 $<

cpmnew: cpm86.sys
	cpmrm -f ibmpc-514ss cpm86-1.img 0:cpm.sys
	cpmcp -f ibmpc-514ss cpm86-1.img cpm86.sys 0:cpm.sys

clean:
	rm -rf *.h86 *.lst *.sym *.log
	rm -rf cpm86.cmd cpm86.sys 
	rm -rf cpm86-1.img cpm86-2.img
	rm -rf *.xxd

dist: cpm86-1.img cpm86-2.img

test: dist
	./cpm86
