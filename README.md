# CP/M-86 Kernel

## Synopsis

The goal of this project is to provide an out-of-the-box CP/M-86 1.1 kernel (BIOS, BDOS and CCP) that incorporates all existing patches plus the capacity to run on modern hardware and virtualization. A distribution of the CP/M-86 OS is also provided fully patched.

The distribution also packages digital research assembler tools and various basic environments.

- visual y2k support and tod replacement (https://github.com/tsupplis/cpm86-hacking)
- AT support
- resilience to bios limits for video display

This is a raw dump right now with a way to compile the kernel starting from dissassembled sources.
The compilation requires the (cross-development environment for CP/M-86)[https://github.com/tsupplis/cpm86-crossdev]

The CP/M-86 kernels (8088 and V20 Mixed 8080/8088 with CP/M-80 compatibility) for the V20 MBC are also produced. The sources of the bioses used are available at:
- https://hackaday.io/project/170924-v20-mbc-a-v20-8088-8080-cpu-homebrew-computer

The 3 kernels use the same BDOS and CCP components.

## Playing with CP/M-86

To test, the PCE emulator and cpmtools are needed. PCE can be found at http://www.hampa.ch/pce/. the floppy images released also work with qemu.

Alternatively, you can use the excellent V20 MBC available at:
- https://hackaday.io/project/170924-v20-mbc-a-v20-8088-8080-cpu-homebrew-computer
- https://shop.mcjohn.it/en/diy-kit

- Patched CP/M-86 running in the PCE Emulator
<p align="center">
<img src="./images/cpm86.png" width="75%">
</p>

- CP/M-86 BIOS Setup 1.2
<p align="center">
<img src="./images/setup.png" width="75%">
</p>

- CP/M-86 Disk Maintenance 1.2
<p align="center">
<img src="./images/dskmaint.png" width="75%">
</p>

## Distribution

A full 160K single phase distribution is provided on 4 disks. The compiled cpm.sys file is also provided standalone.

- cpm86-1.img: bootable core CP/M-86
- cpm86-at-1.img: bootable core CP/M-86 with AT-compatible clock
- cpm86-2.img: assembler CP/M-86 tools
- cpm86-3.img: digital research dev tools
- cpm86-4.img: basic development (microsoft basic, personal basic, cbasic)

The CP/M-86 OS contains the following commands are in the original distribution:
- asm86.cmd
- assign.cmd
- config.cmd
- ddt86.cmd
- help.cmd
- print.cmd
- function.cmd
- gencmd.cmd
- stat.cmd

The kernels built arE:
- cpm86.sys/cpm.sys (ibm pc xt)
- cpmv20.sys (MBC V20, 8088 mode)
- cpm816.sys (MBC V20, mixed 8080/8088 mode with CP/M-80 compatibility)

The CP/M-86 OS is enhanced with the following patched or updated components:
- help.hlp (more complete content)
- dskmaint.cmd (updated from 1.0 to version 1.2)
- setup.cmd (updated from 1.0 to version 1.2)
- hdmaint.cmd (updated from 1.0 to version 1.1)
- ed.cmd (patched following dr recommendation)
- gendef.cmd (patched following dr recommendation)
- pip.cmd (patched following dr recommendation) 
- submit.cmd (patched following dr recommendation)
- mform.cmd (patched to avoid interactive question)
- tod.cmd (complete rewrite at https://github.com/tsupplis/cpm86-hacking)
- atinit.cmd (sync up RTC clock and bios if clock available, cf https://github.com/tsupplis/cpm86-hacking)

also the images produced from the blank image have a boot loader terminating with 55AA allowing emulators like qemu to load CP/M-86 properly. Beware, if the image is formatted using dskmaint.cmd, the signature will not be added. A small boot fix will be added later.

## Pedigree

The main source for it is: http://www.cpm.z80.de

- Baseline: http://www.cpm.z80.de/download/cpm86src.zip
- Baseline: http://www.cpm.z80.de/download/cpmdev.zip
- Patching Source: http://www.cpm.z80.de/download/cpm86ann.zip
- Patching Source: http://www.cpm.z80.de/download/cpm86bug.zip

To be continued...
