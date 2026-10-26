ASM86=cpm86_asm86
GENCMD=cpm86_gencmd

TOOLS=print.cmd printorg.cmd
REF=../../base/print.cmd

.PHONY: all check clean
.DELETE_ON_ERROR:
all: $(TOOLS)

# Separate CODE/DATA groups; GENCMD retains the original record padding.
%.cmd: %.h86 Makefile
	$(GENCMD) $<
	@cmdinfo $@

%.h86: %.a86 Makefile
	$(ASM86) $<

# Frozen invariant and maintained reconstruction initially match in full.
check: $(TOOLS)
	cmp printorg.cmd $(REF)
	cmp print.cmd $(REF)
	@echo "PASS: both PRINT builds are byte-identical to $(REF)"

clean:
	rm -f *.cmd *.obj *.h86 *.sym *.lst *.prn *.log
