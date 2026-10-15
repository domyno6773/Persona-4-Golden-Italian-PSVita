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
    if not any(seq in data for seq in ACCENT_MAP):
        return data
    out = bytearray(data)
    for seq, repl in ACCENT_MAP.items():
        pos = 0
        while True:
            idx = out.find(seq, pos)
            if idx == -1:
                break
            w_start = max(0, idx - 30)
            w_end = min(len(out), idx + 32)
            window = out[w_start:w_end]
            ascii_count = sum(1 for b in window if (32 <= b <= 126) or b == 10)
            if ascii_count >= 5:
                out[idx : idx + 2] = repl
            pos = idx + 2
    return bytes(out)

def encode_reloc(addressLocations, addressBaseOffset=0):
    ADDRESS_SIZE = 4
    SEQ_LOOP = 0xF8
    SEQ_BASE = 0x07
    SEQ_BASE_NUM_LOOP = 2
    SEQ_MAX_NUM_LOOP = 33

    sequences = {}
    i = 0
    while i < len(addressLocations):
        if i + 1 == len(addressLocations):
            break
        if addressLocations[i + 1] - addressLocations[i] == ADDRESS_SIZE:
            start_idx = i
            count = 2
            i += 1
            while i + 1 < len(addressLocations) and (addressLocations[i + 1] - addressLocations[i] == ADDRESS_SIZE):
                count += 1
                i += 1
            if count > 2:
                sequences[start_idx] = count
        i += 1

    relocationTable = bytearray()
    prevRelocSum = 0

    def encode_address(reloc):
        nonlocal prevRelocSum
        if (reloc & 0x01) == 0:
            newReloc = reloc >> 1
            if newReloc <= 0xFF:
                relocationTable.append(newReloc)
            else:
                relocLo = (reloc & 0xFF) + 1
                relocHi = (reloc & 0xFF00) >> 8
                relocationTable.append(relocLo)
                relocationTable.append(relocHi)
        else:
            relocLo = (reloc & 0xFF) + 1
            relocHi = (reloc & 0xFF00) >> 8
            relocationTable.append(relocLo)
            relocationTable.append(relocHi)
        prevRelocSum += reloc

    addr_idx = 0
    while addr_idx < len(addressLocations):
        if addr_idx not in sequences:
            reloc = addressLocations[addr_idx] - prevRelocSum - addressBaseOffset
            encode_address(reloc)
            addr_idx += 1
        else:
            seq_count = sequences[addr_idx]
            reloc = addressLocations[addr_idx] - prevRelocSum - addressBaseOffset
            encode_address(reloc)
            num_remaining = seq_count - 1
            while num_remaining > 0:
                to_add = min(num_remaining, SEQ_MAX_NUM_LOOP)
                loop = to_add - SEQ_BASE_NUM_LOOP
                code = (loop << 3) | SEQ_BASE
                relocationTable.append(code)
                addr_idx += to_add
                prevRelocSum += to_add * ADDRESS_SIZE
                num_remaining -= to_add
            addr_idx += 1

    return bytes(relocationTable)

def parse_bmd(bmd_bytes):
    if len(bmd_bytes) < 32:
        return {'user_id': 0, 'version': 2, 'dialogs': [], 'speakers': []}
    file_type, fmt, user_id, file_size = struct.unpack('<BBhI', bmd_bytes[:8])
    magic = bmd_bytes[8:12]
    ext_size, rel_off, rel_sz, dlg_cnt = struct.unpack('<IIII', bmd_bytes[12:28])
    is_rel, version = struct.unpack('<hh', bmd_bytes[28:32])

    dialogs = []
    for i in range(dlg_cnt):
        kind, offset = struct.unpack('<II', bmd_bytes[32 + i*8 : 32 + (i+1)*8])
        dlg_pos = 32 + offset
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

    spk_hdr_pos = 32 + dlg_cnt * 8
    spk_arr_off, spk_cnt, ext_data_off, spk_res = struct.unpack('<IIII', bmd_bytes[spk_hdr_pos : spk_hdr_pos + 16])
    
    speakers = []
    if spk_arr_off != 0 and spk_cnt > 0:
        spk_offsets = list(struct.unpack(f'<{spk_cnt}I', bmd_bytes[32 + spk_arr_off : 32 + spk_arr_off + spk_cnt * 4]))
        for off in spk_offsets:
            p = 32 + off
            end = bmd_bytes.find(b'\x00', p)
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
        if name not in pc_dialogs_by_name:
            pc_dialogs_by_name[name] = d

    new_dialogs = []
    transplanted_count = 0
    kept_count = 0

    for vd in v_parsed['dialogs']:
        v_name = vd['name']
        if v_name in pc_dialogs_by_name:
            pd = pc_dialogs_by_name[v_name]
            new_d = dict(vd)
            new_d['kind'] = pd['kind']
            new_d['text_buf'] = replace_accents_safe(pd['text_buf'])
            
            p_dlg_off = pd.get('dlg_offset', 0)
            if pd['kind'] == 0:
                new_d['page_count'] = pd['page_count']
                new_d['speaker_id'] = pd['speaker_id']
                new_d['page_addrs'] = [pa - p_dlg_off for pa in pd['page_addrs']]
            elif pd['kind'] == 1:
                new_d['option_count'] = pd['option_count']
                new_d['pattern'] = pd['pattern']
                new_d['ext'] = pd.get('ext', 0)
                new_d['reserved'] = pd.get('reserved', 0)
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

    new_speakers = []
    if len(p_parsed['speakers']) == len(v_parsed['speakers']):
        for s in p_parsed['speakers']:
            new_speakers.append(replace_accents_safe(s))
    else:
        new_speakers = v_parsed['speakers']

    loc_bmd = build_bmd_relative(new_dialogs, new_speakers, v_parsed['user_id'], v_parsed['version'])
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

            curr_pos += 4
            curr_pos += len(d['text_buf'])

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

def transplant_bf(v_bf_bytes, p_bf_bytes):
    if len(v_bf_bytes) < 32 or v_bf_bytes[8:12] != b'FLW0':
        return v_bf_bytes
    if len(p_bf_bytes) < 32 or p_bf_bytes[8:12] != b'FLW0':
        return v_bf_bytes

    v_sec_cnt = struct.unpack('<I', v_bf_bytes[0x10:0x14])[0]
    p_sec_cnt = struct.unpack('<I', p_bf_bytes[0x10:0x14])[0]

    v_sec3_idx = -1
    v_sec4_idx = -1
    for i in range(v_sec_cnt):
        st = struct.unpack('<I', v_bf_bytes[0x20 + i*16 : 0x20 + i*16 + 4])[0]
        if st == 3: v_sec3_idx = i
        elif st == 4: v_sec4_idx = i

    p_sec3_idx = -1
    for i in range(p_sec_cnt):
        st = struct.unpack('<I', p_bf_bytes[0x20 + i*16 : 0x20 + i*16 + 4])[0]
        if st == 3: p_sec3_idx = i

    if v_sec3_idx == -1 or p_sec3_idx == -1:
        return v_bf_bytes

    _, _, v_s3_cnt, v_s3_off = struct.unpack('<IIII', v_bf_bytes[0x20 + v_sec3_idx*16 : 0x20 + (v_sec3_idx+1)*16])
    v_bmd = v_bf_bytes[v_s3_off : v_s3_off + v_s3_cnt]

    _, _, p_s3_cnt, p_s3_off = struct.unpack('<IIII', p_bf_bytes[0x20 + p_sec3_idx*16 : 0x20 + (p_sec3_idx+1)*16])
    p_bmd = p_bf_bytes[p_s3_off : p_s3_off + p_s3_cnt]

    if len(v_bmd) == 0 or len(p_bmd) == 0:
        return v_bf_bytes

    loc_bmd, trans_cnt, kept_cnt = transplant_bmd(v_bmd, p_bmd)

    v_sec4_data = b''
    if v_sec4_idx != -1:
        _, _, v_s4_cnt, v_s4_off = struct.unpack('<IIII', v_bf_bytes[0x20 + v_sec4_idx*16 : 0x20 + (v_sec4_idx+1)*16])
        v_sec4_data = v_bf_bytes[v_s4_off : v_s4_off + v_s4_cnt]

    out_hdr = bytearray(v_bf_bytes[:v_s3_off])
    out_hdr[0x20 + v_sec3_idx*16 + 8 : 0x20 + v_sec3_idx*16 + 12] = struct.pack('<I', len(loc_bmd))

    new_sec4_off = v_s3_off + len(loc_bmd)
    if v_sec4_idx != -1:
        out_hdr[0x20 + v_sec4_idx*16 + 12 : 0x20 + v_sec4_idx*16 + 16] = struct.pack('<I', new_sec4_off)

    new_file_sz = new_sec4_off + len(v_sec4_data)
    out_hdr[4:8] = struct.pack('<I', new_file_sz)

    out = bytearray(out_hdr)
    out += loc_bmd
    out += v_sec4_data

    pad = (64 - (len(out) % 64)) % 64
    out += b'\x00' * pad

    return bytes(out)
