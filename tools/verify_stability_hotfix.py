"""Verify the serialized patch against the user's original Vita archive."""
import argparse
import collections
import json
from pathlib import Path
import struct
import cricodecs.cpk as cpk
from build_full_italian_cpk import is_arc,parse_arc,is_pac,parse_pac
from build_vita_bf import parse_bmd,read_sections
from build_vita_tables import parse_table,parse_bvp
from build_stability_hotfix import file_lookup,sha256
from vita_native_policy import approved_texture,check_adapted_text,community_text_ranges
from cpk_vita_metadata import verify_metadata
from battle_commands import preserve_command_texture


def decode_relocations(data):
    offset,size = struct.unpack_from('<II',data,16)
    if offset+size > len(data): raise ValueError('Relocations outside file')
    cursor,result,pos = 32,[],offset
    while pos < offset+size:
        value = data[pos];pos += 1
        if value & 1:
            if value & 7 == 7:
                for _ in range(2+(value >> 3)):
                    cursor += 4;result.append(cursor)
                continue
            value = value-1+(data[pos]<<8);pos += 1
        else: value *= 2
        cursor += value;result.append(cursor)
    return result


def check_messages(vita, localized):
    a,b = parse_bmd(vita),parse_bmd(localized)
    assert [(d['name'],d['kind']) for d in a['dialogs']] == [(d['name'],d['kind']) for d in b['dialogs']], 'Dialog IDs/kinds changed'
    assert len(a['speakers']) == len(b['speakers']), 'Native speaker table changed size'
    expected = [36+i*8 for i in range(len(b['dialogs']))]+[32+len(b['dialogs'])*8]
    for old,new in zip(a['dialogs'],b['dialogs']):
        if new['kind'] == 0:
            assert old['speaker_id'] == new['speaker_id'], 'Speaker ID changed'
            speaker = new['speaker_id']
            # Empty placeholder messages can have no speaker table in retail.
            if new['page_count'] and speaker < 0x8000:
                assert speaker < len(b['speakers']), 'Speaker outside table'
            off = 32+new['dlg_offset']+28
            addresses = new['page_addrs']
        else:
            assert old['option_count'] == new['option_count'], 'Choice count changed'
            off = 32+new['dlg_offset']+32
            addresses = new['opt_addrs']
        expected.extend(range(off,off+len(addresses)*4,4))
    arr,n = struct.unpack_from('<II',localized,32+len(b['dialogs'])*8)
    expected.extend(range(32+arr,32+arr+n*4,4))
    actual = decode_relocations(localized)
    # Unmodified retail messages can share dialog bodies and relocations;
    # their existing table is authoritative. Every rebuilt table is exact.
    if vita != localized:
        assert actual == expected, 'Incorrect relocation table'
    return len(b['dialogs'])


def check_pair(vita, patched, path, counts):
    counts['assets'] += 1
    assert is_arc(vita)==is_arc(patched),'ARC container format changed: '+path
    assert is_pac(vita)==is_pac(patched),'PAC container format changed: '+path
    if is_arc(vita) and is_arc(patched):
        va,pa=parse_arc(vita),parse_arc(patched)
        assert list(va) == list(pa), f'ARC directory changed: {path}'
        cursor=4
        for k in va:
            assert len(va[k])%32==0, f'Unknown native ARC member alignment: {path}/{k}'
            assert len(pa[k])%32==0, f'ARC member padding lost: {path}/{k}'
            assert (cursor+36)%4==0, f'Unaligned ARC member address: {path}/{k}'
            counts['aligned_arc_members']+=1
            check_pair(va[k],pa[k],path+'/'+k,counts)
            cursor+=36+len(pa[k])
    elif is_pac(vita) and is_pac(patched):
        va,vo=parse_pac(vita);pa,po=parse_pac(patched)
        assert vo==po, f'PAC directory/order changed: {path}'
        for k in vo: check_pair(va[k],pa[k],path+'/'+k,counts)
    elif vita[8:12] in (b'FLW0',b'PMD1'):
        magic=vita[8:12];message_kind=3 if magic==b'FLW0' else 6
        old=vita
        if magic==b'PMD1':
            n=struct.unpack_from('<I',vita,4)[0]
            if len(vita)<n<=len(vita)+16:old=vita.ljust(n,b'\0')
        vs,ps=read_sections(old,magic),read_sections(patched,magic)
        assert len(vs)==len(ps),'Section count changed'
        for a,b in zip(vs,ps):
            t,s,n,o=a;tt,ss,nn,oo=b
            assert t==tt,'Section kind changed'
            if t!=message_kind:
                layout_ok=a==b or (magic==b'FLW0' and t==4 and a[:3]==b[:3])
                assert layout_ok and old[o:o+s*n]==patched[oo:oo+ss*nn], f'Native section {t} modified: {path}'
            elif s*n:
                counts['dialogs']+=check_messages(old[o:o+s*n],patched[oo:oo+ss*nn])
        counts['flowscripts' if magic==b'FLW0' else 'events']+=1
        if magic==b'FLW0':
            strings=next(s for s in ps if s[0]==4)
            assert struct.unpack_from('<I',patched,4)[0]==strings[3],'BF FileSize convention changed'
            assert all(a[3]<=b[3] for a,b in zip(ps,ps[1:])),'BF section physical order changed'
    elif vita[8:12]==b'MSG1':
        counts['dialogs']+=check_messages(vita,patched)
        counts['message_files']+=1
    elif path.lower().endswith(('aicalc.tbl','encount.tbl','msg.tbl')):
        va,pa=parse_table(vita),parse_table(patched)
        assert len(va)==len(pa),'Table block count changed'
        for i,(a,b) in enumerate(zip(va,pa)):
            if a[8:12] in (b'FLW0',b'MSG1'):
                check_pair(a,b,path+f'/block{i}',counts)
            elif path.lower().endswith('msg.tbl'):
                assert len(a)==len(b),'Native text slot layout changed'
            else:assert a==b,'Native battle table data changed'
        counts['battle_tables']+=1
    elif path.lower().endswith('.bvp'):
        va,pa=parse_bvp(vita),parse_bvp(patched)
        assert len(va)==len(pa),'BVP directory count changed'
        for i,((t,a),(tt,b)) in enumerate(zip(va,pa)):
            assert t==tt,'BVP entry kind changed'
            if not a:
                assert vita[i*12:i*12+12] == patched[i*12:i*12+12], 'BVP sentinel changed'
            if a[8:12]==b'MSG1':check_pair(a,b,path+f'/entry{i}',counts)
            else:assert a==b,'Native BVP data changed'
        counts['battle_voices']+=1
    elif path.lower().endswith(('.bed','dummy.dat')):
        assert vita==patched,'Native battle effect changed'
        counts['native_battle_assets']+=1
    elif path.lower().endswith('itemtbl.bin'):
        assert len(vita)==len(patched) and vita[:174112]==patched[:174112], 'Native item layout changed'
        counts['item_tables']+=1
    elif preserve_command_texture(vita,patched,path) is not None:
        counts['battle_command_textures']+=1
    elif approved_texture(path):
        assert len(vita)==len(patched) and vita[8:12]==patched[8:12],'Adapted texture native layout changed'
        counts['adapted_textures']+=1
    elif check_adapted_text(vita,patched,path):
        counts['fixed_text_tables']+=1
    elif community_text_ranges(vita,path):
        assert len(vita)==len(patched) and vita[:8]==patched[:8],'Community text native layout changed'
        masked=bytearray(patched)
        for offset,size in community_text_ranges(vita,path):masked[offset:offset+size]=vita[offset:offset+size]
        assert bytes(masked)==vita,'Community table gameplay metadata changed'
        counts['community_tables']+=1
    else:
        assert vita==patched,'Unrecognized native asset changed: '+path
        counts['unchanged_native_assets']+=1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vita',default='clean_vita_data.cpk')
    parser.add_argument('--patch',default='P4G_Italian_Patch_v1.0.4/rePatch/PCSB00245/data/data.cpk')
    parser.add_argument('--report',default='P4G_Italian_Patch_v1.0.4/verification_report.json')
    args=parser.parse_args()
    verify_metadata(args.vita,args.patch)
    v,p=cpk.load(args.vita),cpk.load(args.patch)
    vi,pi=file_lookup(v),file_lookup(p)
    assert set(vi)==set(pi),'CPK directory changed'
    counts=collections.Counter();errors=[]
    for key,i in vi.items():
        try:check_pair(v.file_bytes(i),p.file_bytes(pi[key]),key,counts)
        except Exception as exc:errors.append((key,str(exc)))
        if i%2500==0:print('Verified',i,'/',len(vi),flush=True)
    report={'passed':not errors,'hardware_tested':False,'native_cpk_metadata_preserved':True,'counts':dict(counts),'errors':errors,'data_cpk_sha256':sha256(args.patch)}
    executable=Path(args.patch).parents[1]/'eboot.bin'
    if executable.exists():
        blob=executable.read_bytes()
        assert blob[:4]==b'SCE\0', 'Executable is not a SELF'
        assert struct.unpack_from('<Q',blob,32)[0]==len(blob), 'SELF file size mismatch'
        report['eboot_sha256']=sha256(executable)
    Path(args.report).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
