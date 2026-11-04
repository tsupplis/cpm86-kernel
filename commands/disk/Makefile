# DISK — local command build.
# all builds the declared tools; check validates them; clean removes generated files.

CMDINFO=cmdinfo
RASM86=pcdev_rasm86
LINK86=pcdev_linkcmd

TOOLS=dcopy.cmd dcomp.cmd

.PHONY: all check clean
.DELETE_ON_ERROR:
all: $(TOOLS)

dcopy.obj: dcopy.a86 ccpmio.a86 geom.a86 Makefile

dcomp.obj: dcomp.a86 ccpmio.a86 geom.a86 Makefile

# Both utilities use an 8080-model CMD: one CODE group holding code, data and stack,
# with the base page at 0-0FFh.  Collapsing the data group keeps it that way.
# Keep uninitialized DMA storage resident via CMD MIN, without storing its
# zero-filled bytes on disk. Both buffers are last in DATA; assert that the
# omitted tail contains only zeros. Trim LINK86 padding too. The real native
# loaders reserve MIN; the tests also exercise this shorter stored image.
dcopy.cmd: BSSPARAS=2048
dcomp.cmd: BSSPARAS=3072

%.cmd: %.obj Makefile
	$(LINK86) $* '[$$sz, cod[ori[0]], dat[ori[0],max[0]]]'
	@python3 -c "from pathlib import Path; p=Path('$@'); b=bytearray(p.read_bytes()); resident=int.from_bytes(b[1:3],'little'); stored=resident-$(BSSPARAS); assert stored>0 and not any(b[128+stored*16:128+resident*16]), 'Nonzero trailing BSS'; b[1:3]=stored.to_bytes(2,'little'); p.write_bytes(b[:128+stored*16])"
	$(CMDINFO) $@

# RASM-86 exits 0 and still writes an .obj when it reports errors, so neither
# the exit status nor the file's existence can be trusted; check the count.
%.obj: %.a86 Makefile
	unix2dos $<
	rm -f $@
	@$(RASM86) $< $$ pz sz > $*.log 2>&1; cat $*.log
	@grep -qE 'Number of errors: +0\.' $*.log || \
	  { echo "*** $<: assembly errors"; rm -f $@; exit 1; }

check: all
	python3 ../../tools/dsktest.py

clean:
	rm -f *.sys *.loc *.cmd *.obj *.h86 *.sym *.lin *.lst *.prn
	rm -f *.loc *.mp? *.lnk *.log
