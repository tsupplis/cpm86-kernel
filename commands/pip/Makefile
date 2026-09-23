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

cpmtest.img: bptest.cmd pip.cmd cpmbase.img
	cp cpmbase.img cpmtest.img
	cpmrm -f ibmpc-514ss cpmtest.img 0:*.cmd
	cpmrm -f ibmpc-514ss cpmtest.img 0:test.txt
	cpmcp -f ibmpc-514ss cpmtest.img bptest.cmd 0:
	cpmcp -f ibmpc-514ss cpmtest.img pip.cmd 0:
	cpmls -F -f ibmpc-514ss cpmtest.img 0:

