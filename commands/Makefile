SUBDIRS=tod asm86 ddt86 submit pip ed gencmd help submit stat

all clean:
	for d in $(SUBDIRS); do \
		$(MAKE) -C $$d $@; \
	done

.PHONY: all clean dist $(SUBDIRS)
