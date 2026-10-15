import struct
import cricodecs.cpk as cpk

def parse_pac(data):
    pos = 0; files = {}; order = []
    while pos < len(data):
        if pos + 256 > len(data): break
        h = data[pos:pos+256]
        nb = h[:252].split(b'\x00')[0].decode('latin1', errors='ignore')
        sz = struct.unpack('<I', h[252:256])[0]
        files[nb] = data[pos+256:pos+256+sz]
        order.append(nb)
        pos += 256 + sz + (64 - ((256+sz)%64))%64
    return files, order

def parse_arc(data):
    cnt = struct.unpack('<I', data[:4])[0]; pos = 4; files = {}
    for i in range(cnt):
        name = data[pos:pos+32].split(b'\x00')[0].decode('latin1')
        sz = struct.unpack('<I', data[pos+32:pos+36])[0]
        files[name] = data[pos+36:pos+36+sz]; pos += 36 + sz
    return files

def build_arc(files_dict):
    out = bytearray()
    out += struct.pack('<I', len(files_dict))
    for name, b in files_dict.items():
        nb = name.encode('latin1').ljust(32, b'\x00')
        out += nb
        out += len(b).to_bytes(4, 'little')
        out += b
    return bytes(out)

def build_localized_fcltable(vita_cpk_path, pc_cpk_path):
    print("Building localized fclTable.bin for PS Vita...")
    vita = cpk.load(vita_cpk_path)
    pc = cpk.load(pc_cpk_path)

    def get_file(c, target):
        for i in range(c.file_count):
            if c.file_info(i).filename == target: return c.file_bytes(i)

    v_init_free = get_file(vita, 'init_free.bin')
    p_init_free = get_file(pc, 'init_free.bin')

    vf = parse_arc(parse_pac(v_init_free)[0]['init/fclTable.bin'])
    pf = parse_arc(parse_pac(p_init_free)[0]['init/fclTable.bin'])

    new_fcl = {}
    for k, v in vf.items():
        new_fcl[k] = v

    for name in vf:
        if name not in pf:
            continue
        vd = vf[name]
        pd = pf[name]
        vh = struct.unpack('<4I', vd[:16])
        ph = struct.unpack('<4I', pd[:16])
        if vh[1] == 0:
            continue
        v_esz = vh[0] // vh[1]
        p_esz = ph[0] // ph[1] if ph[1] > 0 else 0

        # Create bytearray copy of Vita file
        new_d = bytearray(vd)

        if v_esz == 34 and p_esz == 44:
            for i in range(vh[1]):
                if i < ph[1]:
                    p_str = pd[16 + i*44 : 16 + (i+1)*44].split(b'\x00')[0]
                    # Special overrides for strings that exceeded 33 bytes
                    if name == 'fclSearchText.ftd' and i == 1:
                        p_str = b'Nessun candidato alla fusione'
                    elif name == 'fclUserCmmHelp.ftd' and i == 0:
                        p_str = b'Modifica le parole del messaggio'
                    p_str_fit = p_str[:33].ljust(34, b'\x00')
                    new_d[16 + i*34 : 16 + (i+1)*34] = p_str_fit

        elif v_esz == 48 and p_esz == 56:
            if name == 'fclHelpTable_SKLCARD2.ftd':
                # Entries 3, 4, 5 take PC entries 0, 1, 2
                for i in range(3):
                    p_str = pd[16 + i*56 + 8 : 16 + (i+1)*56 - 4].split(b'\x00')[0]
                    p_str_fit = p_str[:33].ljust(34, b'\x00')
                    new_d[16 + (i+3)*48 + 8 : 16 + (i+3)*48 + 8 + 34] = p_str_fit
            else:
                for i in range(vh[1]):
                    if i < ph[1]:
                        p_str = pd[16 + i*56 + 8 : 16 + (i+1)*56 - 4].split(b'\x00')[0]
                        p_str_fit = p_str[:33].ljust(34, b'\x00')
                        new_d[16 + i*48 + 8 : 16 + i*48 + 8 + 34] = p_str_fit

        elif v_esz == 102 and p_esz == 132:
            for i in range(vh[1]):
                if i < ph[1]:
                    p_str = pd[16 + i*132 : 16 + (i+1)*132].split(b'\x00')[0]
                    p_str_fit = p_str[:101].ljust(102, b'\x00')
                    new_d[16 + i*102 : 16 + (i+1)*102] = p_str_fit

        elif len(vd) == len(pd):
            # Same entry size and length: can copy PC's body directly!
            new_d = bytearray(pd)

        assert len(new_d) == len(vd), f"Length mismatch in {name}: {len(new_d)} vs {len(vd)}"
        new_fcl[name] = bytes(new_d)

    out_arc = build_arc(new_fcl)
    print(f"Built localized fclTable.bin: {len(out_arc)} bytes ({len(new_fcl)} files).")
    return out_arc

if __name__ == '__main__':
    arc_data = build_localized_fcltable('clean_vita_data.cpk', 'Persona 4 Golden/data_it.cpk')
    with open('test_localized_fclTable.bin', 'wb') as f:
        f.write(arc_data)
    print("Saved test_localized_fclTable.bin successfully!")
