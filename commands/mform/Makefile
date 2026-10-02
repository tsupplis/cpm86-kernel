RASM86=pcdev_rasm86
LINK86=pcdev_linkcmd

# Extra data paragraphs the loader must reserve past the CMD image.
# Layout (DS-relative): base page 000h, data origin 100h, last static var
#   ~1F0h (dmaoff), secbuf at 280h (128 bytes), dirbuf at 400h growing up.
# CMD image ends at ~1F0h (nofill).  additional[NNN] appends NNN*16 bytes
# past that end.  We must reach 2400h (400h + worst-case dir 2000h):
#   2400h - 1F0h = 210h paragraphs minimum.  Use 220h for a small margin.
MFORM_ADD=220

TOOLS=mform.cmd mformorg.cmd

SNIPPETS=

all: $(TOOLS) $(SNIPPETS)

mform.obj: mform.a86

mformorg.obj: mformorg.a86

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

check: mformorg.cmd
	cmp $< $(REF)
	@echo "PASS: mform.cmd is byte-identical to $(REF)"


clean:
	rm -f *.sys *.loc *.cmd *.obj *.h86 *.sym *.lin *.lst *.prn ccpmtest.img
	rm -f *.mp? *.lnk *.log
	rm -f *.loc *.mp? *.lnk

