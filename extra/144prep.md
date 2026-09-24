# The 1.44 MB Feature for CP/M-86

This software makes "CP/M-86 for the IBM PC and IBM PC XT  Version 1.1"
support diskettes with much higher capacities than the old, standard CP/M-86
160 KB and 320 KB formats. Now, you can store:

- up to 710 KB of data on a 3.5 inch, 720 KB diskette
- up to 1.18 MB of data on a 5.25 inch, 1.2 MB diskette
- up to 1.42 MB of data on a 3.5 inch, 1.44 MB diskette.


## Program 144PREP

This program will prepare a standard, already formatted, 720 KB or 1.2 MB
or 1.44 MB diskette for use with "CP/M-86 for the IBM PC and IBM PC XT 
Version 1.1".

The word "prepare" is used here instead of "format", as the 144PREP program
does not perform a true "low level format". 

To actually USE the full 720 KB or 1.44 MB or 1.2 MB capacity under CP/M-86,
you also need the other program of the "1.44 MB Feature", called 144PAT2.CMD.


## Running 144PREP

Syntax:

```
	144PREP drive <options>

drive

	is the diskette drive you want to use; it can be either A: or B:


<options>

	are used to specify the diskette type and the preparation type.
        Options are not case sensitive; they can be given in any order.

        Do NOT put any blanks between options. If you do, some options will
        be ignored.
```


## 144PREP command line options

	1

	specifies a 1.2 MB, 5.25 inch diskette. If you do not specify this
        option, 144PREP will prepare a 1.44 MB, 3.5 inch  diskette.

	3

	specifies that the 1.2 MB format you have asked with option 1, should
        be prepared on 1.44 MB, 3.5 inch media instead of the usual 5.25 inch
        media.
        This option is only effective in combination with option 1, if you want
        to test 1.2 MB support on a PC without a real 5.25 inch high capacity
        diskette drive.

	7

	specifies a 720 KB, 3.5 inch diskette. If you do not specify this
        option, 144PREP will prepare a 1.44 MB, 3.5 inch diskette.

	Q

	specifies a "quick prepare" where only the first four tracks of
        the diskette (i.e. the boot area, the directory and a small part of
        the data area) are re-initialized.
        If you do not specify this option, all tracks on the diskette will be
        re-initialized.

	V

	is an abbreviation for "verbose". 144PREP will display some
        additional, diagnostic messages.


If you specify both options 1 and 7, only the one that comes first on the
command line, will be honoured. The other(s) will be ignored.


## 144PREP command line examples


```
144PREP A:

	will prepare the 1.44 B diskette in drive A: as a 1.44 MB CP/M-86
	diskette for use with the "1.44 MB Feature".


144PREP B: Q7

	will perform a "quick prepare" for the 720 KB diskette in drive B:.
        Note that there must be NO blanks between the option characters.

144PREP A: 13V

	will prepare the 1.2 MB format on 1.44 MB, 3.5 inch media in drive A:.
        The program will display some additional information that might be
        useful for problem determination.
```


## Usage notes about 144PREP

1. Program 144PREP.CMD requires that the 1.44 MB Feature is already active.
   Activate this either by running the companion program 144PAT2.CMD, or by
   booting CP/M-86 from a diskette that you prepared before with 144PREP.CMD
   and have made bootable by copying CPM.SYS to it.

2. The CP/M-86 program 144PREP.CMD needs to reset all disk drives. This
   causes CP/M-86 to log-in your boot drive. So there must be a formatted
   diskette in your boot drive, if you started CP/M-86 from a diskette.

3. The diskette must already have been formatted, as a 720 KB, 1.2 MB or 1.44
   MB diskette, with any standard DOS, Windows or OS/2 FORMAT program, or it 
   must have been pre-formatted by the diskette's manufacturer.

   Technically: 144PREP does NOT perform a low-level format of the
   diskette, it just writes some data that CP/M-86 is expecting to find on a 
   diskette (i.e. information to recognize the diskette as a valid 720
   KB, 1.2 MB or 1.44 MB diskette). The remainder of the diskette is filled
   with the CP/M-standard hexadecimal byte value E5.

4. You can only succesfully prepare and use the diskette type(s) that are
   valid for your hardware.

   Not all 5.25 inch drives support 1.2 MB media; not all 3.5 inch drives
   support 1.44 MB media.

   For 1.2 MB you need "double sided, high density" 5.25 inch diskettes;
   for 1.44 MB you need "double sided, high density" 3.5 inch diskettes;

5. Do not forget to press a control-C at the CP/M-86 command prompt, every time
   you have changed diskettes!

   CP/M-86 can, by itself, detect a diskette change and it will put the new
   diskette in read-only status. But it will only re-calculate the free space
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

6. Standard CP/M-86, without the "1.44 MB feature" loaded, will "see" all
   diskette types prepared by 144PREP as a 160 KB single-sided
   diskette with all diskette space used by a file called CP/M-86.720 c.q.
   CP/M-86.120 c.q. CP/M-86.144. 
   This will prevent a non-patched, standard CP/M-86 system from accidently
   overwriting data on the new higher capacity diskette types.

7. The CP/M-86 program 144PREP.CMD disables the control-break key combination
   while it is preparing a diskette.

8. DOS will "see" all diskette types prepared by 144PREP as DOS 160 KB
   diskettes with no free space available, and all clusters marked as "bad".
   This will prevent DOS from accidently overwriting your CP/M-86 data on the
   diskette.

   The DOS volume label is CPM-86-DISK.

   It has been reported that DOS 3.2 will not properly show this volume label
   on 720 KB diskettes; instead, it displays the first 11 bytes of the FAT.


## Last but not least

Thanks to Tim Olmstedt, John Elliott, Barry Watzman.
The test team: Kirk Lawrence, Steve Dubrovich, Stephen Hunt.

Questions? Remarks? Bugs? Share them in the newsgroup comp.os.cpm on the 
internet.

You may use, misuse and abuse this software any way you want - but at your own
risk. The author of the software does not accept any responsibility for the
consequences of such use, misuse or abuse.


- Version: 2.0
- Date   : 16Oct2000
- Author : Freek Heite
- Email  : fheite@knoware.nl
