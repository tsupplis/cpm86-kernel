INTEL_PLM86=intel_plm86
INTEL_ASM86=intel_asm86
INTEL_LOC86=intel_loc86
INTEL_LINK86=intel_link86
INTEL_OH86=intel_oh86
ASM86=cpm86_asm86
GENCMD=cpm86_gencmd

TOOLS=gencmd.cmd

SNIPPETS=

all: $(TOOLS) $(SNIPPETS)

# BBB and MMM for gencmd's data[bBBB,mMMM,xfff], derived from gencmd.mp2:
#   BBB = start of dats segment / 16 (e.g. 1000)
#   MMM = (start of memory segment - start of dats segment) / 16
PARA = sub(/H$$/,"",s); sub(/.$$/,"",s); sub(/^0+/,"",s); print tolower(s); exit
GENCMD_BASE = $(shell awk '/DATS +DATA/{s=$$1; $(PARA)}' gencmd.mp2)
GENCMD_MEM  = $(shell awk '/MEMORY +MEMORY/{s=$$1; $(PARA)}' gencmd.mp2)
GENCMD_MIN  = $(shell printf '%x' $$((0x$(GENCMD_MEM)-0x$(GENCMD_BASE))))

gencmd.cmd: gencmd.h86
	@test -n "$(GENCMD_BASE)" -a -n "$(GENCMD_MEM)" || \
	  { echo "gencmd: cannot derive DATS/MEMORY from gencmd.mp2"; exit 1; }
	$(GENCMD) $< 'data[b$(GENCMD_BASE) m$(GENCMD_MIN) xfff]'
	cmdinfo $@

%.cmd: %.h86
	@test -n "$(GENCMD_BASE)" -a -n "$(GENCMD_MEM)" || \
	  { echo "gencmd: cannot derive DATS/MEMORY from gencmd.mp2"; exit 1; }
	$(GENCMD) $< 'data[b$(GENCMD_BASE) m$(GENCMD_MIN) xfff]'
	cmdinfo $@

gencmd.loc: gencmd.obj scd.obj
	$(INTEL_LINK86) scd.obj, $(basename $@).obj to $(basename $@).lnk
	$(INTEL_LOC86) $(basename $@).lnk 'od(sm(code,dats,data,stack,const))' \
		'ad(sm(code(0),dats(10000h)))' 'ss(stack(+32))' to $(basename $@).loc

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


test.h86: gencmd.h86
	cp $< $@

test.cmd: test.h86 gencmd.cmd
	@test -n "$(GENCMD_BASE)" -a -n "$(GENCMD_MEM)" || \
	  { echo "gencmd: cannot derive DATS/MEMORY from gencmd.mp2"; exit 1; }
	emu2 gencmd.cmd test.h86 'data[b$(GENCMD_BASE) m$(GENCMD_MIN) xfff]'
	cmdinfo test.cmd


check: test.cmd gencmd.cmd hellob.cmd
	cmp gencmd.cmd test.cmd
	cmp hellob.cmd hellob.ref

hellob.h86: hellob.a86
	cpm86_asm86 hellob

hellob.cmd: hellob.h86 gencmd.cmd
	emu2 gencmd.cmd $(basename $<).h86 8080
