CC=aztec42_cc
LD=aztec42_link
CFLAGS=-I. +0 -D__CPM__
CPM_LDFLAGS=-lc86

all: binaries

OBJS=hexcom.o

binaries: hexcom.cmd

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

hexcom.cmd: $(OBJS)
	$(LD) -o $@ $(OBJS) $(CPM_LDFLAGS)

clean:
	rm -rf *.o *.cmd
