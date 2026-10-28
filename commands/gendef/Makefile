INTEL_PLM86=intel_plm86
INTEL_ASM86=intel_asm86
INTEL_LOC86=intel_loc86
INTEL_LINK86=intel_link86
INTEL_OH86=intel_oh86
GENCMD=cpm86_gencmd

TOOLS=gendef.cmd

SNIPPETS=

.PHONY: all check clean
.DELETE_ON_ERROR:
all: $(TOOLS) $(SNIPPETS)

gendef.obj gtoken.obj gscan.obj: glit.plb copyrt.lit
gscan.obj: gpas.plb

# BBB and MMM for gencmd's data[bBBB,mMMM,xfff], derived from gendef.mp2:
#   BBB = start of dats segment / 16 (e.g. 1000)
#   MMM = (start of memory segment - start of dats segment) / 16
# Recursively expanded on purpose: gendef.mp2 only exists once gendef.h86 is built.
PARA = sub(/H$$/,"",s); sub(/.$$/,"",s); sub(/^0+/,"",s); print tolower(s); exit
GENDEF_BASE = $(shell awk '/DATS +DATA/{s=$$1; $(PARA)}' gendef.mp2)
GENDEF_MEM  = $(shell awk '/MEMORY +MEMORY/{s=$$1; $(PARA)}' gendef.mp2)
GENDEF_MIN  = $(shell printf '%x' $$((0x$(GENDEF_MEM)-0x$(GENDEF_BASE))))

gendef.cmd: gendef.h86
	@test -n "$(GENDEF_BASE)" -a -n "$(GENDEF_MEM)" || \
	  { echo "gendef: cannot derive DATS/MEMORY from gendef.mp2"; exit 1; }
	$(GENCMD) $< 'data[b$(GENDEF_BASE) m$(GENDEF_MIN) xfff]'
	cmdinfo $@

gendef.loc: gendef.obj gtoken.obj gscan.obj gemit.obj scd.obj
	$(INTEL_LINK86) scd.obj, gendef.obj, gtoken.obj, gscan.obj, gemit.obj to $(basename $@).lnk
	$(INTEL_LOC86) $(basename $@).lnk 'od(sm(code,dats,data,stack,const))' \
		'ad(sm(code(0),dats(10000h)))' 'ss(stack(+32))'  to $(basename $@).loc

%.h86: %.loc
	$(INTEL_OH86) $<
	mv $*.hex $*.h86

%.obj: %.a86
	$(INTEL_ASM86) $<

%.obj: %.plm
	$(INTEL_PLM86) $< debug 'optimize(3)' xref

check: gendef.cmd
	python3 check.py

clean:
	rm -f *.sys *.loc *.cmd *.obj *.h86 *.sym *.lin *.lst *.prn ccpmtest.img
	rm -f *.loc *.mp? *.lnk
