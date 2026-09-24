INTEL_PLM86=intel_plm86
INTEL_ASM86=intel_asm86
INTEL_LOC86=intel_loc86
INTEL_LINK86=intel_link86
INTEL_OH86=intel_oh86
ASM86=cpm86_asm86
GENCMD=cpm86_gencmd
RASM86=pcdev_rasm86
LINK86=pcdev_linkcmd
LIB86=pcdev_lib86

TOOLS=asm86.cmd

all: $(TOOLS)

# BBB and MMM for gencmd's data[bBBB,mMMM,xfff], derived from asm86.mp2:
#   BBB = start of const segment / 16
#   MMM = (start of memory segment - start of const segment) / 16 + symbol table
# Both segments are paragraph-aligned, so /16 is just dropping the last hex
# digit.  DRI's note gave 100h (4K) of symbol table; this build has long used
# 490h (~18K) instead - keep it, 4K is very tight for a macro assembler.
# Recursively expanded on purpose: asm86.mp2 only exists once asm86.h86 is built.
ASM86_SYMTAB = 490
PARA = sub(/H$$/,"",s); sub(/.$$/,"",s); sub(/^0+/,"",s); print tolower(s); exit
ASM86_BASE = $(shell awk '/CONST +CONST/{s=$$1; $(PARA)}' asm86.mp2)
ASM86_MEM  = $(shell awk '/MEMORY +MEMORY/{s=$$1; $(PARA)}' asm86.mp2)
ASM86_MIN  = $(shell printf '%x' $$((0x$(ASM86_MEM)-0x$(ASM86_BASE)+0x$(ASM86_SYMTAB))))

asm86.cmd: asm86.h86
	@test -n "$(ASM86_BASE)" -a -n "$(ASM86_MEM)" || \
	  { echo "asm86: cannot derive CONST/MEMORY from asm86.mp2"; exit 1; }
	$(GENCMD) $< 'data[b$(ASM86_BASE), m$(ASM86_MIN), xfff]'
	cmdinfo $@

asm86.h86: c86lnk.obj mainp.obj f21.mod f22.mod
	$(INTEL_LINK86) c86lnk.obj,mainp.obj,f21.mod,f22.mod to asm86.mod
	$(INTEL_LOC86) asm86.mod nopublics 'ad(sm(code(0))) od(sm(code,const,stack))' to asm86.loc
	$(INTEL_OH86) asm86.loc to asm86.hex
	mv asm86.hex asm86.h86

asm86.mod: c86lnk.obj mainp.obj f21.mod f22.mod
	$(INTEL_LINK86) c86lnk.obj,mainp.obj,f21.mod,f22.mod to $@

f21.mod: f11.mod f12.mod f13.mod
	$(INTEL_LINK86) f11.mod,f12.mod,f13.mod to $@

f22.mod: f14.mod f15.mod f16.mod
	$(INTEL_LINK86) f14.mod,f15.mod,f16.mod to $@

f11.mod: cmac1.obj cmac2.obj cmac3.obj cmac4.obj cmac5.obj
	$(INTEL_LINK86) cmac1.obj, cmac2.obj, cmac3.obj, cmac4.obj, cmac5.obj to $@

f12.mod: mnem1.obj mnem2.obj mnem3.obj mnem4.obj symb.obj
	$(INTEL_LINK86) mnem1.obj,mnem2.obj,mnem3.obj,mnem4.obj,symb.obj to $@

f13.mod: io.obj subr1.obj subr2.obj files.obj scan.obj
	$(INTEL_LINK86) io.obj,subr1.obj,subr2.obj,files.obj,scan.obj to $@

f14.mod: print.obj predef.obj ermod.obj text.obj outp.obj
	$(INTEL_LINK86) print.obj,predef.obj,ermod.obj,text.obj,outp.obj to $@

f15.mod: expr.obj brexpr.obj pseud1.obj pseud2.obj cmsubr.obj
	$(INTEL_LINK86) expr.obj,brexpr.obj,pseud1.obj,pseud2.obj,cmsubr.obj to $@

f16.mod: instr.obj dline.obj global.obj cm.obj cm2.obj
	$(INTEL_LINK86) instr.obj,dline.obj,global.obj,cm.obj,cm2.obj to $@

%.obj: %.a86
	$(INTEL_ASM86) $^

%.obj: %.plm
	$(INTEL_PLM86) $^ debug 'optimize(2)' xref

clean:
	rm -f *.sys *.cmd *.obj *.sym *.lin *.lst *.mod *.mp1 *.mp2 *.loc


