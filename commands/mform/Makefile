RASM86=pcdev_rasm86
LINK86=pcdev_linkcmd

# LINK-86 adds the 100h base page to data offsets. Runtime secbuf is at
# 380h and dirbuf at 400h; the largest supported directory ends at 2400h.
# Keep 220h additional paragraphs beyond the assembled group, including
# uninitialized storage, so the new utility retains ample directory space.
MFORM_ADD=220

TOOLS=mform.cmd mformorg.cmd

SNIPPETS=

all: $(TOOLS) $(SNIPPETS)

mform.cmd mformorg.cmd: Makefile

mform.obj: mform.a86

mformorg.obj: mformorg.a86

# The historical binary reserves 240h data paragraphs in total. Its
# assembled group uses 41h, so add 1FFh for the reference build only.
mformorg.cmd: MFORM_ADD=1ff

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

check: mform.cmd mformorg.cmd
	cmp mformorg.cmd $(REF)
	@echo "PASS: mformorg.cmd is byte-identical to $(REF)"


clean:
	rm -f *.sys *.loc *.cmd *.obj *.h86 *.sym *.lin *.lst *.prn ccpmtest.img
	rm -f *.mp? *.lnk *.log
	rm -f *.loc *.mp? *.lnk

