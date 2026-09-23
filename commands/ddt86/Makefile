INTEL_PLM86=intel_plm86
INTEL_ASM86=intel_asm86
INTEL_LINK86=intel_link86
INTEL_LOC86=intel_loc86
INTEL_OH86=intel_oh86
ASM86=cpm86_asm86
GENCMD=cpm86_gencmd
RASM86=pcdev_rasm86
PLI86=drplicpm_pc
PLILINK86=drplicpm_link

TOOLS=gentab.cmd ddt86.cmd

SNIPPETS=

all: $(TOOLS) $(SNIPPETS)

#  the value for the minimum code group required comes from the start of
#  the ??seg as listed in ass86.mp2
ddt86.cmd: ddt86m.h86
	$(GENCMD) $< 8080 'code[m379]'
	mv ddt86m.cmd ddt86.cmd

ddt86m.h86: ddt86.h86 dis86.h86 ass86.h86
	doscat $^ > $@

ddt86.h86: ddt86.a86
	$(ASM86) ddt86 '$$fi'

dis86.h86: dis86.abs
	$(INTEL_OH86) $< to $@

dis86.abs: dislnk86.obj dis86.obj ins86.obj
	$(INTEL_LINK86) dislnk86.obj, dis86.obj, ins86.obj to $(basename $@).lnk
	$(INTEL_LOC86) $(basename $@).lnk to $@ \
        'ad(sm(dats(0),code(0h)))' 'od(sm(dats,code,const,data))'

ass86.h86: ass86.abs
	$(INTEL_OH86) $< to $@

ass86.abs: asslnk86.obj asmtab.obj ass86.obj dis86.abs
	$(INTEL_LINK86) asslnk86.obj, asmtab.obj, ass86.obj, 'po(dis86.abs)' \
        to $(basename $@).lnk$@
	$(INTEL_LOC86) $(basename $@).lnk to $@ \
        'ad(sm(dats(0),code(0h)))' 'od(sm(dats,code,const,data))'

op86.dat: gentab.cmd

gentab.cmd: gentab.obj
	$(PLILINK86) gentab=gentab '[data[ori[0]]'

cpmif.obj: cpmif.a86
	$(RASM86) $^

%.obj: %.asm
	$(INTEL_ASM86) $^

%.obj: %.pli
	$(PLI86) $^ \$$d

%.obj: %.plm
	$(INTEL_PLM86) $^ debug 'optimize(2)' 'pagewidth(100)' xref

clean:
	rm -f *.sys *.cmd *.obj *.exe *.map *.h86 *.sym 
	rm -f *.lin *.lst *.prn ccpmtest.img ddt86m.h86 *.abs *.lnk *.mp?

ccpmtest.img: $(TOOLS) Makefile startup.0
	cp cpmbase.img ccpmtest.img
	cpmcp -f ibmpc-514ss ccpmtest.img ddt86.cmd 0:
	cpmcp -f ibmpc-514ss ccpmtest.img startup.0 0:
	cpmls -F -f ibmpc-514ss ccpmtest.img 0:*.*

test: ccpmtest $(TOOLS)

ccpmtest: ccpmtest.img $(TOOLS)
	@./ccpm86
