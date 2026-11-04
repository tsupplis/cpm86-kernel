"""Native directory-repair checks on disposable images; no user disks."""
from pathlib import Path
import tempfile
from live import (ROOT,MEDIA,local_system,prepare_system,prepare_data,convert,
                  directory_entries,boot,read_screen)

def main():
    system=local_system();cwd=ROOT if system=='cpm86' else MEDIA
    fmt='cpm86-320' if system=='cpm86' else 'ccpm86-320'
    empty=ROOT/'base-320.img' if system=='cpm86' else MEDIA/'base.img'
    with tempfile.TemporaryDirectory(prefix='chkcpmfs-native-repair-') as tmp:
        folder=Path(tmp)
        sysimage,_=prepare_system(folder,system,fmt,cwd)
        clean,_,_,_,_=prepare_data(folder,empty,fmt,cwd)
        logical=folder/'dirty.logical';convert(clean,logical,'untwist',cwd)
        data=bytearray(logical.read_bytes())
        first=next(at for at,e in directory_entries(logical) if e[1:12]==b'FIRST   DAT')
        duplicate=next(at for at in range(4096+40*32,6144,32) if data[at]==0xe5)
        data[first+12]|=0xe0;data[first+14]|=0xc0
        data[duplicate:duplicate+32]=data[first:first+32]
        first_stamp=(first//128)*128+97+(first//32%4)*10
        duplicate_stamp=(duplicate//128)*128+97+(duplicate//32%4)*10
        if data[(first//128)*128+96]==33 and data[(duplicate//128)*128+96]==33:
            data[duplicate_stamp:duplicate_stamp+10]=data[first_stamp:first_stamp+10]
        logical.write_bytes(data);dirty=folder/'dirty.img';convert(logical,dirty,'twist',cwd)
        expected=bytearray(data);expected[first+12]&=31;expected[first+14]&=63;expected[duplicate]=0xe5
        logical.write_bytes(expected);fixed=folder/'fixed.img';convert(logical,fixed,'twist',cwd)
        screen,status=boot(folder,system,sysimage,dirty,repair=True,expected_target=fixed.read_bytes())
        assert 'Metadata repairs written and verified.' in read_screen(folder/'repair-result.bin'),read_screen(folder/'repair-result.bin')
        assert 'Consistency errors: 0' in screen,screen
        assert 'B: RW' in status,status
        boot(folder,system,sysimage,dirty,repair=True,answer='n')
        assert 'Repair cancelled; no changes written.' in read_screen(folder/'repair-result.bin')
        # A conflicting duplicate must prevent even the otherwise safe bit repair.
        conflict=bytearray(data);conflict[duplicate+16]+=1
        logical.write_bytes(conflict);bad=folder/'conflict.img';convert(logical,bad,'twist',cwd)
        boot(folder,system,sysimage,bad,repair=True)
        assert 'ambiguous or unsafe findings prevent all repairs' in read_screen(folder/'repair-result.bin')
    print('PASS: native '+system+' combined metadata repair, clean rescan, cancellation and conflicting-duplicate refusal; exact images')

if __name__=='__main__':main()
