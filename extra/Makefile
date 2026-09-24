# 1.44 MB Feature for CP/M-86 (Freek Heite), rebuilt from source.
# Replaces the original 144make2.bat.
#
# The sources are 144bldr2.asm / 144boot2.asm / 144pat2.asm / 144prep2.asm: the
# "2" is not a repo naming convention, it's upstream's own version-2 marker,
# and 144BLDR2.CMD is the literal 8.3 filename the boot sector's FCB searches
# for on disk (see 144boot2.asm) - unlike the ccpexp.a86-style renames
# elsewhere in this repo, so the sources keep their original names.
#
# Two variants come out of the same sources. The stock one patches cpm.sys; the
# x one patches cpmexp.sys, whose CCP and BDOS stack switches sit at different
# offsets (see the expkrnl block in 144pat2.asm).
#
# The assembler and linker run under DOS emulation, and the results land on
# CP/M disks, so every name here stays inside 8.3 - hence the x suffix on the
# experimental variants rather than -exp.

MASM = pcdev_masm
LINK = pcdev_link5		# 3.65 has no /tiny, 5.13 does
HDR  = cpmhdr32.bin

STOCK = 144pat2.cmd 144prep2.cmd 144bldr2.cmd
EXP   = 144patx.cmd 144prepx.cmd 144bldrx.cmd

all: $(STOCK) $(EXP)

# 144PREP carries the boot sector and the secondary loader appended to it.
144prep2.cmd: 144prep2.tmp 144boot2.bin 144bldr2.cmd
	cat $^ > $@

144prepx.cmd: 144prep2.tmp 144boot2.bin 144bldrx.cmd
	cat $^ > $@

144pat2.cmd: 144pat2.com $(HDR)
	cat $(HDR) $< > $@

144patx.cmd: 144patx.com $(HDR)
	cat $(HDR) $< > $@

# The secondary loader, as written to disk under the name 144BLDR2.CMD.
144bldr2.cmd: 144bldr2.com $(HDR)
	cat $(HDR) $< > $@

144bldrx.cmd: 144bldrx.com $(HDR)
	cat $(HDR) $< > $@

%.tmp: %.com $(HDR)
	cat $(HDR) $< > $@

# The boot sector is a bare 512-byte image, with no CMD header.
144boot2.bin: 144boot2.com
	cp $< $@

144patx.com: 144pat2.asm
	$(MASM) "/z" "/Dexpkrnl=1" "144pat2.asm,144patx.obj,nul,nul;"
	$(LINK) "/tiny" "144patx.obj,$@;"

144bldrx.com: 144bldr2.asm
	$(MASM) "/z" "/Dexpkrnl=1" "144bldr2.asm,144bldrx.obj,nul,nul;"
	$(LINK) "/tiny" "144bldrx.obj,$@;"

%.com: %.asm
	$(MASM) "/z" "$<,$*.obj,nul,nul;"
	$(LINK) "/tiny" "$*.obj,$@;"

clean:
	rm -f *.obj *.com *.tmp 144boot2.bin $(STOCK) $(EXP)

.PHONY: all clean
