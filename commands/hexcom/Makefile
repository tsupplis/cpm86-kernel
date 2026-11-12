# HEXCOM — local command build.
# all builds the declared tools; check validates them; clean removes generated files.

CMDINFO=cmdinfo
TOOLS=hexcom.cmd

CC=aztec43_acc
LD=aztec43_acc
CFLAGS=-squeeze -Osize -I. -D__CPM__

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
