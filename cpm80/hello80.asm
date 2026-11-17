; This is an example of the "Hello World" program.
; Uses 8080 assembler mnemonics.
ORG 100h ; cpm programs start address.
JMP START ; go to program start.
; Variable storage space
MsgStr: DB 13,10,'Hello world.',13,10,0
Stack1: DW 0 ; place to save old stack.
Sbot: DS 32 ; temp stack for us to use.

; Constants
STOP: EQU $-1 ; top of our stack.
BDOS: EQU 5 ; address of BDOS entry.

; Start of code segment
START: LXI H, 0 ; HL = 0.
DAD SP ; HL = SP.
SHLD Stack1 ; save original stack.
LXI H, STOP ; HL = address of new stack.
SPHL ; stack pointer = our stack.
LXI H, MsgStr ; HL = address of string.
LOOP1: MOV A, M ; read string char.
ORA A ; set cpu flags.
JZ EXIT ; if char = 0 done.
MOV E, A ; E = char to send.
MVI C, 2 ; we want BDOS func 2.
PUSH H ; save HL register.
CALL BDOS ; call BDOS function.
POP H ; restore HL register
INX H ; point to next char.
JMP LOOP1 ; do next char.

; Exit and return code
EXIT: LHLD Stack1 ; HL = entry stack address.
SPHL ; SP = value on entry.
RET ; return control back to CPM.
END

