RASM86=pcdev_rasm86
LINK86=pcdev_linkcmd

# Extra data paragraphs the loader must reserve past the CMD image, for the
# sector buffer and the directory image.  0x1ff brings the data group's
# minimum to 0x2400 (9216), the figure in the shipped base/mform.cmd.
MFORM_ADD=1ff

TOOLS=mform.cmd

SNIPPETS=

all: $(TOOLS) $(SNIPPETS)

mform.obj: mform.a86

%.cmd: %.obj
	$(LINK86) $* '[$$sz, nofill, data[additional[$(MFORM_ADD)]]]'
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
REF=../../base/mform.cmd

check: mform.cmd
	cmp $< $(REF)
	@echo "PASS: mform.cmd is byte-identical to $(REF)"


clean:
	rm -f *.sys *.loc *.cmd *.obj *.h86 *.sym *.lin *.lst *.prn ccpmtest.img
	rm -f *.mp? *.lnk *.log
	rm -f *.loc *.mp? *.lnk

