INTEL_PLM86=intel_plm86
INTEL_ASM86=intel_asm86
INTEL_LOC86=intel_loc86
INTEL_LINK86=intel_link86
INTEL_OH86=intel_oh86
GENCMD=cpm86_gencmd

TOOLS=stat.cmd

SNIPPETS=

all: $(TOOLS) $(SNIPPETS)

# Data group minimum, in paragraphs.  Must cover the data segment *and* the FCB
# table, which scom.plm builds in 'memory' past the end of data (fcbmax = 512).
# 352h is DRI's own figure from stat.plm: enough for 512 directory entries.
STATMIN = 352

stat.cmd: stat.h86
	$(GENCMD) $< 'data[b1000 m$(STATMIN) xfff]'
	cmdinfo $@

stat.loc: stat.obj dpb86.obj scd.obj
	$(INTEL_LINK86) scd.obj, $(basename $@).obj, dpb86.obj to $(basename $@).lnk
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
