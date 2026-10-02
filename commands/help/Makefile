INTEL_PLM86=intel_plm86
INTEL_ASM86=intel_asm86
INTEL_LOC86=intel_loc86
INTEL_LINK86=intel_link86
INTEL_OH86=intel_oh86
GENCMD=cpm86_gencmd

TOOLS=help.cmd
DATA=help.hlp

SNIPPETS=

all: $(TOOLS) $(DATA) $(SNIPPETS)

# Build help.hlp from help.dat using the index generator tool.
# Edit help.dat to change topics; the index is regenerated automatically.
help.hlp: help.dat ../../tools/help_hlp.py
	python3 ../../tools/help_hlp.py help.dat help.hlp

# BBB and MMM for gencmd's data[bBBB,mMMM,xfff], derived from help.mp2:
#   BBB = start of dats segment / 16 (e.g. 1000)
#   MMM = (start of memory segment - start of dats segment) / 16
# Recursively expanded on purpose: help.mp2 only exists once help.h86 is built.
PARA = sub(/H$$/,"",s); sub(/.$$/,"",s); sub(/^0+/,"",s); print tolower(s); exit
HELP_BASE = $(shell awk '/DATS +DATA/{s=$$1; $(PARA)}' help.mp2)
HELP_MEM  = $(shell awk '/MEMORY +MEMORY/{s=$$1; $(PARA)}' help.mp2)
HELP_MIN  = $(shell printf '%x' $$((0x$(HELP_MEM)-0x$(HELP_BASE))))

help.cmd: help.h86
	@test -n "$(HELP_BASE)" -a -n "$(HELP_MEM)" || \
	  { echo "help: cannot derive DATS/MEMORY from help.mp2"; exit 1; }
	$(GENCMD) $< 'data[b$(HELP_BASE) m$(HELP_MIN) xfff]'
	cmdinfo $@

help.loc: help.obj scd.obj
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
	rm -f help.hlp
