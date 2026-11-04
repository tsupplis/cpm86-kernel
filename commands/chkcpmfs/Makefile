# CHKCPMFS — read-only CP/M filesystem consistency check.

CMDINFO=cmdinfo
INTEL_PLM86=intel_plm86
INTEL_ASM86=intel_asm86
INTEL_LOC86=intel_loc86
INTEL_LINK86=intel_link86
INTEL_OH86=intel_oh86
GENCMD=cpm86_gencmd

TOOLS=chkcpmfs.cmd

.PHONY: all check check-bdos check-live clean
.DELETE_ON_ERROR:

all: $(TOOLS)

PARA = sub(/H$$/,"",s); sub(/.$$/,"",s); sub(/^0+/,"",s); print tolower(s); exit
GENCMD_BASE = $(shell awk '/DATS +DATA/{s=$$1; $(PARA)}' chkcpmfs.mp2)
GENCMD_MEM  = $(shell awk '/MEMORY +MEMORY/{s=$$1; $(PARA)}' chkcpmfs.mp2)
GENCMD_MIN  = $(shell printf '%x' $$((0x$(GENCMD_MEM)-0x$(GENCMD_BASE))))

chkcpmfs.cmd: chkcpmfs.h86 Makefile
	@test -n "$(GENCMD_BASE)" -a -n "$(GENCMD_MEM)" || \
	  { echo "chkcpmfs: cannot derive DATS/MEMORY from chkcpmfs.mp2"; exit 1; }
	$(GENCMD) $< 'data[b$(GENCMD_BASE) m$(GENCMD_MIN) xfff]'
	$(CMDINFO) $@

chkcpmfs.loc: chkcpmfs.obj scd.obj Makefile
	$(INTEL_LINK86) scd.obj, chkcpmfs.obj to chkcpmfs.lnk
	$(INTEL_LOC86) chkcpmfs.lnk 'od(sm(code,dats,data,stack,const))' \
		'ad(sm(code(0),dats(10000h)))' 'ss(stack(+128))' to chkcpmfs.loc

%.h86: %.loc Makefile
	$(INTEL_OH86) $<
	mv $*.hex $*.h86

%.obj: %.a86 Makefile
	$(INTEL_ASM86) $<

%.obj: %.plm Makefile
	$(INTEL_PLM86) $< debug 'optimize(3)' xref

clean:
	rm -f *.sys *.loc *.cmd *.obj *.h86 *.sym *.lin *.lst *.prn
	rm -f *.mp? *.lnk

check: all check-bdos
	python3 tests/parameters.py
	@set -e; for file in $(TOOLS); do $(CMDINFO) $$file; done

check-bdos: all
	python3 tests/check.py

check-live: all
	$(MAKE) -C ../.. chkcpmfs-live-images
	python3 tests/live.py
