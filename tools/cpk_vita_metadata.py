"""Preserve the retail Vita CPK UTF schemas and directory order on save."""
import struct
from pathlib import Path
import cricodecs.cpk as cpk

FORMATS={0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'Q',7:'q',8:'f',10:'I',11:'II'}


def read_chunk(stream,offset):
    stream.seek(offset)
    header=stream.read(16)
    if len(header)!=16:raise ValueError('Missing CPK chunk')
    size=struct.unpack_from('<Q',header,8)[0]
    payload=stream.read(size)
    if len(payload)!=size:raise ValueError('Truncated CPK chunk')
    return header,payload


class Utf:
    def __init__(self,data):
        self.data=bytearray(data)
        if self.data[:4]!=b'@UTF':raise ValueError('Only plain retail UTF metadata supported')
        _,size,rows,strings,blobs,self.name,columns,self.width,self.count=struct.unpack_from('>4sIIIIIHHI',data)
        self.rows,self.strings,self.blobs=rows+8,strings+8,blobs+8
        if size+8!=len(data):raise ValueError('UTF size mismatch')
        self.columns=[]
        offset,row_cursor=32,0
        for _ in range(columns):
            flags,name=struct.unpack_from('>BI',data,offset);offset+=5
            storage,kind=flags&0xf0,flags&15
            fmt='>'+FORMATS[kind];n=struct.calcsize(fmt)
            name=self.string(name)
            if storage==0x30:cell=offset;offset+=n
            elif storage==0x50:cell=row_cursor;row_cursor+=n
            elif storage==0x10:cell=None
            else:raise ValueError('Unsupported UTF storage')
            self.columns.append((name,storage,kind,cell,fmt))
        if row_cursor!=self.width:raise ValueError('UTF row width mismatch')
        if self.rows+self.width*self.count>len(data):raise ValueError('UTF rows outside table')

    def string(self,offset):
        start=self.strings+offset;end=self.data.index(0,start)
        return bytes(self.data[start:end]).decode('utf-8')

    def get(self,name,row=0):
        for column in self.columns:
            key,storage,kind,cell,fmt=column
            if key!=name:continue
            if cell is None:return 0
            pos=cell if storage==0x30 else self.rows+row*self.width+cell
            value=struct.unpack_from(fmt,self.data,pos)
            value=value[0] if len(value)==1 else value
            return self.string(value) if kind==10 else value
        raise KeyError(name)

    def set_number(self,name,value,row=0):
        key,storage,kind,cell,fmt=next(c for c in self.columns if c[0]==name)
        if kind in (10,11):raise ValueError('Numeric setter cannot change UTF strings/blobs')
        if cell is None:
            if value!=0:raise ValueError('Cannot populate a native zero-storage field')
            return
        pos=cell if storage==0x30 else self.rows+row*self.width+cell
        struct.pack_into(fmt,self.data,pos,value)


def describe(path):
    with open(path,'rb') as stream:
        _,payload=read_chunk(stream,0);header=Utf(payload)
        print(path,'HEADER',[(n,hex(s|k),header.get(n)) for n,s,k,_,_ in header.columns])
        for name in ('TocOffset','EtocOffset'):
            _,payload=read_chunk(stream,header.get(name));table=Utf(payload)
            print(name,table.count,table.width,[(n,hex(s|k)) for n,s,k,_,_ in table.columns])


def preserve_metadata(native_path,patched_path):
    """Replace only metadata, using original rows/names/types/flags verbatim.

    Compressed payload bytes and their current absolute offsets do not move.
    """
    patched=cpk.load(str(patched_path))
    before_entries=[(f.full_path,f.file_offset,f.file_size,f.extract_size)
                    for i in range(patched.file_count) for f in (patched.file_info(i),)]
    lookup={name.lower():(offset,size,extracted) for name,offset,size,extracted in before_entries}
    # The native extension holds a read-only Windows file handle until release.
    del patched
    import gc
    gc.collect()
    with open(native_path,'rb') as source,open(patched_path,'r+b') as target:
        nh,np=read_chunk(source,0);native_header=Utf(np)
        _,pp=read_chunk(target,0);current_header=Utf(pp)
        if current_header.get('ContentOffset')!=native_header.get('ContentOffset'):
            raise ValueError('Payload start differs from the native metadata prefix')
        ntoc_head,ntoc_bytes=read_chunk(source,native_header.get('TocOffset'))
        toc=Utf(ntoc_bytes)
        base=min(current_header.get('TocOffset'),current_header.get('ContentOffset'))
        for row in range(toc.count):
            dirname=toc.get('DirName',row);filename=toc.get('FileName',row)
            key='/'.join(p for p in (dirname,filename) if p and p!='<NULL>').lower()
            offset,size,extracted=lookup.pop(key)
            toc.set_number('FileSize',size,row)
            toc.set_number('ExtractSize',extracted,row)
            toc.set_number('FileOffset',offset-base,row)
        if lookup:raise ValueError('Patched file directory differs from native Vita')
        etoc_header,etoc_bytes=read_chunk(source,native_header.get('EtocOffset'))
        for name in ('ContentOffset','ContentSize','EtocOffset','EnabledPackedSize','EnabledDataSize'):
            if any(c[0]==name for c in native_header.columns) and any(c[0]==name for c in current_header.columns):
                native_header.set_number(name,current_header.get(name))
        native_header.set_number('TocSize',16+len(toc.data))
        native_header.set_number('EtocSize',16+len(etoc_bytes))
        if native_header.get('TocOffset')+16+len(toc.data)>native_header.get('ContentOffset'):
            raise ValueError('Native TOC does not fit before payloads')
        source.seek(0)
        prefix=bytearray(source.read(native_header.get('ContentOffset')))
        prefix[:16+len(native_header.data)]=nh+native_header.data
        offset=native_header.get('TocOffset')
        prefix[offset:offset+16+len(toc.data)]=ntoc_head+toc.data
        target.seek(0);target.write(prefix)
        target.seek(native_header.get('EtocOffset'));target.write(etoc_header+etoc_bytes)
        target.truncate(native_header.get('EtocOffset')+16+len(etoc_bytes))
        target.flush()
    # A separate reader must resolve every entry to the same physical bytes.
    reread=cpk.load(str(patched_path))
    entries={reread.file_info(i).full_path.lower():reread.file_info(i) for i in range(reread.file_count)}
    for name,offset,size,extracted in before_entries:
        after=entries[name.lower()]
        assert (offset,size,extracted)==(after.file_offset,after.file_size,after.extract_size)


def verify_metadata(native_path,patched_path):
    with open(native_path,'rb') as source,open(patched_path,'rb') as target:
        _,a=read_chunk(source,0);_,b=read_chunk(target,0)
        a,b=Utf(a),Utf(b)
        assert a.columns==b.columns and a.width==b.width and a.count==b.count,'Native CPK header schema changed'
        for name in ('Version','Revision','Align','Sorted','Files','UpdateDateTime','CpkMode'):
            assert a.get(name)==b.get(name),'Native CPK configuration changed: '+name
        for name in ('TocOffset','EtocOffset'):
            _,av=read_chunk(source,a.get(name));_,bv=read_chunk(target,b.get(name))
            av,bv=Utf(av),Utf(bv)
            assert av.columns==bv.columns and av.width==bv.width and av.count==bv.count,'Native CPK directory schema/count changed: '+name
            if name=='TocOffset':
                for row in range(av.count):
                    for column in ('DirName','FileName','ID','UserString'):
                        assert av.get(column,row)==bv.get(column,row),'Native CPK directory order or ID changed'
            else:assert av.data==bv.data,'Native ETOC metadata changed'
        target.seek(0,2)
        assert target.tell()==b.get('EtocOffset')+b.get('EtocSize'),'CPK trailing metadata/file size mismatch'


def append_entry_update(base_path,rebuilt_path,output_path,changed_path):
    """Keep every existing payload offset; append one updated packed entry.

    The generic writer supplies the compressed bytes. Moving only that entry
    avoids shifting two gigabytes of otherwise unchanged data on the Vita.
    """
    import shutil,gc
    from pathlib import Path
    base=cpk.load(str(base_path));rebuilt=cpk.load(str(rebuilt_path))
    old={base.file_info(i).full_path.lower():base.file_info(i) for i in range(base.file_count)}
    new={rebuilt.file_info(i).full_path.lower():rebuilt.file_info(i) for i in range(rebuilt.file_count)}
    key=changed_path.lower()
    if set(old)!=set(new) or key not in old:raise ValueError('CPK directory changed')
    for name,f in old.items():
        if name!=key and (f.file_size,f.extract_size)!=(new[name].file_size,new[name].extract_size):
            raise ValueError('Unexpected additional changed CPK entry: '+name)
    changed=new[key]
    with open(base_path,'rb') as source,open(rebuilt_path,'rb') as packed:
        header=Utf(read_chunk(source,0)[1])
        toc=Utf(read_chunk(source,header.get('TocOffset'))[1])
        etoc_header,etoc=read_chunk(source,header.get('EtocOffset'))
        new_header=Utf(read_chunk(packed,0)[1])
        packed.seek(changed.file_offset);payload=packed.read(changed.file_size)
    if len(payload)!=changed.file_size:raise ValueError('Truncated replacement payload')
    insertion=header.get('EtocOffset')
    next_etoc=(insertion+len(payload)+2047)&~2047
    base_offset=min(header.get('TocOffset'),header.get('ContentOffset'))
    matches=[]
    for row in range(toc.count):
        name='/'.join(x for x in (toc.get('DirName',row),toc.get('FileName',row)) if x and x!='<NULL>')
        if name.lower()==key:matches.append(row)
    if len(matches)!=1:raise ValueError('Ambiguous replacement TOC row')
    row=matches[0]
    toc.set_number('FileOffset',insertion-base_offset,row)
    toc.set_number('FileSize',changed.file_size,row)
    toc.set_number('ExtractSize',changed.extract_size,row)
    header.set_number('EtocOffset',next_etoc)
    header.set_number('ContentSize',next_etoc-header.get('ContentOffset'))
    for field in ('EnabledPackedSize','EnabledDataSize'):
        header.set_number(field,new_header.get(field))
    output=Path(output_path)
    if output.exists() or output.resolve() in (Path(base_path).resolve(),Path(rebuilt_path).resolve()):
        raise FileExistsError(output)
    shutil.copyfile(base_path,output)
    with output.open('r+b') as target:
        target.seek(insertion);target.write(payload)
        target.write(b'\0'*(next_etoc-target.tell()))
        target.write(etoc_header);target.write(etoc)
        target.truncate()
        target.seek(16);target.write(header.data)
        target.seek(header.get('TocOffset')+16);target.write(toc.data)
    verify_metadata(base_path,output)
    check=cpk.load(str(output))
    for i in range(check.file_count):
        f=check.file_info(i);name=f.full_path.lower()
        if name==key:
            assert f.file_offset==insertion
            assert check.file_bytes(i)==rebuilt.file_bytes(next(j for j in range(rebuilt.file_count) if rebuilt.file_info(j).full_path.lower()==key))
        else:
            f0=old[name]
            assert (f.file_offset,f.file_size,f.extract_size)==(f0.file_offset,f0.file_size,f0.extract_size)
    del check,base,rebuilt
    gc.collect()


if __name__=='__main__':
    import sys
    for path in sys.argv[1:]:describe(path)
