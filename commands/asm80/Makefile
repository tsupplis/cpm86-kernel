# ASM80 — local command build.
# all builds the declared tools; check validates them; clean removes generated files.

CMDINFO=cmdinfo
TOOLS=asm80.cmd

ASM86=cpm86_asm86
GENCMD=cpm86_gencmd

.PHONY: all check clean
.DELETE_ON_ERROR:
all: $(TOOLS)

asm80.cmd: asm80.h86 Makefile
	$(GENCMD) $< 8080 'code[xfff]'

%.h86: %.a86 Makefile
	$(ASM86) $<
	[ -f $@ ]

clean:
	$(RM) *.prn *.lst *.h86 *.cmd

# Structural validation; byte comparisons or runtime checks are separate where available.
check: all
	@set -e; for file in $(TOOLS); do $(CMDINFO) $$file; done
