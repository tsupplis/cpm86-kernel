"""Confirmed, narrow metadata repairs through the compiled PL/M core.
Raw adapter calls are substituted; live tests exercise the real adapter.
Every resulting directory byte is compared, including refused/cancelled cases.
"""
from pathlib import Path
import tempfile
from check import COMMAND,entry,run_case

count=0
with tempfile.TemporaryDirectory(prefix='chkcpmfs-repair-') as tmp:
    tmp=Path(tmp);image=(COMMAND/'chkcpmfs.cmd').read_bytes()
    def run(version,name,entries,expected=None,needles=(),**extra):
        global count
        settings=dict(REPAIR_FIXTURE=1,TAIL='"A: [F]"',ANSWER=89,
            RAW_OPEN_FAIL=0,RAW_READ_FAIL=65535,RAW_WRITE_FAIL=65535,RAW_VERIFY_FAIL=65535,
            EXPECTED_SEARCHES=0,EXPECTED_DMA_SETS=1,EXPECTED_RO_QUERIES=1,
            EXPECTED_PROTECTS=0,EXPECTED_RESETS=0,EXPECTED_USER_SETS=0,EXPECTED_USER_MASK=0,
            EXPECTED_FINAL_RO=0)
        settings.update(extra)
        before=b''.join(entries);before+=b'\xe5'*(2048-len(before))
        expected=before if expected is None else expected
        text=run_case(tmp,image,version,name,entries,settings,list(needles))
        after=(tmp/'after.bin').read_bytes()
        assert after==expected,(name,version,[(i,a,b) for i,(a,b) in enumerate(zip(after,expected)) if a!=b][:8],text)
        count+=1
        return text,after,before
    for v in (0x22,0x1431,0x1441):
        bad=entry('FLAGS.DAT',[1],extent=0xe0,module=0xc0,records=1)
        expected=bytearray(bad+b'\xe5'*(2048-32));expected[12]=expected[14]=0
        run(v,'normalize',[bad],expected,('Metadata repairs written and verified.',),EXPECTED_RESETS=1)
        for tail in ('A: [FV]','A: [VF]','A: [F','a: [fv]','A: /F','a: /fv'):
            run(v,'repair-syntax',[bad],expected,('Metadata repairs written and verified.',),EXPECTED_RESETS=1,TAIL='"'+tail+'"')
        run(v,'reset-failure',[bad],expected,('post-repair drive reset failed',),EXPECTED_RESETS=1,RESTORE_FAIL=1)
        run(v,'cancel',[bad],needles=('Repair cancelled; no changes written.',),ANSWER=78)
        run(v,'readonly',[bad],needles=('drive is read-only; repair refused.',),INITIAL_RO=1,EXPECTED_FINAL_RO=1)
        run(v,'open-failure',[bad],needles=('cannot acquire supported directory I/O',),RAW_OPEN_FAIL=1)
        good=entry('DUP.DAT',[1],records=1)
        for pos in (1,5):
            entries=[good]+[bytes([0xe5])*32]*(pos-1)+[good]
            exp=bytearray(b''.join(entries)+b'\xe5'*(2048-len(entries)*32));exp[pos*32]=0xe5
            run(v,'identical-duplicate',entries,exp,('Metadata repairs written and verified.',),EXPECTED_RESETS=1)
        entries=[bad,bad];exp=bytearray(b''.join(entries)+b'\xe5'*(2048-64));exp[12]=exp[14]=0;exp[32]=0xe5
        run(v,'combined',entries,exp,('Metadata repairs written and verified.',),EXPECTED_RESETS=1)
        run(v,'conflicting',[good,entry('DUP.DAT',[2],records=1)],needles=('ambiguous or unsafe',))
        run(v,'crosslink',[bad,entry('OTHER.DAT',[1],records=1)],needles=('ambiguous or unsafe',))
        run(v,'bad-count',[bad,entry('COUNT.DAT',[2],records=129)],needles=('ambiguous or unsafe',))
        run(v,'metadata',[good,good,entry('XFCB.DAT',user=16)],needles=('associated metadata prevents duplicate removal',))
        run(v,'stamp',[good,good,entry('STAMP.DAT',user=33)],needles=('associated metadata prevents duplicate removal',))

        # Known timestamp records and volume labels remain byte-identical.
        sfcb=bytearray(32);sfcb[0]=33;sfcb[1:11]=bytes(range(1,11))
        entries=[good,bytes([0xe5])*32,bytes([0xe5])*32,bytes(sfcb),good,
                 entry('LABEL.DAT',user=32),bytes([0xe5])*32,bytes(sfcb)]
        exp=bytearray(b''.join(entries)+b'\xe5'*(2048-len(entries)*32));exp[128]=0xe5
        run(v,'equal-stamps',entries,exp,('Metadata repairs written and verified.',),EXPECTED_RESETS=1)
        other=bytearray(sfcb);other[1]^=1;entries[-1]=bytes(other)
        run(v,'different-stamps',entries,needles=('ambiguous or unsafe',))
        uncertain=bytearray(bad);uncertain[1]=0
        run(v,'uncertain-name',[bytes(uncertain)],needles=('UNCERTAIN FILENAME; REPAIR REFUSED',))
        run(v,'no-repair',[good],needles=('No metadata repairs needed.',))
        # Different S1/attribute bytes must prevent "identical" classification.
        for off in (9,13):
            other=bytearray(good);other[off]^=0x80
            run(v,'nonidentical',[good,bytes(other)],needles=('ambiguous or unsafe',))
        # Duplicate removal precedes normalization, so every completed prefix
        # leaves an unambiguous retry instead of two records with different flags.
        split=[bad]+[bytes([0xe5])*32]*4+[bad]
        original=b''.join(split)+b'\xe5'*(2048-len(split)*32)
        deleted=bytearray(original);deleted[160]=0xe5
        fixed=bytearray(deleted);fixed[12]=fixed[14]=0
        for fail in (1,2):
            run(v,'duplicate-first-write-failure',split,original if fail==1 else deleted,
                ('disk may contain partial changes.',),RAW_WRITE_FAIL=fail,EXPECTED_RESETS=1)
        for fail in range(1,36):
            exp=original if fail<=18 else deleted if fail==19 else fixed
            run(v,'duplicate-first-read-failure',split,exp,RAW_READ_FAIL=fail,
                EXPECTED_RESETS=0 if fail<=18 else 1)
        resumed=[bytes(deleted[i:i+32]) for i in range(0,192,32)]
        run(v,'retry-after-duplicate-removal',resumed,fixed,
            ('Metadata repairs written and verified.',),EXPECTED_RESETS=1)
        # Two separate records: failed writes retain only successful prefixes.
        entries=[bad]+[bytes([0xe5])*32]*3+[entry('OTHER.DAT',[2],extent=0xe0,module=0xc0,records=1)]
        before=b''.join(entries)+b'\xe5'*(2048-160)
        first=bytearray(before);first[12]=first[14]=0
        both=bytearray(first);both[140]=both[142]=0
        run(v,'two-records',entries,both,('Metadata repairs written and verified.',),EXPECTED_RESETS=1)
        for fail in (1,2):
            run(v,'write-failure',entries,before if fail==1 else first,
                ('disk may contain partial changes.',),RAW_WRITE_FAIL=fail,EXPECTED_RESETS=1)
            run(v,'verify-failure',entries,first if fail==1 else both,
                ('disk may contain partial changes.',),RAW_VERIFY_FAIL=fail,EXPECTED_RESETS=1)
        # Fail every planning, execution and final scan read, comparing exact
        # possible committed prefixes. No stage can write after the failed read.
        for fail in range(1,35):
            if fail<=17:exp=before
            elif fail==18:exp=first
            else:exp=both
            # scan 16 reads, then execution reads 17/18, final scan 19..34.
            run(v,'read-failure',entries,exp,RAW_READ_FAIL=fail,
                EXPECTED_RESETS=0 if fail<=17 else 1)
print(f'PASS: {count} compiled metadata repair cases across three OS versions; exact changes/refusals/failure prefixes')
