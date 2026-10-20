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

# HELP's native indexer requires CRLF. Convert a temporary copy so the
# repository's LF text remains editable without rebuilding a malformed index.
help.hlp: help.cmd help.dat
	@tmp=$$(mktemp -d); \
	trap 'rm -rf "$$tmp"' EXIT HUP INT TERM; \
	cp help.cmd "$$tmp/help.cmd"; \
	cp help.dat "$$tmp/help.dat"; \
	unix2dos "$$tmp/help.dat"; \
	(cd "$$tmp" && emu2 help.cmd '[C]') && cp "$$tmp/help.hlp" $@
	@test -s $@

# BBB and MMM for gencmd's data[bBBB,mMMM,xfff], derived from help.mp2:
#   BBB = start of dats segment / 16 (e.g. 1000)
#   MMM = (start of memory segment - start of dats segment) / 16
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
