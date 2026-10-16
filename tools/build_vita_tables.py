"""Adapters for native Vita tables and battle voice/message containers."""
import struct
from build_vita_bf import parse_bmd, replace_accents_safe, transplant_bmd, transplant_bf


def parse_table(data):
    blocks = []
    pos = 0
    while pos < len(data):
        if pos+4 > len(data):
            raise ValueError('Truncated table header')
        size = struct.unpack_from('<I', data, pos)[0]
        end = pos+4+size
        following = (end+15) & ~15
        if end > len(data) or following > len(data):
            raise ValueError('Table block outside file')
        blocks.append(data[pos+4:end])
        pos = following
    return blocks


def build_table(blocks):
    out = bytearray()
    for block in blocks:
        out += struct.pack('<I', len(block)) + block
        out += b'\0' * (-len(out) % 16)
    return bytes(out)


SHORTENED_LABELS = []


def localize_slots(vita, pc, vwidth, pwidth):
    if len(vita) % vwidth or len(pc) % pwidth or len(vita)//vwidth != len(pc)//pwidth:
        raise ValueError('Incompatible fixed-width text table')
    out = bytearray()
    for index in range(len(vita)//vwidth):
        source = pc[index*pwidth:(index+1)*pwidth]
        if b'\0' not in source:
            raise ValueError('Unterminated table label')
        label = replace_accents_safe(source.split(b'\0')[0])
        if len(label) >= vwidth:
            original = label
            # Keep glyph boundaries, and signal the shortened console label.
            tokens, pos = [], 0
            while pos < len(label):
                size = 2 if label[pos] >= 0x80 else 1
                tokens.append(label[pos:pos+size])
                pos += size
            label = b''
            for token in tokens:
                if len(label)+len(token) > vwidth-2:
                    break
                label += token
            label = label.rstrip()+b'.'
            SHORTENED_LABELS.append((index, original.hex(), label.hex()))
        out += label.ljust(vwidth, b'\0')
    return bytes(out)


def transplant_table(vita, pc, name):
    vb, pb = parse_table(vita), parse_table(pc)
    if len(vb) != len(pb):
        raise ValueError('Native and PC table block counts differ')
    result = list(vb)
    for i, (a, b) in enumerate(zip(vb, pb)):
        if a[8:12] == b'FLW0' and b[8:12] == b'FLW0':
            result[i] = transplant_bf(a, b)
        elif a[8:12] == b'MSG1' and b[8:12] == b'MSG1':
            result[i] = transplant_bmd(a, b)[0]
        elif name.lower().endswith('msg.tbl') and i < 4:
            # 32 arcana, 624 skills, 368 enemies and 256 Personae. The PC
            # expanded the skill and enemy name fields; Vita still uses 23/21.
            result[i] = localize_slots(a, b, (21,23,21,21)[i], (21,33,29,21)[i])
    return build_table(result)


def transplant_item_names(vita, pc):
    # EU PCSB00245: the binary item records precede 2560 names, 24 bytes each.
    count, start = 2560, 174112
    if len(vita) != start+count*24 or len(pc) != start+count*28 or vita[:start] != pc[:start]:
        raise ValueError('Unknown item table layout')
    return vita[:start]+localize_slots(vita[start:], pc[start:], 24, 28)


def parse_bvp(data):
    first = struct.unpack_from('<I', data, 4)[0]
    if first % 12 or first > len(data):
        raise ValueError('Invalid BVP directory')
    entries = []
    for pos in range(0, first, 12):
        kind, offset, size = struct.unpack_from('<III', data, pos)
        if offset+size > len(data):
            raise ValueError('BVP entry outside file')
        entries.append((kind, data[offset:offset+size]))
    return entries


def transplant_bvp(vita, pc):
    ve, pe = parse_bvp(vita), parse_bvp(pc)
    lookup = {}
    for _, data in pe:
        if data[8:12] == b'MSG1':
            dialogs = parse_bmd(data)['dialogs']
            lookup[tuple((d['name'],d['kind']) for d in dialogs)] = data
    out = bytearray(len(ve)*12)
    for i, (kind, data) in enumerate(ve):
        if data[8:12] == b'MSG1':
            key = tuple((d['name'],d['kind']) for d in parse_bmd(data)['dialogs'])
            if key in lookup:
                data = transplant_bmd(data, lookup[key])[0]
        # A zero directory entry is the end sentinel in the packed Vita BVPs.
        struct.pack_into('<III', out, i*12, kind, len(out) if data else 0, len(data))
        out += data
        out += b'\0' * (-len(out) % 16)
    return bytes(out)


def transplant_cmm_table(vita, pc, name):
    """Keep retail field widths and gameplay metadata in community tables."""
    name=name.lower().rsplit('/',1)[-1]
    if len(vita)<8 or len(pc)<8:return vita
    vs,count=struct.unpack_from('<II',vita)
    ps,pcount=struct.unpack_from('<II',pc)
    if count!=pcount or 8+vs>len(vita) or 8+ps>len(pc):
        raise ValueError('Incompatible community table')
    out=bytearray(vita)
    if name in ('cmmpc_param_help.dat','cmmpc_param_name.dat'):
        out[8:8+vs]=localize_slots(vita[8:8+vs],pc[8:8+ps],14,17)
    elif name=='cmmbooktable.dat':
        if vs!=count*84 or ps!=count*116:raise ValueError('Unknown book table layout')
        for i in range(count):
            vo,po=8+i*84,8+i*116
            out[vo+12:vo+34]=localize_slots(vita[vo+12:vo+34],pc[po+12:po+45],22,33)
            out[vo+34:vo+84]=localize_slots(vita[vo+34:vo+84],pc[po+45:po+116],50,71)
    elif name=='cmmcommunitymaxwork.dat':
        if vs!=count*66 or ps!=count*66:raise ValueError('Unknown max work layout')
        for i in range(count):
            off=8+i*66
            out[off:off+64]=localize_slots(vita[off:off+64],pc[off:off+64],64,64)
    elif name in {'cmmname.dat','cmmplace.dat','cmmarcanasphelp.dat','cmmclubname.dat',
                  'cmmmailorder_text.dat','cmmmailorder_name.dat','cmmmembername.dat','cmmfixstring.dat'}:
        if not count or vs%count or ps%count:raise ValueError('Unknown community text stride')
        out[8:8+vs]=localize_slots(vita[8:8+vs],pc[8:8+ps],vs//count,ps//count)
    else:return vita
    if len(out)!=len(vita):raise ValueError('Community table grew')
    return bytes(out)
