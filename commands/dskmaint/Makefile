RASM86=pcdev_rasm86
LINK86=pcdev_linkcmd
ASM86=cpm86_asm86
H862BIN=h862bin
BIN2ASM=bin2asm

TOOLS=dskmaint.cmd dskmorg.cmd dform.cmd

# The two images DSKMAINT writes to track 0, as flat binaries.
IMAGES=bootsect.bin loader.bin

# The same images as include files; DSKMAINT carries them in its data.
INCS=bootsect.inc loader.inc

SNIPPETS=$(IMAGES)

all: $(TOOLS) $(SNIPPETS)

dskmaint.obj: dskmaint.a86 $(INCS)

dskmorg.obj: dskmorg.a86 $(INCS)

dform.obj: dform.a86 ccpmio.a86 $(INCS)

# bootsect and loader are assembled by themselves (ASM-86, not RASM-86):
# BOOTSECT runs at 0000:7c00 and LOADER at offset 100h of the segment it is
# loaded into. h862bin extracts each binary image; bin2asm emits the data
# declarations included by DSKMAINT and DFORM.
bootsect.h86: bootsect.a86
loader.h86: loader.a86

%.h86: %.a86
	unix2dos $<
	rm -f $@
	$(ASM86) $*
	@test -f $@ || { echo "*** $<: assembly errors"; exit 1; }

%.bin: %.h86
	$(H862BIN) $< $@

%.inc: %.bin Makefile
	$(BIN2ASM) -m -f $@ $<
	unix2dos $@

# dskmaint is an 8080-model CMD: one CODE group holding code, data and stack,
# with the base page at 0-0FFh.  Collapsing the data group keeps it that way.
%.cmd: %.obj
	$(LINK86) $* '[$$sz, cod[ori[0]], dat[ori[0],max[0]]]'
	cmdinfo $@

# LINKCMD may retain trailing unused DATA bytes after collapsing the group.
# Keep only the declared CODE payload, as in the dual-OS CCP/M build.
dform.cmd: dform.obj Makefile
	$(LINK86) dform '[$$sz,cod[ori[0]],dat[ori[0],max[0]]]'
	@python3 -c "p='$@';b=open(p,'rb').read();open(p,'wb').write(b[:128+int.from_bytes(b[1:3],'little')*16])"
	cmdinfo $@

# RASM-86 exits 0 and still writes an .obj when it reports errors, so neither
# the exit status nor the file's existence can be trusted; check the count.
%.obj: %.a86
	unix2dos $<
	rm -f $@
	@$(RASM86) $< $$ pz sz > $*.log 2>&1; cat $*.log
	@grep -qE 'Number of errors: +0\.' $*.log || \
	  { echo "*** $<: assembly errors"; rm -f $@; exit 1; }

# The reconstruction reproduces the shipped binary exactly; keep it that way.
REF=../../base/dskmaint.cmd

check: dskmorg.cmd check-dform
	cmp $< $(REF)
	@echo "PASS: dskmaint.cmd is byte-identical to $(REF)"


clean:
	rm -f *.sys *.loc *.cmd *.obj *.h86 *.sym *.lin *.lst *.prn
	rm -f *.loc *.mp? *.lnk *.log $(IMAGES) $(INCS)

check-dform: dform.cmd $(IMAGES)
	python3 ../../tools/dfmtest.py

.PHONY: all check check-dform clean
