INTEL_PLM86=intel_plm86
INTEL_ASM86=intel_asm86
INTEL_LOC86=intel_loc86
INTEL_LINK86=intel_link86
INTEL_OH86=intel_oh86
GENCMD=cpm86_gencmd

TOOLS=ed.cmd

SNIPPETS=

all: $(TOOLS) $(SNIPPETS)

# BBB and MMM for gencmd's data[bBBB,mMMM,xfff], derived from ed.mp2:
#   BBB = start of dats segment / 16 (e.g. 1000)
#   MMM = (start of memory segment - start of dats segment) / 16
# Recursively expanded on purpose: ed.mp2 only exists once ed.h86 is built.
PARA = sub(/H$$/,"",s); sub(/.$$/,"",s); sub(/^0+/,"",s); print tolower(s); exit
ED_BASE = $(shell awk '/DATS +DATA/{s=$$1; $(PARA)}' ed.mp2)
ED_MEM  = $(shell awk '/MEMORY +MEMORY/{s=$$1; $(PARA)}' ed.mp2)
ED_MIN  = $(shell printf '%x' $$((0x$(ED_MEM)-0x$(ED_BASE))))

ed.cmd: ed.h86
	@test -n "$(ED_BASE)" -a -n "$(ED_MEM)" || \
	  { echo "ed: cannot derive DATS/MEMORY from ed.mp2"; exit 1; }
	$(GENCMD) $< 'data[b$(ED_BASE) m$(ED_MIN) xfff]'
	cmdinfo $@

ed.loc: ed.obj scd.obj
	$(INTEL_LINK86) scd.obj, $(basename $@).obj to $(basename $@).lnk
	$(INTEL_LOC86) $(basename $@).lnk 'od(sm(code,dats,data,stack,const))' \
		'ad(sm(code(0),dats(10000h)))' 'ss(stack(+32))'  to $(basename $@).loc

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
