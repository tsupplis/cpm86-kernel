# CP/M-86 Kernel

## Synopsis

The goal of this project is to provide an out of the box cp/m-86 1.1 kernel that incorporate all existing patches plus the capacity to run on modern hardware and virtualization.

- visual y2k support
- AT support
- resilience to bios limits for video display

This is a raw dump right now with a way to compile the kernel starting from dissassembled sources.
The compilation requires the (cross-development environment for CP/M-86)(https://github.com/tsupplis/cpm86-crossdev)

To test, the PCE and cpmtools are needed:
-  PCE (http://www.hampa.ch/pce/)

<p align="center">
<img src="./diagrams/legacy.png" width="70%">
</p>
<p align="center">
Patched CP/M-86 running in the PCE Emulator
</p>


## Pedigree

The main source for it is: http://www.cpm.z80.de

- Baseline: http://www.cpm.z80.de/download/cpm86src.zip
- Baseline: http://www.cpm.z80.de/download/cpmdev.zip
- Patching Source: http://www.cpm.z80.de/download/cpm86ann.zip
- Patching Source: http://www.cpm.z80.de/download/cpm86bug.zip

To be continued...
