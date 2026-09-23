RASM86=pcdev_rasm86
LINK86=pcdev_linkcmd

TOOLS=tod.cmd

SNIPPETS=

all: $(TOOLS) $(SNIPPETS)

tod.obj: tod.a86 baselib.a86 tinylib.a86

%.cmd: %.obj
	$(LINK86) $* '[$$sz]'
	cmdinfo $@

%.obj: %.a86
	$(RASM86) $< $$ pz sz
	[ -f "$@" ]


clean:
	rm -f *.sys *.loc *.cmd *.obj *.h86 *.sym *.lin *.lst *.prn ccpmtest.img
	rm -f *.loc *.mp? *.lnk

