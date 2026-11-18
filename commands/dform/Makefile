# DFORM — local command build, using DSKMAINT's maintained boot images.
RASM86=pcdev_rasm86
LINK86=pcdev_linkcmd
CMDINFO=cmdinfo
BIN2ASM=bin2asm

TOOLS=dform.cmd
INCS=bootsect.inc loader.inc

.PHONY: all check clean
.DELETE_ON_ERROR:
all: $(TOOLS)

dform.obj: dform.a86 ccpmio.a86 $(INCS) Makefile

# DSKMAINT owns boot image generation. DFORM keeps only generated includes.
../dskmaint/bootsect.bin: ../dskmaint/bootsect.a86 ../dskmaint/Makefile
	$(MAKE) -C ../dskmaint bootsect.bin

../dskmaint/loader.bin: ../dskmaint/loader.a86 ../dskmaint/Makefile
	$(MAKE) -C ../dskmaint loader.bin

%.inc: ../dskmaint/%.bin Makefile
	$(BIN2ASM) -m -f $@ $<
	unix2dos $@

# LINKCMD may retain trailing unused DATA bytes after collapsing the group.
# Keep only the declared CODE payload, as in the dual-OS CCP/M build.
dform.cmd: dform.obj Makefile
	$(LINK86) dform '[$$sz,cod[ori[0]],dat[ori[0],max[0]]]'
	@python3 -c "p='$@';b=open(p,'rb').read();open(p,'wb').write(b[:128+int.from_bytes(b[1:3],'little')*16])"
	$(CMDINFO) $@

# RASM-86 can return success after reporting errors; check its error count.
%.obj: %.a86
	unix2dos $<
	rm -f $@
	@$(RASM86) $< $$ pz sz > $*.log 2>&1; cat $*.log
	@grep -qE 'Number of errors: +0\.' $*.log || \
	  { echo "*** $<: assembly errors"; rm -f $@; exit 1; }

check: all
	python3 -B tests/check.py

clean:
	rm -f *.cmd *.obj *.sym *.lst *.prn *.log *.mp? *.loc *.lnk $(INCS)
