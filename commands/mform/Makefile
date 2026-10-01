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

%.obj: %.a86
	unix2dos $<
	$(RASM86) $< $$ pz sz
	[ -f "$@" ]

# The reconstruction reproduces the shipped binary exactly; keep it that way.
REF=../../base/mform.cmd

check: mform.cmd
	cmp $< $(REF)
	@echo "PASS: mform.cmd is byte-identical to $(REF)"


clean:
	rm -f *.sys *.loc *.cmd *.obj *.h86 *.sym *.lin *.lst *.prn ccpmtest.img
	rm -f *.loc *.mp? *.lnk

