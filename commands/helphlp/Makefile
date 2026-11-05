# HELPHLP — indexed HELP database. Builds help.hlp from help.dat with the
# native HELP [C] indexer of ../help/help.cmd (run under emu2).

HELPCMD=../help/help.cmd

.PHONY: all check clean
.DELETE_ON_ERROR:

all: help.hlp

check: all
	python3 -B ../../tools/help_style.py help.dat

$(HELPCMD):
	$(MAKE) -C ../help help.cmd

# HELP's native indexer requires CRLF. Convert a temporary copy so the
# repository's text remains editable without rebuilding a malformed index.
# Tabs compact space runs in that copy only; displayed columns are asserted
# identical, preserving space on the 320 KB system disk.
help.hlp: $(HELPCMD) help.dat ../../tools/help_style.py ../../tools/help_tabs.py Makefile
	python3 -B ../../tools/help_style.py help.dat
	@set -e; tmp=$$(mktemp -d); \
	trap 'rm -rf "$$tmp"' EXIT HUP INT TERM; \
	cp $(HELPCMD) "$$tmp/help.cmd"; \
	cp help.dat "$$tmp/help.dat"; \
	python3 ../../tools/help_tabs.py "$$tmp/help.dat"; \
	unix2dos "$$tmp/help.dat"; \
	(cd "$$tmp" && emu2 help.cmd '[C]') && cp "$$tmp/help.hlp" $@
	@test -s $@

clean:
	rm -f help.hlp
