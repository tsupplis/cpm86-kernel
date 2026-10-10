SUBDIRS=tod asm86 asm80 ddt86 submit pip ed gencmd help submit stat \
    mform assign function dskmaint hexcom

all clean:
	for d in $(SUBDIRS); do \
		$(MAKE) -C $$d $@; \
	done

.PHONY: all clean dist $(SUBDIRS)
