INTEL_PLM86=intel_plm86
INTEL_ASM86=intel_asm86
INTEL_LOC86=intel_loc86
INTEL_LINK86=intel_link86
INTEL_OH86=intel_oh86
GENCMD=cpm86_gencmd
CPM_ASM86=cpm86_asm86

TOOLS=pip.cmd 

SNIPPETS=

all: $(TOOLS) $(SNIPPETS)

pip.cmd: pip.h86
	$(GENCMD) $< 'data[b1000 m280 xfff]'
	cmdinfo $@

pip.loc: pip.obj inpout.obj scd1.obj
	$(INTEL_LINK86) scd1.obj, inpout.obj, $(basename $@).obj to $(basename $@).lnk
	$(INTEL_LOC86) $(basename $@).lnk 'od(sm(code,dats,data,stack,const))' \
		'ad(sm(code(0),dats(10000h)))' 'ss(stack(+32))'  to $(basename $@).loc

bptest.cmd: bptest.h86
	$(GENCMD) $< 8080
	cmdinfo $@

bptest.h86: bptest.a86
	unix2dos $<
	$(CPM_ASM86) $<

%.h86: %.loc
	$(INTEL_OH86) $^
	mv $*.hex $*.h86

%.obj: %.a86
	$(INTEL_ASM86) $^

%.obj: %.plm
	$(INTEL_PLM86) $^ debug 'optimize(3)' xref

clean:
	rm -f *.sys *.loc *.cmd *.obj *.h86 *.sym *.lin *.lst *.prn ccpmtest.img
	rm -f *.loc *.mp? *.lnk

# emu2 runs the CP/M-86 .cmd directly; EMU2_DRIVE_A maps A: onto a host dir.
# Outputs use .prn so 'clean' sweeps them.  PIP pads its output with NULs to the
# 128-byte record boundary, so comparing against the host source strips the pad.
TESTSRC=scd1.a86

test: pip.cmd
	@rm -f t?.prn
	@echo "-- plain copy"
	emu2 pip.cmd t1.prn=$(TESTSRC)
	perl -0pe 's/\x00+\z//' t1.prn | cmp - $(TESTSRC)
	@echo "-- copy to drive A:"
	EMU2_DRIVE_A=`pwd` emu2 pip.cmd a:t2.prn=$(TESTSRC)
	cmp t1.prn t2.prn
	@echo "-- concatenate two sources"
	emu2 pip.cmd t3.prn=$(TESTSRC),$(TESTSRC)
	cat t1.prn t1.prn | cmp - t3.prn
	@echo "-- copy with [V] verify"
	emu2 pip.cmd 't4.prn=$(TESTSRC)[V]'
	cmp t1.prn t4.prn
	@echo "PASS: pip"

cpmtest.img: bptest.cmd pip.cmd cpmbase.img
	cp cpmbase.img cpmtest.img
	cpmrm -f ibmpc-514ss cpmtest.img 0:*.cmd
	cpmrm -f ibmpc-514ss cpmtest.img 0:test.txt
	cpmcp -f ibmpc-514ss cpmtest.img bptest.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img pip.cmd 0:
	cpmls -F -f ibmpc-514ss cpmtest.img 0:*.*

