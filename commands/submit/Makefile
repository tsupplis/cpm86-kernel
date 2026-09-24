INTEL_PLM86=intel_plm86
INTEL_ASM86=intel_asm86
INTEL_LOC86=intel_loc86
INTEL_LINK86=intel_link86
INTEL_OH86=intel_oh86
ASM86=cpm86_asm86
GENCMD=cpm86_gencmd

TOOLS=submit.cmd

SNIPPETS=

all: $(TOOLS) $(SNIPPETS)

submit.cmd: submit.h86
	$(GENCMD) $< data[b1000]
	cmdinfo $@

# scd links first so its entry stub lands at code offset 0.
# Unlike pip, the stack sits between dats and the PL/M data: the shipped binary
# has SP=0130h with PL/M data starting just above it.  PL/M-86 contributes its
# own stack to the group, so +16 (not +46) is what lands stack_base on 0130h.
submit.loc: submit.obj scd.obj
	$(INTEL_LINK86) scd.obj, $(basename $@).obj to $(basename $@).lnk
	$(INTEL_LOC86) $(basename $@).lnk 'od(sm(code,dats,stack,data,const))' \
		'ad(sm(code(0),dats(10000h),const(109f0h)))' 'ss(stack(+16))'  to $(basename $@).loc

%.h86: %.loc
	$(INTEL_OH86) $^
	mv $*.hex $*.h86

%.obj: %.a86
	$(INTEL_ASM86) $^

%.h86: %.a86
	$(ASM86) $^

%.obj: %.plm
	$(INTEL_PLM86) $^ debug 'optimize(3)' xref

clean:
	rm -f *.sys *.loc *.cmd *.obj *.h86 *.sym *.lin *.lst *.prn cpmtest.img
	rm -f *.loc *.mp? *.lnk *.hex

cpmtest.img: test.sub submit.cmd cpmbase.img
	cp cpmbase.img cpmtest.img
	cpmrm -f ibmpc-514ss cpmtest.img 0:*.cmd
	cpmrm -f ibmpc-514ss cpmtest.img 0:test.sub
	cpmcp -f ibmpc-514ss cpmtest.img submit.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img test.sub 0:
	cpmls -F -f ibmpc-514ss cpmtest.img 0:*.*


