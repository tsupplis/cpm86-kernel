declare
    true literally '1',
    false literally '0',
    forever literally 'while true',
    cr literally '13',
    lf literally '10';

printchar: procedure(char) public;
    declare char byte;
    call mon1(2,char);
    end printchar;

crlf: procedure public;
    call printchar(cr);
    call printchar(lf);
    end crlf;

printn: procedure(a) public;
    declare a address;
    call mon1(9,a);
    end printn;

print: procedure(a) public;
    declare a address;
    /* print the string starting at address a until the
    next dollar sign is encountered */
    call crlf;
    call printn(a);
    end print;

declare dcnt byte public;

open: procedure(fcb) public;
    declare fcb address;
    dcnt = mon2(15,fcb);
    end open;

close: procedure(fcb) public;
    declare fcb address;
    dcnt = mon2(16,fcb);
    end close;

delete: procedure(fcb) public;
    declare fcb address;
    call mon1(19,fcb);
    end delete;

diskread: procedure(fcb) byte public;
    declare fcb address;
    return mon2(20,fcb);
    end diskread;

diskwrite: procedure(fcb) byte public;
    declare fcb address;
    return mon2(21,fcb);
    end diskwrite;

make: procedure(fcb) public;
    declare fcb address;
    dcnt = mon2(22,fcb);
    end make;

rename: procedure(fcb) public;
    declare fcb address;
    call mon1(23,fcb);
    end rename;

setdma: procedure(dma) public;
    declare dma address;
    call mon1(26,dma);
    end setdma;
