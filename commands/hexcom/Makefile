# HEXCOM — local command build.
# all builds the declared tools; check validates them; clean removes generated files.

CMDINFO=cmdinfo
TOOLS=hexcom.cmd

CC=aztec42_cc
LD=aztec42_link
CFLAGS=-I. +0 -D__CPM__
CPM_LDFLAGS=-lc86

.PHONY: all check clean
.DELETE_ON_ERROR:
all: binaries

OBJS=hexcom.o

binaries: hexcom.cmd

%.o: %.c Makefile
	$(CC) $(CFLAGS) -c -o $@ $<

hexcom.cmd: $(OBJS) Makefile
	$(LD) -o $@ $(OBJS) $(CPM_LDFLAGS)

clean:
	rm -rf *.o *.cmd

# Structural validation; byte comparisons or runtime checks are separate where available.
check: all
	@set -e; for file in $(TOOLS); do $(CMDINFO) $$file; done
