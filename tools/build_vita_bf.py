import struct

ACCENT_MAP = {
    b'\x9c\xda': b"a'", # à
    b'\x9c\xe2': b"e'", # è
    b'\x9c\xe3': b"e'", # é
    b'\x9c\xe6': b"i'", # ì
    b'\x9c\xec': b"o'", # ò
    b'\x9c\xf2': b"u'", # ù
    b'\x9c\xc0': b"A'", # À
    b'\x9c\xc3': b"E'", # È
    b'\x9c\xc4': b"E'", # É
    b'\x9c\xc7': b"I'", # Ì
}

def replace_accents_safe(data):
    """Convert glyphs in a text buffer without changing function arguments."""
    out = bytearray()
    pos = 0
    while pos < len(data):
        first = data[pos]
        if 0xf0 <= first <= 0xff:
            size = 2 * (first & 15)
            if size < 2 or pos + size > len(data):
                raise ValueError('Invalid message function')
            out += data[pos:pos+size]
        elif first >= 0x80:
            size = 2
            glyph = data[pos:pos+2]
            if len(glyph) != 2:
                raise ValueError('Truncated message glyph')
            out += ACCENT_MAP.get(glyph, glyph)
        else:
            size = 1
            out.append(first)
        pos += size
    return bytes(out)

def encode_reloc(addressLocations, addressBaseOffset=0):
    # A delta for every pointer avoids the old run-length encoder's invalid
    # one-address remainder after runs of 34, 67, ... additional pointers.
    out = bytearray()
    previous = addressBaseOffset
    for address in addressLocations:
        delta = address - previous
        if delta < 0 or delta % 4 or delta > 0xfffc:
            raise ValueError(f'Unrepresentable relocation delta: {delta}')
        if delta <= 0x1fc:
            out.append(delta >> 1)
        else:
            out.extend(((delta & 255) + 1, delta >> 8))
        previous = address
    return bytes(out)

def parse_bmd(bmd_bytes):
    if len(bmd_bytes) < 32 or bmd_bytes[8:12] != b'MSG1':
        raise ValueError('Expected MSG1 message script')
    file_type, fmt, user_id, file_size = struct.unpack('<BBhI', bmd_bytes[:8])
    magic = bmd_bytes[8:12]
    ext_size, rel_off, rel_sz, dlg_cnt = struct.unpack('<IIII', bmd_bytes[12:28])
    is_rel, version = struct.unpack('<hh', bmd_bytes[28:32])
    if file_size > len(bmd_bytes) or 48 + dlg_cnt*8 > file_size:
        raise ValueError('Invalid MSG1 size or dialog table')
    if is_rel or ext_size:
        raise ValueError('Relocated or extended MSG1 is unsupported')

    dialogs = []
    for i in range(dlg_cnt):
        kind, offset = struct.unpack('<II', bmd_bytes[32 + i*8 : 32 + (i+1)*8])
        dlg_pos = 32 + offset
        if kind not in (0, 1) or dlg_pos < 48+dlg_cnt*8 or dlg_pos+28 > file_size:
            raise ValueError('Invalid dialog kind or offset')
        if kind == 0:
            name = bmd_bytes[dlg_pos : dlg_pos + 24].split(b'\x00')[0].decode('latin1', errors='ignore')
            page_count, speaker_id = struct.unpack('<hH', bmd_bytes[dlg_pos + 24 : dlg_pos + 28])
            pos = dlg_pos + 28
            page_addrs = []
            if page_count > 0:
                page_addrs = list(struct.unpack(f'<{page_count}I', bmd_bytes[pos : pos + page_count*4]))
                pos += page_count * 4
                text_buf_sz = struct.unpack('<I', bmd_bytes[pos : pos + 4])[0]
                pos += 4
                text_buf = bmd_bytes[pos : pos + text_buf_sz]
            else:
                text_buf = b''
            dialogs.append({
                'kind': 0,
                'name': name,
                'page_count': page_count,
                'speaker_id': speaker_id,
                'page_addrs': page_addrs,
                'text_buf': text_buf,
                'dlg_offset': offset,
            })

        elif kind == 1:
            name = bmd_bytes[dlg_pos : dlg_pos + 24].split(b'\x00')[0].decode('latin1', errors='ignore')
            ext, opt_cnt, pattern, reserved = struct.unpack('<hhhh', bmd_bytes[dlg_pos + 24 : dlg_pos + 32])
            pos = dlg_pos + 32
            opt_addrs = list(struct.unpack(f'<{opt_cnt}I', bmd_bytes[pos : pos + opt_cnt*4]))
            pos += opt_cnt * 4
            text_buf_sz = struct.unpack('<I', bmd_bytes[pos : pos + 4])[0]
            pos += 4
            text_buf = bmd_bytes[pos : pos + text_buf_sz]
            dialogs.append({
                'kind': 1,
                'name': name,
                'ext': ext,
                'option_count': opt_cnt,
                'pattern': pattern,
                'reserved': reserved,
                'opt_addrs': opt_addrs,
                'text_buf': text_buf,
                'dlg_offset': offset,
            })

        d = dialogs[-1]
        addresses = d.get('page_addrs', d.get('opt_addrs', []))
        if addresses:
            text_start = offset + (32 if kind == 0 else 36) + len(addresses)*4
            if any(not text_start <= a < text_start+len(d['text_buf']) for a in addresses):
                raise ValueError('Message page pointer outside text buffer')

    spk_hdr_pos = 32 + dlg_cnt * 8
    spk_arr_off, spk_cnt, ext_data_off, spk_res = struct.unpack('<IIII', bmd_bytes[spk_hdr_pos : spk_hdr_pos + 16])
    
    speakers = []
    if spk_arr_off != 0 and spk_cnt > 0:
        spk_offsets = list(struct.unpack(f'<{spk_cnt}I', bmd_bytes[32 + spk_arr_off : 32 + spk_arr_off + spk_cnt * 4]))
        for off in spk_offsets:
            p = 32 + off
            end = bmd_bytes.find(b'\x00', p)
            if end < p or end >= file_size:
                raise ValueError('Invalid speaker string')
            speakers.append(bmd_bytes[p:end])

    return {
        'user_id': user_id,
        'version': version,
        'dialogs': dialogs,
        'speakers': speakers,
    }

def transplant_bmd(vita_bmd_bytes, pc_bmd_bytes):
    if not vita_bmd_bytes or len(vita_bmd_bytes) < 32:
        return vita_bmd_bytes, 0, 0
    if not pc_bmd_bytes or len(pc_bmd_bytes) < 32:
        return vita_bmd_bytes, 0, 0

    v_parsed = parse_bmd(vita_bmd_bytes)
    p_parsed = parse_bmd(pc_bmd_bytes)

    pc_dialogs_by_name = {}
    for d in p_parsed['dialogs']:
        name = d['name']
        pc_dialogs_by_name.setdefault((name, d['kind']), []).append(d)

    new_dialogs = []
    transplanted_count = 0
    kept_count = 0
    new_speakers = list(v_parsed['speakers'])

    for vd in v_parsed['dialogs']:
        v_name = vd['name']
        candidates = pc_dialogs_by_name.get((v_name, vd['kind']), [])
        pd = candidates.pop(0) if candidates else None
        # Native scripts branch on the selection's original option numbers.
        if pd and vd['kind'] == 1 and vd['option_count'] != pd['option_count']:
            pd = None
        if pd:
            new_d = dict(vd)
            new_d['kind'] = pd['kind']
            new_d['text_buf'] = replace_accents_safe(pd['text_buf'])
            
            p_dlg_off = pd.get('dlg_offset', 0)
            if pd['kind'] == 0:
                new_d['page_count'] = pd['page_count']
                # Speaker indices belong to the Vita table, including variable
                # speakers (0x8000+) and the no-speaker sentinel (0xffff).
                vs, ps = vd['speaker_id'], pd['speaker_id']
                if vs < len(new_speakers) and ps < len(p_parsed['speakers']):
                    new_speakers[vs] = replace_accents_safe(p_parsed['speakers'][ps])
                new_d['page_addrs'] = [pa - p_dlg_off for pa in pd['page_addrs']]
            elif pd['kind'] == 1:
                new_d['option_count'] = pd['option_count']
                new_d['opt_addrs'] = [oa - p_dlg_off for oa in pd['opt_addrs']]

            new_dialogs.append(new_d)
            transplanted_count += 1
        else:
            new_d = dict(vd)
            v_dlg_off = vd.get('dlg_offset', 0)
            if vd['kind'] == 0:
                new_d['page_addrs'] = [pa - v_dlg_off for pa in vd['page_addrs']]
            else:
                new_d['opt_addrs'] = [oa - v_dlg_off for oa in vd['opt_addrs']]
            new_dialogs.append(new_d)
            kept_count += 1

    loc_bmd = build_bmd_relative(new_dialogs, new_speakers, v_parsed['user_id'], v_parsed['version'])
    parse_bmd(loc_bmd)
    return loc_bmd, transplanted_count, kept_count

def build_bmd_relative(dialogs, speakers, user_id=0, version=2):
    dlg_cnt = len(dialogs)
    spk_cnt = len(speakers)

    address_locations = []
    
    curr_pos = 32
    for _ in range(dlg_cnt):
        curr_pos += 4
        address_locations.append(curr_pos)
        curr_pos += 4

    address_locations.append(curr_pos)
    curr_pos += 16

    dlg_offsets = []
    built_dialogs_data = []

    for d in dialogs:
        if curr_pos % 4 != 0:
            curr_pos += (4 - (curr_pos % 4))
        
        dlg_addr = curr_pos - 32
        dlg_offsets.append(dlg_addr)

        if d['kind'] == 0:
            name_bytes = d['name'].encode('latin1').ljust(24, b'\x00')
            curr_pos += 24
            page_cnt = d['page_count']
            curr_pos += 4
            
            new_page_addrs = []
            for rel in d['page_addrs']:
                address_locations.append(curr_pos)
                curr_pos += 4
                new_page_addrs.append(dlg_addr + rel)

            if page_cnt > 0:
                curr_pos += 4 + len(d['text_buf'])

            data = bytearray()
            data += name_bytes
            data += struct.pack('<hH', page_cnt, d['speaker_id'])
            if page_cnt > 0:
                data += struct.pack(f'<{page_cnt}I', *new_page_addrs)
                data += struct.pack('<I', len(d['text_buf']))
                data += d['text_buf']
            built_dialogs_data.append(bytes(data))

        elif d['kind'] == 1:
            name_bytes = d['name'].encode('latin1').ljust(24, b'\x00')
            curr_pos += 24
            opt_cnt = d['option_count']
            curr_pos += 8

            new_opt_addrs = []
            for rel in d['opt_addrs']:
                address_locations.append(curr_pos)
                curr_pos += 4
                new_opt_addrs.append(dlg_addr + rel)

            curr_pos += 4
            curr_pos += len(d['text_buf'])

            data = bytearray()
            data += name_bytes
            data += struct.pack('<hhhh', d.get('ext', 0), opt_cnt, d['pattern'], d.get('reserved', 0))
            data += struct.pack(f'<{opt_cnt}I', *new_opt_addrs)
            data += struct.pack('<I', len(d['text_buf']))
            data += d['text_buf']
            built_dialogs_data.append(bytes(data))

    if curr_pos % 4 != 0:
        curr_pos += (4 - (curr_pos % 4))
    
    spk_arr_offset = curr_pos - 32
    for _ in range(spk_cnt):
        address_locations.append(curr_pos)
        curr_pos += 4

    spk_offsets = []
    built_spk_names = bytearray()
    for s in speakers:
        spk_offsets.append(curr_pos - 32)
        sb = s + b'\x00'
        built_spk_names += sb
        curr_pos += len(sb)

    if curr_pos % 4 != 0:
        curr_pos += (4 - (curr_pos % 4))
    
    reloc_offset = curr_pos
    reloc_bytes = encode_reloc(address_locations, 32)
    reloc_sz = len(reloc_bytes)
    curr_pos += reloc_sz

    total_file_size = curr_pos

    out = bytearray()
    out += struct.pack('<BBhI4sIIIIhh',
        7, 0, user_id, total_file_size,
        b'MSG1', 0, reloc_offset, reloc_sz,
        dlg_cnt, 0, version
    )

    for i in range(dlg_cnt):
        out += struct.pack('<II', dialogs[i]['kind'], dlg_offsets[i])

    out += struct.pack('<IIII', spk_arr_offset, spk_cnt, 0, 0)

    for i in range(dlg_cnt):
        target_pos = 32 + dlg_offsets[i]
        pad = target_pos - len(out)
        if pad > 0:
            out += b'\x00' * pad
        out += built_dialogs_data[i]

    target_pos = 32 + spk_arr_offset
    pad = target_pos - len(out)
    if pad > 0:
        out += b'\x00' * pad
    for off in spk_offsets:
        out += struct.pack('<I', off)

    out += built_spk_names

    target_pos = reloc_offset
    pad = target_pos - len(out)
    if pad > 0:
        out += b'\x00' * pad
    out += reloc_bytes

    return bytes(out)

def read_sections(data, magic):
    if len(data) < 32 or data[8:12] != magic:
        raise ValueError(f'Expected {magic!r} container')
    count = struct.unpack_from('<I', data, 16)[0]
    if 32+count*16 > len(data):
        raise ValueError('Section table outside file')
    result = [struct.unpack_from('<IIII', data, 32+i*16) for i in range(count)]
    for _, size, n, off in result:
        if off+size*n > len(data):
            raise ValueError('Section outside file')
    return result


def transplant_section(vita, pc, magic, message_kind):
    """Leave native absolute pointers intact, even inside opaque PMD1 chunks.

    Reuse the original message slot when it fits. Otherwise append an aligned
    message section and update its descriptor; no other section moves.
    """
    vs = read_sections(vita, magic)
    ps = read_sections(pc, magic)
    for index, (kind, size, count, offset) in enumerate(vs):
        if kind != message_kind or not size*count:
            continue
        source = next((s for s in ps if s[0] == message_kind), None)
        if source is None or not source[1]*source[2]:
            return vita
        _, ss, sc, so = source
        localized, _, _ = transplant_bmd(vita[offset:offset+size*count], pc[so:so+ss*sc])
        out = bytearray(vita)
        padded = localized + b'\0' * (-len(localized) % 16)
        if len(padded) <= size*count:
            out[offset:offset+size*count] = padded.ljust(size*count, b'\0')
            target = offset
        else:
            out.extend(b'\0' * (-len(out) % 16))
            target = len(out)
            out.extend(padded)
        descriptor = 32+index*16
        if magic == b'FLW0':
            struct.pack_into('<IIII', out, descriptor, kind, 1, len(localized), target)
        else:
            struct.pack_into('<IIII', out, descriptor, kind, len(padded), 1, target)
        struct.pack_into('<I', out, 4, len(out))
        return bytes(out)
    return vita


def transplant_bf(vita, pc):
    vs, ps = read_sections(vita, b'FLW0'), read_sections(pc, b'FLW0')
    vm = next((s for s in vs if s[0] == 3), None)
    pm = next((s for s in ps if s[0] == 3), None)
    strings = next((s for s in vs if s[0] == 4), None)
    if not vm or not pm or not vm[1]*vm[2] or not pm[1]*pm[2]:
        return vita
    if not strings or strings[3] != vm[3]+vm[1]*vm[2]:
        raise ValueError('Unsupported BF section order')
    _,size,count,offset=vm
    _,psize,pcount,poffset=pm
    localized,_,_=transplant_bmd(vita[offset:offset+size*count],pc[poffset:poffset+psize*pcount])
    # Retail Vita BFs put messages before the string section and declare the
    # beginning of that section as FileSize. Do not append duplicate messages
    # or change that retail size convention.
    out=bytearray(vita[:offset])+localized
    string_start=len(out)
    out += vita[strings[3]:strings[3]+strings[1]*strings[2]]
    for index,section in enumerate(vs):
        if section[0]==3:struct.pack_into('<IIII',out,32+index*16,3,1,len(localized),offset)
        elif section[0]==4:struct.pack_into('<IIII',out,32+index*16,*strings[:3],string_start)
    struct.pack_into('<I',out,4,string_start)
    # Archive-level padding is supplied by its enclosing container, not by BF.
    return bytes(out)


def transplant_pm1(vita, pc):
    # This retail event omits a final 16-byte record/padding present in the
    # declared size on both platforms. Materialize it before appending data.
    def complete(data):
        declared = struct.unpack_from('<I', data, 4)[0]
        if len(data) < declared <= len(data)+16:
            return data.ljust(declared, b'\0')
        return data
    vita, pc = complete(vita), complete(pc)
    return transplant_section(vita, pc, b'PMD1', 6)
