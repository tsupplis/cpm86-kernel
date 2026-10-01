RASM86=pcdev_rasm86
LINK86=pcdev_linkcmd

TOOLS=function.cmd

SNIPPETS=

all: $(TOOLS) $(SNIPPETS)

function.obj: function.a86

# function is an 8080-model CMD: one CODE group holding code, data and stack,
# with the base page at 0-0FFh.  Collapsing the data group keeps it that way.
# LINK86 pads the output past the end of the group, so cut it back to the
# length the header declares (128-byte header + LEN paragraphs).
%.cmd: %.obj
	$(LINK86) $* '[$$sz, cod[ori[0]], dat[ori[0],max[0]]]'
	@python3 -c "f='$@';d=open(f,'rb').read();open(f,'wb').write(d[:128+int.from_bytes(d[1:3],'little')*16])"
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
REF=../../base/function.cmd

check: function.cmd
	cmp $< $(REF)
	@echo "PASS: function.cmd is byte-identical to $(REF)"

clean:
	rm -f *.sys *.loc *.cmd *.obj *.h86 *.sym *.lin *.lst *.prn
	rm -f *.loc *.mp? *.lnk *.log
