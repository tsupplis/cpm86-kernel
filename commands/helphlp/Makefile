# HELPHLP — indexed HELP database. Builds help.hlp from help.dat with the
# native HELP [C] indexer of ../help/help.cmd (run under emu2).

HELPCMD=../help/help.cmd

.PHONY: all check clean
.DELETE_ON_ERROR:

all: help.hlp

check: all

$(HELPCMD):
	$(MAKE) -C ../help help.cmd

# HELP's native indexer requires CRLF. Convert a temporary copy so the
# repository's LF text remains editable without rebuilding a malformed index.
help.hlp: $(HELPCMD) help.dat Makefile
	@set -e; tmp=$$(mktemp -d); \
	trap 'rm -rf "$$tmp"' EXIT HUP INT TERM; \
	cp $(HELPCMD) "$$tmp/help.cmd"; \
	cp help.dat "$$tmp/help.dat"; \
	unix2dos "$$tmp/help.dat"; \
	(cd "$$tmp" && emu2 help.cmd '[C]') && cp "$$tmp/help.hlp" $@
	@test -s $@

clean:
	rm -f help.hlp
