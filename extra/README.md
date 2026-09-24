The 1.44 MB Feature for CP/M-86 version 2
=========================================

Contents:

1. Introduction
2. What's new in this version
3. Quick start
4. Note about SETUP and "FIDD" storage
5. Stack bonus
6. You cannot...
7. Bugs fixed
8. Last but not least


1. Introduction
===============

This software makes "CP/M-86 for the IBM PC and IBM PC XT  Version 1.1"
support diskettes with much higher capacities than the old, standard CP/M-86
160 KB and 320 KB formats. Now, you can store:

- up to 710 KB of data on a 3.5 inch, 720 KB diskette
- up to 1.18 MB of data on a 5.25 inch, 1.2 MB diskette
- up to 1.42 MB of data on a 3.5 inch, 1.44 MB diskette.

Up to 4 diskette drives are supported.

The 1.44 MB Feature package consists of 2 programs:

1. program 144PAT2.CMD is the "driver", it adds some code to an 
   already-running CP/M-86 system so CP/M-86 can read from and write to
   720 KB, 1.44 MB and 1.2 MB diskettes.

2. program 144PREP2.CMD will prepare (format) a diskette (720 KB, 1.44 MB or
   1.2 MB type) for use with CP/M-86. When you have prepared a diskette, you
   might want to copy CPM.SYS to it, so you can boot CP/M-86 from such a higher
   capacity diskette.

The documentation:

- 144PAT2.DOC describes the driver program 144PAT2.CMD
- 144PREP2.DOC describes the prepare (format) program 144PREP2.CMD
- 144TECH2.DOC gives some technical background information.

The source code and related files:

- 144PAT2.ASM, source code for program 144PAT2.CMD
- 144PREP2.ASM, source code for program 144PREP2.CMD
- 144BOOT2.ASM, boot sector program for higher capacity diskettes
- 144BLDR2.ASM, secondary boot loader program for higher capacity diskettes
- 144MAKE2.BAT, sample batch file to build all binaries
- CPMHDR32.BIN, binary CP/M-86 CMD header file.

Thanks to Tim Olmstedt, John Elliott, Barry Watzman.
The test team: Kirk Lawrence, Steve Dubrovich, Stephen Hunt.


2. What's new in this version
=============================

New features, added in version 2:

- support for 1.2 MB HD diskettes (80 tracks, 15 sectors per track)

- CP/M-86 can be booted from 720 KB, 1.2 MB and 1.44 MB diskettes

- memory requirement for the "device driver" reduced from 12 KB to 9 KB

- CP/M-86 version of the program to "prepare" diskettes

- support for reading from and writing to the 720 KB (netto 702 KB) 3.5 inch
  diskette format as used by "Personal CP/M-86 version 2.0/4" a.k.a. "CP/M-86
  Plus". This CP/M-86 version is said to have been shipped with Siemens
  PG685/695 machines, but seems to run well on a "standard" PC. 
  Do NOT use the "Personal CP/M-86 Plus" utility INITDIR to put date and time
  stamps and passwords on the diskette, if you want to write to such a diskette
  from standard CP/M-86 1.1 - as standard CP/M-86 1.1 might overwrite them.


3. Quick start
==============

This assumes your 720 KB, 1.44 MB or 1.2 MB diskette drive is A: 

Step 1
------

Boot CP/M-86 version 1.1 just like you always do.

Step 2
------

Run the standard CP/M-86-supplied utility 

	SETUP

and follow the instructions on the screen to reserve at least nine (09)
kilobytes of memory for "Field Installable Device Drivers". Be sure to save
your changes to your boot harddisk or boot diskette.

Step 3
------

Reboot CP/M-86 version 1.1 just like you always do, to activate the changes
you have made in step 3 to your boot disk with the SETUP program.

Now load the driver for 720 KB, 1.44 MB and 1.2 MB diskettes with the command

	144PAT2

If the program gives no error messages, CP/M-86 is now able to use 720 KB,
1.44 MB and 1.2 MB diskettes, in addition to the standard 160 KB and 320 KB
diskette formats.

Step 4
------

Your CP/M-86 system now supports up to 1.44 MB per diskette. So it's time
to prepare one or more higher capacity diskettes for use with CP/M-86.

Find yourself a 720 KB, 1.2 MB or 1.44 MB diskette that has been formatted
before by yourself or is pre-formatted by the diskette manufacturer (if you
only have really blank, unformatted out-of-the-box diskettes, you will need a
DOS, Windows or OS/2 program to format the diskettes once at its appropriate
capacity).

In case of 1.44 MB diskettes, run the command

	144PREP A:

In case of 720 KB diskettes, run the command

	144PREP A: 7

In case of 1.2 MB KB diskettes, run the command

	144PREP A: 1

In all cases, follow the instructions on the screen and insert the higher
capacity diskette when 144PREP2 prompts you to do so.

If you do not want the diskette to be bootable, you can remove the file
144BLDR2.CMD that you'll see in the directory of a prepared diskette.

But you want to make these diskettes bootable (now or at a later moment),
leave the 144BLDR2.CMD file as it is, and copy your CPM.SYS file to them with
the standard CP/M-86 utility PIP. This CPM.SYS can be anywhere on the
diskette and anywhere in the directory, as long as it is present under user
number 0. If you want, you can give CPM.SYS the read-only and/or system
attributes.

When you boot CP/M-86 from a higher capacity diskette, the boot code will add
the support for 720 KB, 1.2 MB and 1.44 MB diskettes to CP/M-86, so you don't
need to run the separate driver program 144PAT2.CMD again.

Step 5
------

Enjoy the higher diskette capacities of CP/M-86. But please read these caveats:

Do not forget to press a control-C at the CP/M-86 command prompt, EVERY time
you have changed diskettes!

CP/M-86 can, by itself, detect a diskette change and it will put the new
diskette in read-only status. But: it will only re-calculate the free space
and recognize the format of the new diskette if you press a control-C. If
you don't, CP/M-86 will blindly assume that the new diskette has exactly
the same format as the previous diskette in the drive.

Pressing control-C after a diskette change is a standard, documented
CP/M-86 requirement. To prevent CP/M-86 from crashing, strictly follow this
requirement - especially when you change from one diskette format to 
another.

If a DIR command shows multiple entries with the same names, or if you get
the message "MEMORY NOT AVAILABLE" after you typed the name of an external
command: then you probably have forgotten to press control-C after you
changed a diskette.


4. Note about SETUP and "FIDD" storage
======================================

If you are using the command-line driver 144PAT2.CMD of the 1.44 MB
Feature, be aware that this driver needs 9 KB of so-called "FIDD" storage.
So before using 144PAT2.CMD, you must allocate this FIDD storage, with the
standard CP/M-86 supplied program SETUP (see 144PAT2.DOC for details).

If, however, you are using the 1.44 MB Feature by booting CP/M-86 from a
diskette prepared with 144PREP2.CMD, this FIDD storage is not an issue. The
boot loader program will automatically handle this for you.

A general remark about using SETUP in combination with higher capacity
boot diskettes:

You are advised to put your higher capacity boot diskette in a drive, and
log it in, before you start the SETUP program. In a system with only a
single diskette drive you should run SETUP from the higher capacity boot
diskette.  This will ensure that CP/M-86 will use the correct way to save
your SETUP definitions to the diskette - whether you are changing
FIDD-allocation or other definitions like power-on command line, memory
disk etc.


5. Stack bonus
==============

Besides adding 720 KB, 1.44 MB and 1.2 MB diskette support to CP/M-86, the
program 144MB Featue enlarges the local CP/M-86 stacks for the CCP, the BDOS
and for the control-break handler in CP/M's BIOS to 256 bytes each.

Originally, these stacks are somewhere between 90 and 128 bytes. For some
modern Pentium systems, these stacks are way too small. Enlarging them
solved some problems I had when running CP/M-86 on a Toshiba Pentium 133
system, like:

- screen saver program changing the current user number
- read and write errors on track 768 (!) on 160 KB and 320 KB diskettes
- scrambled error messages when trying to rename a file at the command prompt.

If you boot CP/M-86 from a higher capacity diskette, the stack space for the
cold start routines in CPM.SYS is increased from 128 bytes to 1 KB. This
enabled me to boot CP/M-86 on a 1999 model Dell Pentium XPST 500 MHz system
with Phoenix ROM-BIOS, where the ROM-BIOS is using ca. 180 bytes of stack
space when accessing the harddisk through interrupt 13h. I think this is an
excessive amount - but now it's no longer a problem.


6. You cannot...
================

- ... use the standard CP/M-86 supplied command DSKMAINT to make copies
  of 720 KB, 1.2 MB and 1.44 MB diskettes. This DSKMAINT only "knows" 160 KB
  and 320 KB diskettes and will treat any other format as 160 KB diskettes.

- ... use the standard CP/M-86 supplied command SETUP to change the stepping
  rate for 720 KB, 1.2 MB and 1.44 MB diskettes. The driver for the 1.44 MB
  Festure uses its own, fixed values for accessing these larger capacity 
  diskettes.


7. Bugs fixed
=============

Bugs found in version 1 and fixed in version 2:

- "quick preparing" a 720 KB diskette only erases the first 144 entries of the
  CP/M-86 directory, the other 112 entries are left unchanged.

- the RC and AL fields in the last directory extent for the filler file in the
  "dummy" 160 KB CP/M directory are incorrect: RC is 41h, it should be 50h;
  the 10th byte of AL is 0, it should be 9Bh.

- the directory entries for the filler file in the "dummy" 160 KB directory
  have the most significant bit of the third byte of the file type set to 1.
  However, this "archive bit" is reserved but not actually used by CP/M-86
  version 1.1 so this bit should be 0.

- when a patch to the in-memory image of CPM.SYS fails because unexpected
  data is found, the value of that unexpected data is not correctly displayed.


8. Last but not least
=====================

Thanks to Tim Olmstedt and John Elliott.
The test team: Kirk Lawrence, Steve Dubrovich, Stephen Hunt.

Questions? Remarks? Bugs? Share them in the newsgroup comp.os.cpm on the 
internet.

You may use, misuse and abuse this software any way you want - but at your own
risk. The author of the software does not accept any responsibility for the
consequences of such use, misuse or abuse.


Version: 2.0
Date   : 16Oct2000
Author : Freek Heite
Email  : fheite@knoware.nl
