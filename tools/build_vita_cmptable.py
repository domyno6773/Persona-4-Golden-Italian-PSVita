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

def build_ctd(entries):
    # Header: (count * 64, count, 0, 0)
    # count * 64 bytes
    # Footer: (count * 64, count, 0, 0)
    cnt = len(entries)
    data_size = cnt * 64
    hdr = struct.pack('<4I', data_size, cnt, 0, 0)
    body = bytearray()
    for e in entries:
        if isinstance(e, str):
            # Encode in Atlus CP1252 / Shift-JIS
            # For pure ascii or standard accented
            eb = e.encode('cp1252', errors='ignore')
        elif isinstance(e, bytes):
            eb = e
        else:
            eb = bytes(e)
        body += eb[:63].ljust(64, b'\x00')
    ftr = struct.pack('<4I', data_size, cnt, 0, 0)
    return hdr + bytes(body) + ftr

def build_localized_cmptable(vita_cpk_path, pc_cpk_path):
    print("Building localized cmpTable.bin for PS Vita...")
    vita = cpk.load(vita_cpk_path)
    pc = cpk.load(pc_cpk_path)

    def get_file(c, target):
        for i in range(c.file_count):
            if c.file_info(i).filename == target: return c.file_bytes(i)

    v_init_free = get_file(vita, 'init_free.bin')
    p_init_free = get_file(pc, 'init_free.bin')

    v_cmp = parse_arc(parse_pac(v_init_free)[0]['init/cmpTable.bin'])
    p_cmp = parse_arc(parse_pac(p_init_free)[0]['init/cmpTable.bin'])

    new_cmp = {}
    for k, v in v_cmp.items():
        new_cmp[k] = v

    # 1. cmpConfigItem.ctd (10 entries x 64)
    # [0] Confirm
    # [1] Voiced Dialogue
    # [2] Auto-Advance
    # [3] Cursor Memory
    # [4] Tactics Memory
    # [5] Persona Memory
    # [6] Invert Camera
    # [7] Network Functions
    # [8] TV Update Notifier
    # [9] Restrict Connection
    pc_items = p_cmp['cmpConfigItem.ctd']
    def get_pc_item(idx):
        return pc_items[16 + idx*128 : 16 + (idx+1)*128].split(b'\x00')[0]

    config_items = [
        get_pc_item(0),   # Conferma
        get_pc_item(4),   # Dialoghi
        get_pc_item(8),   # Testo autom.
        get_pc_item(9),   # Memorizza posiz. cursore
        get_pc_item(10),  # Memorizza ordine battaglia
        get_pc_item(11),  # Memorizza Persona equip.
        get_pc_item(13),  # Visuale invertita
        get_pc_item(15),  # Funzionalit\x9c\xda di rete
        get_pc_item(12),  # Notifica Guida TV
        b'Limita connessione' # Restrict Connection
    ]
    new_cmp['cmpConfigItem.ctd'] = build_ctd(config_items)

    # 2. cmpConfigHelp.ctd (10 entries x 64)
    pc_helps = p_cmp['cmpConfigHelp.ctd']
    def get_pc_help(idx):
        return pc_helps[16 + idx*128 : 16 + (idx+1)*128].split(b'\x00')[0]

    config_helps = [
        get_pc_help(0),   # Applica le impostazioni modificate
        get_pc_help(4),   # Riproduci le voci a tempo con il testo
        get_pc_help(8),   # Fai avanzare autom. il testo a tempo con le voci
        get_pc_help(9),   # Ricorda l'ultima posizione del cursore in battaglia
        get_pc_help(10),  # Ricorda gli ordini selezionati in precedenza in battaglia
        get_pc_help(11),  # Ricorda la Persona equipaggiata a fine battaglia
        get_pc_help(13),  # Inverti i comandi della visuale
        get_pc_help(15),  # Attiva funzionalit\x9c\xda che usano la connessione di rete
        get_pc_help(12),  # Notifica automaticamente gli aggiornamenti della Guida TV
        b'Usa solo il Wi-Fi per la connessione di rete' # Use only Wi-fi when connecting to a network
    ]
    new_cmp['cmpConfigHelp.ctd'] = build_ctd(config_helps)

    # 3. cmpSystemMenu.ctd (6 entries x 64)
    # [0] Quests -> Missioni (PC 0)
    # [1] Settings -> Impostazioni (PC 1)
    # [2] Change Difficulty -> Cambia difficolt\x9c\xda (PC 2)
    # [3] Delete Data -> Elimina dati (PC 4)
    # [4] Load Data -> Carica dati (PC 5)
    # [5] Return to Title -> Torna alla schermata iniziale (PC 6)
    pc_sys_menu = p_cmp['cmpSystemMenu.ctd']
    def get_pc_sys_menu(idx):
        return pc_sys_menu[16 + idx*128 : 16 + (idx+1)*128].split(b'\x00')[0]
    sys_menu = [
        get_pc_sys_menu(0),
        get_pc_sys_menu(1),
        get_pc_sys_menu(2),
        get_pc_sys_menu(4),
        get_pc_sys_menu(5),
        get_pc_sys_menu(6)
    ]
    new_cmp['cmpSystemMenu.ctd'] = build_ctd(sys_menu)

    # 4. cmpSystemHelp.ctd (7 entries x 64)
    pc_sys_help = p_cmp['cmpSystemHelp.ctd']
    def get_pc_sys_help(idx):
        return pc_sys_help[16 + idx*128 : 16 + (idx+1)*128].split(b'\x00')[0]
    sys_help = [
        get_pc_sys_help(0),
        get_pc_sys_help(1),
        get_pc_sys_help(2),
        get_pc_sys_help(4),
        get_pc_sys_help(5),
        get_pc_sys_help(6),
        get_pc_sys_help(8)
    ]
    new_cmp['cmpSystemHelp.ctd'] = build_ctd(sys_help)

    # 5. cmpItemType.ctd (8 entries x 64)
    pc_item_type = p_cmp['cmpItemType.ctd']
    item_type = [pc_item_type[16 + i*128 : 16 + (i+1)*128].split(b'\x00')[0] for i in range(8)]
    new_cmp['cmpItemType.ctd'] = build_ctd(item_type)

    # 6. cmpEquipParam.ctd (5 entries x 64)
    pc_equip_param = p_cmp['cmpEquipParam.ctd']
    equip_param = [pc_equip_param[16 + i*128 : 16 + (i+1)*128].split(b'\x00')[0] for i in range(5)]
    new_cmp['cmpEquipParam.ctd'] = build_ctd(equip_param)

    # 7. cmpEquipDress.ctd (4 entries x 64)
    pc_equip_dress = p_cmp['cmpEquipDress.ctd']
    equip_dress = [pc_equip_dress[16 + i*128 : 16 + (i+1)*128].split(b'\x00')[0] for i in range(4)]
    new_cmp['cmpEquipDress.ctd'] = build_ctd(equip_dress)

    # 8. cmpPersonaParam.ctd (5 entries x 64)
    pc_ps_param = p_cmp['cmpPersonaParam.ctd']
    ps_param = [pc_ps_param[16 + i*128 : 16 + (i+1)*128].split(b'\x00')[0] for i in range(5)]
    new_cmp['cmpPersonaParam.ctd'] = build_ctd(ps_param)

    # 9. cmpItemList.ctd (1 entry x 64)
    pc_item_list = p_cmp['cmpItemList.ctd']
    item_list = [pc_item_list[16 : 16 + 128].split(b'\x00')[0]]
    new_cmp['cmpItemList.ctd'] = build_ctd(item_list)

    # 10. cmpBookHelp.ctd (1 entry x 64)
    pc_book_help = p_cmp['cmpBookHelp.ctd']
    book_help = [pc_book_help[16 : 16 + 128].split(b'\x00')[0]]
    new_cmp['cmpBookHelp.ctd'] = build_ctd(book_help)

    # 11. cmpQuestItem.ctd (69 entries x 64)
    pc_quest = p_cmp['cmpQuestItem.ctd']
    quest_items = [pc_quest[16 + i*128 : 16 + (i+1)*128].split(b'\x00')[0] for i in range(69)]
    new_cmp['cmpQuestItem.ctd'] = build_ctd(quest_items)

    # 12. cmpCalendarItem.ctd (39 entries x 64)
    pc_cal = p_cmp['cmpCalendarItem.ctd']
    cal_items = [pc_cal[16 + i*128 : 16 + (i+1)*128].split(b'\x00')[0] for i in range(39)]
    new_cmp['cmpCalendarItem.ctd'] = build_ctd(cal_items)

    # 13. camp_msg.bmd: use PC Italian version!
    new_cmp['camp_msg.bmd'] = p_cmp['camp_msg.bmd']

    out_arc = build_arc(new_cmp)
    print(f"Built localized cmpTable.bin: {len(out_arc)} bytes ({len(new_cmp)} files).")
    return out_arc

if __name__ == '__main__':
    arc_data = build_localized_cmptable('clean_vita_data.cpk', 'Persona 4 Golden/data_it.cpk')
    with open('test_localized_cmpTable.bin', 'wb') as f:
        f.write(arc_data)
    print("Saved test_localized_cmpTable.bin successfully!")
