ASM86=cpm86_asm86
GENCMD=cpm86_gencmd
H862BIN=h862bin
BIN2ASM=bin2asm

IMAGES=mbr.bin bootsect.bin loader.bin
INCS=$(IMAGES:.bin=.inc)

TOOLS=hdmaint.cmd hdmtorg.cmd
REF=../../base/hdmaint.cmd

.PHONY: all check clean
.DELETE_ON_ERROR:
all: $(TOOLS)

# Original layout: separate CODE/DATA and an allocation-only 32K EXTRA group.
%.cmd: %.h86 Makefile
	$(GENCMD) $< 'extra[m800]'
	@cmdinfo $@

hdmaint.h86 hdmtorg.h86: %.h86: %.a86 hdboot.inc $(INCS) Makefile
	$(ASM86) $<
	# The absolute BIOS reset label emits a declaration-only H86 record.
	# Remove that record so GENCMD does not invent an empty AUX group.
	# Instruction bytes (including JMPF FFFF:0000) remain unchanged.
	@python3 -c "from pathlib import Path; p=Path('$@'); b=p.read_bytes(); marker=b':02000085FFFF7B\r\n'; assert b.startswith(marker), 'Unexpected absolute-segment declaration'; p.write_bytes(b[len(marker):])"

# Assemble each disk stage at its own original offsets. H862BIN checks that
# CODE and DATA form a contiguous flat image, without holes or overlaps.
%.h86: %.a86 Makefile
	$(ASM86) $<

%.flat.h86: %.h86 bootcheck.py
	python3 bootcheck.py normalize $< $@

%.bin: %.flat.h86
	$(H862BIN) $< $@

%.inc: %.bin Makefile
	$(BIN2ASM) -m -f $@ $<

# The original source is frozen. Only its CMD must match the reference.
check: $(TOOLS) $(IMAGES)
	python3 bootcheck.py compare $(REF)
	cmp hdmtorg.cmd $(REF)
	python3 check_maintained.py
	@echo "PASS: frozen original matches; maintained HDMAINT 1.1N checks passed"

clean:
	rm -f *.cmd *.obj *.h86 *.sym *.lst *.prn *.log $(IMAGES) $(INCS)
