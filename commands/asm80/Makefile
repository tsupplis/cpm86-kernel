ASM86=cpm86_asm86
GENCMD=cpm86_gencmd

all: asm80.cmd

asm80.cmd: asm80.h86
	$(GENCMD) $< 8080 'code[xfff]'

%.h86: %.a86
	$(ASM86) $<
	[ -f $@ ]

clean:
	$(RM) *.prn *.lst *.h86 *.cmd
