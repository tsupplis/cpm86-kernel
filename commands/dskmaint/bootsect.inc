; Boot sector written to track 0 by dskmaint, included into its data segment.
bootsect	db	0fah,8ch,0c8h,8eh,0d8h,8eh,0d0h,0bch,00h,7ch,0fbh
	db	0cdh,12h,2dh,08h,00h,0b1h,06h,0d3h,0e0h,0a3h
	db	51h,7ch,0b4h,00h,0cdh,13h,8eh,06h,51h,7ch,0bah
	db	00h,00h,0b9h,05h,00h,0bbh,00h,00h,0b8h,04h,02h
	db	0cdh,13h,73h,09h,0feh,0eh,53h,7ch,75h,0e2h,0e9h
	db	04h,00h,0ffh,2eh,4fh,7ch,0beh,54h,7ch,0fch,0ach
	db	0b4h,0eh,2bh,0dbh,0cdh,10h,0ach,84h,0c0h,75h,0f5h
	db	0fbh,0ebh,0fdh,00h,01h,00h,00h,04h
	db	0dh,0ah,0ah,'*** Error while reading Loader ***'
	db	0dh,0ah,'Try another diskette.',0dh,0ah,00h
