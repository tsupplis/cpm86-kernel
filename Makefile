all: cpm86.sys 

cpm86.img: cpm86.sys base.img
	cp base.img cpm86.img
	cp base.img cpmwk.img
	cpmrm -f ibmpc-514ss cpm86.img 0:CPM.SYS
	cpmcp -f ibmpc-514ss cpm86.img cpm86.sys 0:CPM.SYS
	cpmcp -f ibmpc-514ss cpm86.img extra/atinit.cmd 0:ATINIT.CMD
	cpmls -F -f ibmpc-514ss cpm86.img 0:*.*

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
	cpmrm -f ibmpc-514ss cpm86.img 0:cpm.sys
	cpmcp -f ibmpc-514ss cpm86.img cpm86.sys 0:cpm.sys

clean:
	rm -rf *.h86 *.lst *.sym *.log
	rm -rf cpm86.cmd cpm86.sys 
	rm -rf cpm86.img work.img
	rm -rf *.xxd

test: cpm86.img
	./cpm86
