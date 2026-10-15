import os
import sys
import time
import struct
import shutil
from PIL import Image
import cricodecs.cpk as cpk

from build_vita_cmptable import build_localized_cmptable
from build_vita_fcltable import build_localized_fcltable
from build_vita_textures import (
    build_localized_title_spr,
    build_localized_press_button_tmx,
    build_localized_calender_spr,
    build_localized_event_skip_spr,
    build_localized_cmain_spr,
    build_localized_save_spr,
    build_localized_date_change_spr,
    build_localized_game_help_spr,
    build_localized_picture_tmx,
    build_localized_channel_main,
    build_localized_lesson_pack,
    build_localized_art_ch_arc,
    build_localized_quiz_pack,
    build_localized_music_ch_arc,
    build_localized_live_ch_arc,
    build_localized_anim_ch_arc,
    build_localized_quiz_arc
)

def is_arc(data):
    if len(data) < 40:
        return False
    count = struct.unpack('<I', data[:4])[0]
    if count == 0 or count > 500:
        return False
    pos = 4
    for _ in range(count):
        if pos + 36 > len(data):
            return False
        name_bytes = data[pos:pos+32]
        if b'\x00' not in name_bytes:
            return False
        name = name_bytes.split(b'\x00')[0]
        if not name or not all(0x20 <= b <= 0x7e for b in name):
            return False
        sz = struct.unpack('<I', data[pos+32:pos+36])[0]
        pos += 36 + sz
        if pos > len(data):
            return False
    return pos == len(data)

def parse_arc(data):
    count = struct.unpack('<I', data[:4])[0]
    pos = 4
    files = {}
    for i in range(count):
        name = data[pos:pos+32].split(b'\x00')[0].decode('latin1')
        size = struct.unpack('<I', data[pos+32:pos+36])[0]
        files[name] = data[pos+36:pos+36+size]
        pos += 36 + size
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

def is_pac(data):
    if len(data) < 256:
        return False
    pos = 0
    file_count = 0
    while pos < len(data):
        if pos + 256 > len(data):
            return False
        hdr = data[pos:pos+256]
        if hdr == b'\x00' * 256:
            return pos + 256 == len(data) and file_count > 0
        name_bytes = hdr[:252]
        if b'\x00' not in name_bytes:
            return False
        name = name_bytes.split(b'\x00')[0]
        if not name or not all(0x20 <= b <= 0x7e for b in name):
            return False
        sz = struct.unpack('<I', hdr[252:256])[0]
        file_count += 1
        total = 256 + sz
        pad = (64 - (total % 64)) % 64
        pos += total + pad
        if pos > len(data):
            return False
    return file_count > 0

def parse_pac(data):
    pos = 0
    files = {}
    order = []
    while pos < len(data):
        if pos + 256 > len(data):
            break
        header = data[pos:pos+256]
        name_bytes = header[:252]
        if b'\x00' in name_bytes:
            name_str = name_bytes.split(b'\x00')[0].decode('latin1', errors='ignore')
        else:
            break
        if not name_str or any(c in name_str for c in ['\n', '\r', '\t']):
            break
        size = struct.unpack('<I', header[252:256])[0]
        files[name_str] = data[pos+256:pos+256+size]
        order.append(name_str)
        total = 256 + size
        pad = (64 - (total % 64)) % 64
        pos += total + pad
    return files, order

def build_pac(files_dict, order):
    out = bytearray()
    for name in order:
        b = files_dict[name]
        hdr = bytearray(256)
        nb = name.encode('latin1')
        hdr[:len(nb)] = nb
        hdr[252:256] = len(b).to_bytes(4, 'little')
        out += hdr
        out += b
        total = 256 + len(b)
        pad = (64 - (total % 64)) % 64
        if pad > 0:
            out += b'\x00' * pad
    out += b'\x00' * 256
    return bytes(out)

def is_texture(name):
    lower = name.lower()
    for ext in ['.spr', '.tmx', '.fnt', '.gxt', '.dds']:
        if lower.endswith(ext):
            return True
    return False

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

def merge_general_data(v_bytes, pc_bytes, name=''):
    if is_arc(v_bytes) and is_arc(pc_bytes):
        v_files = parse_arc(v_bytes)
        pc_files = parse_arc(pc_bytes)
        rebuilt = {}
        for sub_name, sub_data in v_files.items():
            if sub_name in pc_files:
                rebuilt[sub_name] = merge_general_data(sub_data, pc_files[sub_name], sub_name)
            else:
                rebuilt[sub_name] = sub_data
        return build_arc(rebuilt)

    if is_pac(v_bytes) and is_pac(pc_bytes):
        v_files, v_order = parse_pac(v_bytes)
        pc_files, _ = parse_pac(pc_bytes)
        rebuilt = {}
        for sub_name in v_order:
            if sub_name in pc_files:
                rebuilt[sub_name] = merge_general_data(v_files[sub_name], pc_files[sub_name], sub_name)
            else:
                rebuilt[sub_name] = v_files[sub_name]
        return build_pac(rebuilt, v_order)

    if is_texture(name):
        return v_bytes
    return replace_accents_safe(pc_bytes)


def main():
    print("==================================================")
    print("   P4G PS Vita Italian Localization Final Builder ")
    print("==================================================")
    t0 = time.time()

    vita_cpk_path = "clean_vita_data.cpk"
    pc_cpk_path = "Persona 4 Golden/data_it.cpk"
    out_cpk_path = "rePatch_PCSB00245/PCSB00245/data/data.cpk"
    os.makedirs(os.path.dirname(out_cpk_path), exist_ok=True)

    print(f"Loading base Vita CPK: {vita_cpk_path}...")
    vita = cpk.load(vita_cpk_path)
    print(f"Loading PC Italian CPK: {pc_cpk_path}...")
    pc = cpk.load(pc_cpk_path)

    def get_cpk_file(c, name):
        for idx in range(c.file_count):
            fi = c.file_info(idx)
            p = f"{fi.dirname}/{fi.filename}" if fi.dirname else fi.filename
            if p == name or fi.filename == name:
                return c.file_bytes(idx)
        return None

    # 1. Build localized cmpTable.bin
    localized_cmptable_bytes = replace_accents_safe(build_localized_cmptable(vita_cpk_path, pc_cpk_path))

    # 2. Build localized fclTable.bin
    localized_fcltable_bytes = replace_accents_safe(build_localized_fcltable(vita_cpk_path, pc_cpk_path))

    # 3. Build localized camp.arc inside init_free.bin
    v_init_free_raw = get_cpk_file(vita, 'init_free.bin')
    v_init_files, v_init_order = parse_pac(v_init_free_raw)
    p_init_free_raw = get_cpk_file(pc, 'init_free.bin')
    p_init_files, _ = parse_pac(p_init_free_raw)

    v_camp_arc = parse_arc(v_init_files['init/camp.arc'])
    p_camp_arc = parse_arc(p_init_files['init/camp.arc'])

    # 3a. calender.spr
    v_cal_spr = v_camp_arc['calender.spr']
    v_camp_arc['calender.spr'] = build_localized_calender_spr(v_cal_spr, 'decoded_pc_calender.png')

    # 3b. event_skip.spr ("Salta")
    v_skip_spr = v_camp_arc['event_skip.spr']
    p_skip_spr = p_camp_arc['event_skip.spr']
    v_camp_arc['event_skip.spr'] = build_localized_event_skip_spr(v_skip_spr, p_skip_spr)

    # 3c. c_main01x2.spr (HUD Days & Times, Backlog Help)
    v_cmain_spr = v_camp_arc['c_main01x2.spr']
    p_cmain_spr = p_camp_arc['c_main01x2.spr']
    v_camp_arc['c_main01x2.spr'] = build_localized_cmain_spr(v_cmain_spr, p_cmain_spr)

    localized_camp_arc_bytes = build_arc(v_camp_arc)

    # 4. Assemble localized init_free.bin
    rebuilt_init_free = {}
    for fn in v_init_order:
        if fn == 'init/cmpTable.bin':
            rebuilt_init_free[fn] = localized_cmptable_bytes
        elif fn == 'init/fclTable.bin':
            rebuilt_init_free[fn] = localized_fcltable_bytes
        elif fn == 'init/camp.arc':
            rebuilt_init_free[fn] = localized_camp_arc_bytes
        elif fn in p_init_files:
            rebuilt_init_free[fn] = merge_general_data(v_init_files[fn], p_init_files[fn], fn)
        else:
            rebuilt_init_free[fn] = v_init_files[fn]

    localized_init_free_bytes = build_pac(rebuilt_init_free, v_init_order)
    print(f"Assembled localized init_free.bin: {len(localized_init_free_bytes)} bytes.")

    # 5. Build localized title.bin
    v_title_raw = get_cpk_file(vita, 'title.bin')
    v_title_files, v_title_order = parse_pac(v_title_raw)
    p_title_raw = get_cpk_file(pc, 'title.bin')
    p_title_files, _ = parse_pac(p_title_raw)

    v_title_spr = v_title_files['p4g_menu01spr.spr']
    v_title_files['p4g_menu01spr.spr'] = build_localized_title_spr(v_title_spr, 'decoded_pc_title_menu.png')
    v_title_files['PRESS_ANY_BUTTONmoji.tmx'] = build_localized_press_button_tmx(v_title_files['PRESS_ANY_BUTTONmoji.tmx'], p_title_files)

    localized_title_bin_bytes = build_pac(v_title_files, v_title_order)
    print(f"Assembled localized title.bin: {len(localized_title_bin_bytes)} bytes.")

    # 6. Build localized date_change.bin
    v_date_raw = get_cpk_file(vita, 'date_change.bin')
    v_date_files, v_date_order = parse_pac(v_date_raw)
    v_date_spr = v_date_files['date_change01.spr']
    localized_date_spr_bytes = build_localized_date_change_spr(v_date_spr, 'decoded_vita_date_change.png')

    v_date_files['date_change01.spr'] = localized_date_spr_bytes
    localized_date_change_bin_bytes = build_pac(v_date_files, v_date_order)
    print(f"Assembled localized date_change.bin: {len(localized_date_change_bin_bytes)} bytes.")

    # 7. Build localized font/game_helpx2.spr
    v_game_help_raw = get_cpk_file(vita, 'game_helpx2.spr')
    localized_game_help_bytes = build_localized_game_help_spr(v_game_help_raw, 'pc_game_helpx2.png')

    # 8. Build localized mcPanel.arc (Save / Load screen UI)
    v_mc_raw = get_cpk_file(vita, 'mcPanel.arc')
    v_mc_files = parse_arc(v_mc_raw)
    p_mc_raw = get_cpk_file(pc, 'mcPanel.arc')
    p_mc_files = parse_arc(p_mc_raw)

    v_mc_files['p4g_savespr01.spr'] = build_localized_save_spr(v_mc_files['p4g_savespr01.spr'], p_mc_files['p4g_savespr01.spr'])
    localized_mcpanel_arc_bytes = build_arc(v_mc_files)
    print(f"Assembled localized mcPanel.arc: {len(localized_mcpanel_arc_bytes)} bytes.")

    # 9. Build localized Midnight Channel TV archives
    print("Building localized Midnight Channel TV archives...")
    v_chan_raw = get_cpk_file(vita, 'title/channelMain.arc')
    p_chan_raw = get_cpk_file(pc, 'title/channelMain.arc')
    localized_channel_main_bytes = build_localized_channel_main(v_chan_raw, p_chan_raw)

    v_lesson_raw = get_cpk_file(vita, 'title/lesson.pack')
    p_lesson_raw = get_cpk_file(pc, 'title/lesson.pack')
    localized_lesson_pack_bytes = build_localized_lesson_pack(v_lesson_raw, p_lesson_raw)

    v_art_raw = get_cpk_file(vita, 'title/artCh.arc')
    p_art_raw = get_cpk_file(pc, 'title/artCh.arc')
    localized_art_ch_arc_bytes = build_localized_art_ch_arc(v_art_raw, p_art_raw)

    v_quiz_raw = get_cpk_file(vita, 'title/quiz.pack')
    p_quiz_raw = get_cpk_file(pc, 'title/quiz.pack')
    localized_quiz_pack_bytes = build_localized_quiz_pack(v_quiz_raw, p_quiz_raw)

    v_mus_raw = get_cpk_file(vita, 'title/musicCh.arc')
    p_mus_raw = get_cpk_file(pc, 'title/musicCh.arc')
    localized_music_ch_arc_bytes = build_localized_music_ch_arc(v_mus_raw, p_mus_raw)

    v_live_raw = get_cpk_file(vita, 'title/liveCh.arc')
    p_live_raw = get_cpk_file(pc, 'title/liveCh.arc')
    localized_live_ch_arc_bytes = build_localized_live_ch_arc(v_live_raw, p_live_raw)

    v_anim_raw = get_cpk_file(vita, 'title/animCh.arc')
    p_anim_raw = get_cpk_file(pc, 'title/animCh.arc')
    localized_anim_ch_arc_bytes = build_localized_anim_ch_arc(v_anim_raw, p_anim_raw)

    v_qarc_raw = get_cpk_file(vita, 'title/quiz.arc')
    p_qarc_raw = get_cpk_file(pc, 'title/quiz.arc')
    localized_quiz_arc_bytes = build_localized_quiz_arc(v_qarc_raw, p_qarc_raw)

    # 10. Build lookup map for PC files
    pc_lookup = {}
    for j in range(pc.file_count):
        pf = pc.file_info(j)
        pfull = f"{pf.dirname}/{pf.filename}" if pf.dirname else pf.filename
        pc_lookup[pfull.lower()] = (j, pfull, pf)

    # 11. Process all Vita CPK files
    print("\nApplying Italian translation to full CPK...")
    replaced_count = 0
    special_count = 0

    for i in range(vita.file_count):
        vf = vita.file_info(i)
        vfull = f"{vf.dirname}/{vf.filename}" if vf.dirname else vf.filename
        v_lower = vfull.lower()

        was_compressed = (vf.extract_size > 0 and vf.extract_size != vf.file_size)

        # Custom injected files
        if vf.filename == 'init_free.bin':
            vita.replace_bytes(i, localized_init_free_bytes, compress=was_compressed)
            special_count += 1
            continue
        elif vf.filename == 'title.bin':
            vita.replace_bytes(i, localized_title_bin_bytes, compress=was_compressed)
            special_count += 1
            continue
        elif vf.filename == 'date_change.bin':
            vita.replace_bytes(i, localized_date_change_bin_bytes, compress=was_compressed)
            special_count += 1
            continue
        elif vf.filename == 'game_helpx2.spr':
            vita.replace_bytes(i, localized_game_help_bytes, compress=was_compressed)
            special_count += 1
            continue
        elif vf.filename == 'mcPanel.arc':
            vita.replace_bytes(i, localized_mcpanel_arc_bytes, compress=was_compressed)
            special_count += 1
            continue
        elif vf.filename == 'channelMain.arc':
            vita.replace_bytes(i, localized_channel_main_bytes, compress=was_compressed)
            special_count += 1
            continue
        elif vf.filename == 'lesson.pack':
            vita.replace_bytes(i, localized_lesson_pack_bytes, compress=was_compressed)
            special_count += 1
            continue
        elif vf.filename == 'artCh.arc':
            vita.replace_bytes(i, localized_art_ch_arc_bytes, compress=was_compressed)
            special_count += 1
            continue
        elif vf.filename == 'quiz.pack':
            vita.replace_bytes(i, localized_quiz_pack_bytes, compress=was_compressed)
            special_count += 1
            continue
        elif vf.filename == 'musicCh.arc':
            vita.replace_bytes(i, localized_music_ch_arc_bytes, compress=was_compressed)
            special_count += 1
            continue
        elif vf.filename == 'liveCh.arc':
            vita.replace_bytes(i, localized_live_ch_arc_bytes, compress=was_compressed)
            special_count += 1
            continue
        elif vf.filename == 'animCh.arc':
            vita.replace_bytes(i, localized_anim_ch_arc_bytes, compress=was_compressed)
            special_count += 1
            continue
        elif vf.filename == 'quiz.arc':
            vita.replace_bytes(i, localized_quiz_arc_bytes, compress=was_compressed)
            special_count += 1
            continue
        elif (vf.dirname or '').lower() == 'font/picture' and v_lower in pc_lookup:
            pj, pfull, pf = pc_lookup[v_lower]
            v_orig = vita.file_bytes(i)
            p_data = pc.file_bytes(pj)
            loc_pic = build_localized_picture_tmx(v_orig, p_data)
            vita.replace_bytes(i, loc_pic, compress=was_compressed)
            special_count += 1
            continue

        # Standard dialog/event/script replacement from PC
        if v_lower in pc_lookup:
            pj, pfull, pf = pc_lookup[v_lower]
            if pf.filename.lower().endswith('.dds') or pf.filename.lower().endswith('.gmo'):
                continue
            v_bytes = vita.file_bytes(i)
            p_bytes = pc.file_bytes(pj)
            new_bytes = merge_general_data(v_bytes, p_bytes, pf.filename)
            vita.replace_bytes(i, new_bytes, compress=was_compressed)
            replaced_count += 1

        if (replaced_count % 300 == 0) and replaced_count > 0:
            print(f"  Processed {replaced_count} files...")

    print(f"\nDone merging. Replaced: {replaced_count} files, Injected custom assets: {special_count}.")

    print("Configuring CPK container header for PS Vita...")
    vita.declared_preset_for_save = cpk.CpkPreset.FILENAME
    vita.enable_toc = True
    vita.enable_etoc = True
    vita.enable_gtoc = False
    vita.enable_itoc = False
    vita.alignment = 2048

    print(f"Saving finalized Italian data.cpk to {out_cpk_path}...")
    t_save = time.time()
    vita.save(out_cpk_path)
    save_time = time.time() - t_save
    sz_mb = os.path.getsize(out_cpk_path) / (1024 * 1024)
    print(f"Saved {out_cpk_path} ({sz_mb:.2f} MB) in {save_time:.1f}s.")

    if os.path.exists("E:/rePatch/PCSB00245/data"):
        print("Copying finalized data.cpk to E:/rePatch/PCSB00245/data/data.cpk...")
        t_copy = time.time()
        shutil.copyfile(out_cpk_path, "E:/rePatch/PCSB00245/data/data.cpk")
        print(f"Copied to PS Vita in {time.time() - t_copy:.1f}s.")

    total_time = time.time() - t0
    print(f"All done in {total_time:.1f}s!")

if __name__ == '__main__':
    main()
