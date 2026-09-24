00000000  2E8C165B00        mov word [cs:0x5b],ss
00000005  2E89265900        mov [cs:0x59],sp
0000000A  8CDB              mov bx,ds
0000000C  9C                pushf
0000000D  58                pop ax
0000000E  FA                cli
0000000F  8ED3              mov ss,bx
00000011  8D263001          lea sp,[0x130]
00000015  50                push ax
00000016  9D                popf
00000017  E85600            call 0x70
0000001A  B119              mov cl,0x19
0000001C  E83E00            call 0x5d
0000001F  A20001            mov [0x100],al
00000022  B2FF              mov dl,0xff
00000024  90                nop
00000025  B120              mov cl,0x20
00000027  E83300            call 0x5d
0000002A  B104              mov cl,0x4
0000002C  D3E0              shl ax,cl
0000002E  0A060001          or al,[0x100]
00000032  8AC8              mov cl,al
00000034  9C                pushf
00000035  58                pop ax
00000036  FA                cli
00000037  2E8E165B00        mov ss,word [cs:0x5b]
0000003C  2E8B265900        mov sp,[cs:0x59]
00000041  50                push ax
00000042  9D                popf
00000043  2E8E065B00        mov es,word [cs:0x5b]
00000048  26C6060508FF      mov byte [es:0x805],0xff
0000004E  B200              mov dl,0x0
00000050  B100              mov cl,0x0
00000052  CDE0              int byte 0xe0
00000054  90                nop
00000055  90                nop
00000056  90                nop
00000057  90                nop
00000058  90                nop
00000059  0000              add [bx+si],al
0000005B  0000              add [bx+si],al
0000005D  CDE0              int byte 0xe0
0000005F  C3                ret
00000060  55                push bp
00000061  8BEC              mov bp,sp
00000063  8B5604            mov dx,[bp+0x4]
00000066  8B4E06            mov cx,[bp+0x6]
00000069  CDE0              int byte 0xe0
0000006B  5D                pop bp
0000006C  C20400            ret word 0x4
0000006F  00558B            add [di-0x75],dl
00000072  EC                in al,dx
00000073  E8D100            call 0x147
00000076  E89B01            call 0x214
00000079  E80203            call 0x37e
0000007C  5D                pop bp
0000007D  C3                ret
0000007E  55                push bp
0000007F  8BEC              mov bp,sp
00000081  B009              mov al,0x9
00000083  50                push ax
00000084  FF7604            push word [bp+0x4]
00000087  E8D6FF            call 0x60
0000008A  5D                pop bp
0000008B  C20200            ret word 0x2
0000008E  55                push bp
0000008F  8BEC              mov bp,sp
00000091  B00F              mov al,0xf
00000093  50                push ax
00000094  FF7604            push word [bp+0x4]
00000097  E8C6FF            call 0x60
0000009A  A25A01            mov [0x15a],al
0000009D  5D                pop bp
0000009E  C20200            ret word 0x2
000000A1  55                push bp
000000A2  8BEC              mov bp,sp
000000A4  B010              mov al,0x10
000000A6  50                push ax
000000A7  FF7604            push word [bp+0x4]
000000AA  E8B3FF            call 0x60
000000AD  A25A01            mov [0x15a],al
000000B0  5D                pop bp
000000B1  C20200            ret word 0x2
000000B4  55                push bp
000000B5  8BEC              mov bp,sp
000000B7  B013              mov al,0x13
000000B9  50                push ax
000000BA  FF7604            push word [bp+0x4]
000000BD  E8A0FF            call 0x60
000000C0  5D                pop bp
000000C1  C20200            ret word 0x2
000000C4  55                push bp
000000C5  8BEC              mov bp,sp
000000C7  B014              mov al,0x14
000000C9  50                push ax
000000CA  FF7604            push word [bp+0x4]
000000CD  E890FF            call 0x60
000000D0  5D                pop bp
000000D1  C20200            ret word 0x2
000000D4  55                push bp
000000D5  8BEC              mov bp,sp
000000D7  B015              mov al,0x15
000000D9  50                push ax
000000DA  FF7604            push word [bp+0x4]
000000DD  E880FF            call 0x60
000000E0  5D                pop bp
000000E1  C20200            ret word 0x2
000000E4  55                push bp
000000E5  8BEC              mov bp,sp
000000E7  B016              mov al,0x16
000000E9  50                push ax
000000EA  FF7604            push word [bp+0x4]
000000ED  E870FF            call 0x60
000000F0  A25A01            mov [0x15a],al
000000F3  5D                pop bp
000000F4  C20200            ret word 0x2
000000F7  55                push bp
000000F8  8BEC              mov bp,sp
000000FA  8A4604            mov al,[bp+0x4]
000000FD  FEC8              dec al
000000FF  884604            mov [bp+0x4],al
00000102  3CFF              cmp al,0xff
00000104  7412              jz 0x118
00000106  8B5E08            mov bx,[bp+0x8]
00000109  8A07              mov al,[bx]
0000010B  8B5E06            mov bx,[bp+0x6]
0000010E  8807              mov [bx],al
00000110  FF4608            inc word [bp+0x8]
00000113  FF4606            inc word [bp+0x6]
00000116  EBE2              jmp 0xfa
00000118  5D                pop bp
00000119  C20600            ret word 0x6
0000011C  55                push bp
0000011D  8BEC              mov bp,sp
0000011F  B8150A            mov ax,0xa15
00000122  50                push ax
00000123  E858FF            call 0x7e
00000126  B8180A            mov ax,0xa18
00000129  50                push ax
0000012A  E851FF            call 0x7e
0000012D  B83401            mov ax,0x134
00000130  50                push ax
00000131  E84AFF            call 0x7e
00000134  FF7604            push word [bp+0x4]
00000137  E844FF            call 0x7e
0000013A  B000              mov al,0x0
0000013C  B400              mov ah,0x0
0000013E  50                push ax
0000013F  50                push ax
00000140  E81DFF            call 0x60
00000143  5D                pop bp
00000144  C20200            ret word 0x2
00000147  55                push bp
00000148  8BEC              mov bp,sp
0000014A  B88100            mov ax,0x81
0000014D  50                push ax
0000014E  B85B01            mov ax,0x15b
00000151  50                push ax
00000152  B07F              mov al,0x7f
00000154  50                push ax
00000155  E89FFF            call 0xf7
00000158  8A1E8000          mov bl,[0x80]
0000015C  B700              mov bh,0x0
0000015E  C6875B0100        mov byte [bx+0x15b],0x0
00000163  B8270A            mov ax,0xa27
00000166  50                push ax
00000167  B86500            mov ax,0x65
0000016A  50                push ax
0000016B  B003              mov al,0x3
0000016D  50                push ax
0000016E  E886FF            call 0xf7
00000171  B85C00            mov ax,0x5c
00000174  50                push ax
00000175  E816FF            call 0x8e
00000178  803E5A01FF        cmp byte [0x15a],0xff
0000017D  7507              jnz 0x186
0000017F  B82A0A            mov ax,0xa2a
00000182  50                push ax
00000183  E896FF            call 0x11c
00000186  C606DB0180        mov byte [0x1db],0x80
0000018B  5D                pop bp
0000018C  C3                ret
0000018D  55                push bp
0000018E  8BEC              mov bp,sp
00000190  803EDB017F        cmp byte [0x1db],0x7f
00000195  7614              jna 0x1ab
00000197  B85C00            mov ax,0x5c
0000019A  50                push ax
0000019B  E826FF            call 0xc4
0000019E  08C0              or al,al
000001A0  7404              jz 0x1a6
000001A2  B01A              mov al,0x1a
000001A4  5D                pop bp
000001A5  C3                ret
000001A6  C606DB0100        mov byte [0x1db],0x0
000001AB  A0DB01            mov al,[0x1db]
000001AE  FEC0              inc al
000001B0  A2DB01            mov [0x1db],al
000001B3  FEC8              dec al
000001B5  B400              mov ah,0x0
000001B7  89C3              mov bx,ax
000001B9  8A878000          mov al,[bx+0x80]
000001BD  A2DC01            mov [0x1dc],al
000001C0  3C0D              cmp al,0xd
000001C2  7526              jnz 0x1ea
000001C4  A03601            mov al,[0x136]
000001C7  FEC0              inc al
000001C9  A23601            mov [0x136],al
000001CC  3C39              cmp al,0x39
000001CE  761A              jna 0x1ea
000001D0  C606360130        mov byte [0x136],0x30
000001D5  A03501            mov al,[0x135]
000001D8  FEC0              inc al
000001DA  A23501            mov [0x135],al
000001DD  3C39              cmp al,0x39
000001DF  7609              jna 0x1ea
000001E1  C606350130        mov byte [0x135],0x30
000001E6  FE063401          inc byte [0x134]
000001EA  A0DC01            mov al,[0x1dc]
000001ED  2C61              sub al,0x61
000001EF  3C1A              cmp al,0x1a
000001F1  7305              jnc 0x1f8
000001F3  8026DC015F        and byte [0x1dc],0x5f
000001F8  A0DC01            mov al,[0x1dc]
000001FB  5D                pop bp
000001FC  C3                ret
000001FD  55                push bp
000001FE  8BEC              mov bp,sp
00000200  B83901            mov ax,0x139
00000203  50                push ax
00000204  E8CDFE            call 0xd4
00000207  08C0              or al,al
00000209  7407              jz 0x212
0000020B  B8400A            mov ax,0xa40
0000020E  50                push ax
0000020F  E80AFF            call 0x11c
00000212  5D                pop bp
00000213  C3                ret
00000214  55                push bp
00000215  8BEC              mov bp,sp
00000217  C606DD0100        mov byte [0x1dd],0x0
0000021C  C70632010000      mov word [0x132],0x0
00000222  C606E00901        mov byte [0x9e0],0x1
00000227  A0E009            mov al,[0x9e0]
0000022A  D0D8              rcr al,1
0000022C  7203              jc 0x231
0000022E  E9C400            jmp 0x2f5
00000231  C606DD0900        mov byte [0x9dd],0x0
00000236  E854FF            call 0x18d
00000239  A2E109            mov [0x9e1],al
0000023C  3C1A              cmp al,0x1a
0000023E  B0FF              mov al,0xff
00000240  7501              jnz 0x243
00000242  40                inc ax
00000243  50                push ax
00000244  803EE1090D        cmp byte [0x9e1],0xd
00000249  B0FF              mov al,0xff
0000024B  7501              jnz 0x24e
0000024D  40                inc ax
0000024E  59                pop cx
0000024F  22C1              and al,cl
00000251  D0D8              rcr al,1
00000253  7203              jc 0x258
00000255  E98600            jmp 0x2de
00000258  803EE1090A        cmp byte [0x9e1],0xa
0000025D  74D7              jz 0x236
0000025F  803EE10924        cmp byte [0x9e1],0x24
00000264  7549              jnz 0x2af
00000266  E824FF            call 0x18d
00000269  A2E109            mov [0x9e1],al
0000026C  3C24              cmp al,0x24
0000026E  7465              jz 0x2d5
00000270  A0E109            mov al,[0x9e1]
00000273  2C30              sub al,0x30
00000275  A2E109            mov [0x9e1],al
00000278  3C09              cmp al,0x9
0000027A  7605              jna 0x281
0000027C  B87A0A            mov ax,0xa7a
0000027F  EB44              jmp 0x2c5
00000281  C606DF0900        mov byte [0x9df],0x0
00000286  E8A500            call 0x32e
00000289  82                db 0x82
0000028A  3EE109            loope 0x296
0000028D  00740D            add [si+0xd],dh
00000290  FE0EE109          dec byte [0x9e1]
00000294  E86000            call 0x2f7
00000297  D0D8              rcr al,1
00000299  72F9              jc 0x294
0000029B  EBE9              jmp 0x286
0000029D  E85700            call 0x2f7
000002A0  D0D8              rcr al,1
000002A2  7392              jnc 0x236
000002A4  FF36DE09          push word [0x9de]
000002A8  E89B00            call 0x346
000002AB  EBF0              jmp 0x29d
000002AD  EB87              jmp 0x236
000002AF  803EE1095E        cmp byte [0x9e1],0x5e
000002B4  751F              jnz 0x2d5
000002B6  E8D4FE            call 0x18d
000002B9  2C41              sub al,0x41
000002BB  A2E109            mov [0x9e1],al
000002BE  3C19              cmp al,0x19
000002C0  7609              jna 0x2cb
000002C2  B88A0A            mov ax,0xa8a
000002C5  50                push ax
000002C6  E853FE            call 0x11c
000002C9  EBE2              jmp 0x2ad
000002CB  A0E109            mov al,[0x9e1]
000002CE  FEC0              inc al
000002D0  50                push ax
000002D1  EB06              jmp 0x2d9
000002D3  EBD8              jmp 0x2ad
000002D5  FF36E109          push word [0x9e1]
000002D9  E86A00            call 0x346
000002DC  EBCF              jmp 0x2ad
000002DE  803EE1090D        cmp byte [0x9e1],0xd
000002E3  B0FF              mov al,0xff
000002E5  7401              jz 0x2e8
000002E7  40                inc ax
000002E8  A2E009            mov [0x9e0],al
000002EB  FF36DD09          push word [0x9dd]
000002EF  E85400            call 0x346
000002F2  E932FF            jmp 0x227
000002F5  5D                pop bp
000002F6  C3                ret
000002F7  55                push bp
000002F8  8BEC              mov bp,sp
000002FA  8A1EDF09          mov bl,[0x9df]
000002FE  B700              mov bh,0x0
00000300  8A875B01          mov al,[bx+0x15b]
00000304  A2DE09            mov [0x9de],al
00000307  3C20              cmp al,0x20
00000309  B0FF              mov al,0xff
0000030B  7401              jz 0x30e
0000030D  40                inc ax
0000030E  50                push ax
0000030F  82                db 0x82
00000310  3EDE09            fimul word [ds:bx+di]
00000313  00B0FF74          add [bx+si+0x74ff],dh
00000317  014059            add [bx+si+0x59],ax
0000031A  0AC1              or al,cl
0000031C  F6D0              not al
0000031E  D0D8              rcr al,1
00000320  7308              jnc 0x32a
00000322  FE06DF09          inc byte [0x9df]
00000326  B001              mov al,0x1
00000328  5D                pop bp
00000329  C3                ret
0000032A  B000              mov al,0x0
0000032C  5D                pop bp
0000032D  C3                ret
0000032E  55                push bp
0000032F  8BEC              mov bp,sp
00000331  8A1EDF09          mov bl,[0x9df]
00000335  B700              mov bh,0x0
00000337  80BF5B0120        cmp byte [bx+0x15b],0x20
0000033C  7506              jnz 0x344
0000033E  FE06DF09          inc byte [0x9df]
00000342  EBED              jmp 0x331
00000344  5D                pop bp
00000345  C3                ret
00000346  55                push bp
00000347  8BEC              mov bp,sp
00000349  A13201            mov ax,[0x132]
0000034C  40                inc ax
0000034D  A33201            mov [0x132],ax
00000350  3DFF07            cmp ax,0x7ff
00000353  7607              jna 0x35c
00000355  B8510A            mov ax,0xa51
00000358  50                push ax
00000359  E8C0FD            call 0x11c
0000035C  8A4604            mov al,[bp+0x4]
0000035F  8B1E3201          mov bx,[0x132]
00000363  8887DD01          mov [bx+0x1dd],al
00000367  A0DD09            mov al,[0x9dd]
0000036A  FEC0              inc al
0000036C  A2DD09            mov [0x9dd],al
0000036F  3C7D              cmp al,0x7d
00000371  7607              jna 0x37a
00000373  B8690A            mov ax,0xa69
00000376  50                push ax
00000377  E8A2FD            call 0x11c
0000037A  5D                pop bp
0000037B  C20200            ret word 0x2
0000037E  55                push bp
0000037F  8BEC              mov bp,sp
00000381  B83901            mov ax,0x139
00000384  50                push ax
00000385  E82CFD            call 0xb4
00000388  C606590100        mov byte [0x159],0x0
0000038D  B83901            mov ax,0x139
00000390  50                push ax
00000391  E850FD            call 0xe4
00000394  803E5A01FF        cmp byte [0x15a],0xff
00000399  7507              jnz 0x3a2
0000039B  B8A40A            mov ax,0xaa4
0000039E  50                push ax
0000039F  E87AFD            call 0x11c
000003A2  E85100            call 0x3f6
000003A5  A2E209            mov [0x9e2],al
000003A8  08C0              or al,al
000003AA  7433              jz 0x3df
000003AC  A0E209            mov al,[0x9e2]
000003AF  A28000            mov [0x80],al
000003B2  B400              mov ah,0x0
000003B4  89C3              mov bx,ax
000003B6  C687810000        mov byte [bx+0x81],0x0
000003BB  C687820024        mov byte [bx+0x82],0x24
000003C0  82                db 0x82
000003C1  3EE209            loop 0x3cd
000003C4  007413            add [si+0x13],dh
000003C7  E82C00            call 0x3f6
000003CA  8A1EE209          mov bl,[0x9e2]
000003CE  B700              mov bh,0x0
000003D0  88878000          mov [bx+0x80],al
000003D4  FE0EE209          dec byte [0x9e2]
000003D8  EBE6              jmp 0x3c0
000003DA  E820FE            call 0x1fd
000003DD  EBC3              jmp 0x3a2
000003DF  B83901            mov ax,0x139
000003E2  50                push ax
000003E3  E8BBFC            call 0xa1
000003E6  803E5A01FF        cmp byte [0x15a],0xff
000003EB  7507              jnz 0x3f4
000003ED  B8B30A            mov ax,0xab3
000003F0  50                push ax
000003F1  E828FD            call 0x11c
000003F4  5D                pop bp
000003F5  C3                ret
000003F6  55                push bp
000003F7  8BEC              mov bp,sp
000003F9  A13201            mov ax,[0x132]
000003FC  48                dec ax
000003FD  A33201            mov [0x132],ax
00000400  89C3              mov bx,ax
00000402  8A87DD01          mov al,[bx+0x1dd]
00000406  5D                pop bp
00000407  C3                ret
00000408  0000              add [bx+si],al
0000040A  0000              add [bx+si],al
0000040C  0000              add [bx+si],al
0000040E  0000              add [bx+si],al
