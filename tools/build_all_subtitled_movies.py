import os
import sys
import time
import shutil
import struct
import subprocess
import cricodecs.cpk as cpk
import cricodecs.usm as usm

def va_to_file(va):
    if not (0x140000000 <= va <= 0x140ffffff):
        return None
    rva = va - 0x140000000
    if 0xa20000 <= rva < 0xa20000 + 0x1da1a000:
        return rva - 0x1800
    elif 0x887000 <= rva < 0x887000 + 0x199000:
        return rva - 0x1400
    return None

def sec_to_ass(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int(round((t - int(t)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

replacements = {
    b'\x9c\xc3': 'È',
    b'\x9c\xda': 'à',
    b'\x9c\xe2': 'è',
    b'\x9c\xe3': 'é',
    b'\x9c\xe6': 'ì',
    b'\x9c\xec': 'ò',
    b'\x9c\xf2': 'ù',
    b'\x80\x82': '"',
}

def decode_text(b):
    for k, v in replacements.items():
        b = b.replace(k, v.encode('utf-8'))
    s = b.decode('utf-8')
    return s.replace('\n', r'\N')

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 960
PlayResY: 544
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Segoe UI,28,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2.5,1,2,30,30,28,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def extract_italian_subtitles(exe_path):
    with open(exe_path, 'rb') as f:
        full_data = f.read()

    movie_names = {}
    pos = 0xb112b0
    for i in range(63):
        chunk = full_data[pos:pos+144]
        name = chunk[16:80].split(b'\x00')[0].decode('latin1', 'ignore')
        if name.startswith('movie/'):
            movie_names[i] = name.replace('movie/', '')
        pos += 144

    it_base = 0x915d00
    movies_subs = {}

    for idx in range(44):
        p_track = struct.unpack('<Q', full_data[it_base + idx*8 : it_base + (idx+1)*8])[0]
        if p_track == 0:
            continue
        tf = va_to_file(p_track)
        if not tf:
            continue
        m_name = movie_names.get(idx)
        if not m_name:
            continue

        lines = []
        pos = tf
        while True:
            st, et, str_va = struct.unpack('<ddQ', full_data[pos:pos+24])
            if st == 0.0 and et == 0.0 and str_va == 0:
                break
            sf = va_to_file(str_va)
            if sf:
                raw = full_data[sf:sf+500].split(b'\x00')[0]
                text = decode_text(raw)
                lines.append((st, et, text))
            pos += 24

        if lines:
            movies_subs[m_name] = lines

    return movies_subs

def main():
    print("=" * 60)
    print(" Persona 4 Golden - PS Vita Italian Movie Subtitler")
    print("=" * 60)

    exe_path = "Persona 4 Golden/P4G.exe"
    cpk_path = "Persona 4 Golden/data_movie.cpk"
    repatch_movie_dir = "rePatch_PCSB00245/PCSB00245/data/movie"
    vita_movie_dir = "E:/rePatch/PCSB00245/data/movie"
    temp_dir = "temp_movie"

    os.makedirs(repatch_movie_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    has_vita_drive = os.path.exists("E:/rePatch/PCSB00245")
    if has_vita_drive:
        os.makedirs(vita_movie_dir, exist_ok=True)
        print(f"[OK] PS Vita detected on drive E: ({vita_movie_dir})")
    else:
        print("[INFO] PS Vita drive E: not detected, saving locally to rePatch.")

    print("\n[1/3] Extracting Italian subtitles from PC executable...")
    movies_subs = extract_italian_subtitles(exe_path)
    print(f"[OK] Found {len(movies_subs)} movies with Italian subtitles.")

    print("\n[2/3] Loading PC data_movie.cpk archive...")
    movie_cpk = cpk.load(cpk_path)
    cpk_files = {}
    for i in range(movie_cpk.file_count):
        fi = movie_cpk.file_info(i)
        cpk_files[fi.filename] = i
    print(f"[OK] Loaded CPK with {movie_cpk.file_count} USM cutscenes.")

    print("\n[3/3] Encoding cutscenes for PS Vita (960x544, H.264 Main L4.0, AAC Stereo)...")
    success_count = 0
    total = len(movies_subs)

    # Sort movies logically
    sorted_movies = sorted(movies_subs.keys())

    t0_all = time.time()

    for idx, m_name in enumerate(sorted_movies, 1):
        lines = movies_subs[m_name]
        out_mp4 = os.path.join(repatch_movie_dir, m_name)
        vita_mp4 = os.path.join(vita_movie_dir, m_name) if has_vita_drive else None

        # Check if already processed
        if os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 100000:
            print(f"[{idx:02d}/{total:02d}] {m_name:15} -> Already built ({os.path.getsize(out_mp4)} bytes).", end="")
            if has_vita_drive and (not os.path.exists(vita_mp4) or os.path.getsize(vita_mp4) != os.path.getsize(out_mp4)):
                shutil.copy2(out_mp4, vita_mp4)
                print(" Copied to Vita.", end="")
            print()
            success_count += 1
            continue

        print(f"[{idx:02d}/{total:02d}] Processing {m_name} ({len(lines)} subtitle lines)...")
        t0_cut = time.time()

        # 1. Write ASS subtitle file
        ass_path = os.path.join(temp_dir, f"{m_name}.ass")
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(ASS_HEADER)
            for st, et, text in lines:
                f.write(f"Dialogue: 0,{sec_to_ass(st)},{sec_to_ass(et)},Default,,0,0,0,,{text}\n")

        # 2. Determine corresponding USM filename
        base_usm = m_name.replace('.mp4', '.usm')
        # Check if _E version exists and is preferred (e.g. P4CT017_E.usm)
        cand_e = m_name.replace('.mp4', '_E.usm')
        if cand_e in cpk_files:
            target_usm = cand_e
        elif base_usm in cpk_files:
            target_usm = base_usm
        else:
            print(f"  [ERROR] Could not find {base_usm} in data_movie.cpk!")
            continue

        # 3. Demux USM
        usm_idx = cpk_files[target_usm]
        usm_bytes = movie_cpk.file_bytes(usm_idx)
        demux_res = usm.demux(usm_bytes)

        ivf_name = None
        hca_name = None

        # Prefer English voice (_VE) if present, else #00
        for sname, sbytes in demux_res.items():
            sp = os.path.join(temp_dir, sname)
            with open(sp, 'wb') as sf:
                sf.write(sbytes)
            if sname.endswith('.ivf'):
                ivf_name = sp
            elif '_VE' in sname and sname.endswith(('.hca', '.adx')):
                hca_name = sp
            elif hca_name is None and sname.endswith(('.hca', '.adx')):
                hca_name = sp

        if not ivf_name or not hca_name:
            print(f"  [ERROR] Demux failed for {target_usm} (ivf={ivf_name}, audio={hca_name})")
            continue

        # 4. Run ffmpeg
        ass_filter_path = os.path.abspath(ass_path).replace('\\', '/').replace(':', '\\:')
        vf = f"scale=960:544,ass='{ass_filter_path}'"

        cmd = [
            'ffmpeg', '-y',
            '-i', ivf_name,
            '-i', hca_name,
            '-vf', vf,
            '-c:v', 'libx264',
            '-profile:v', 'main',
            '-level', '4.0',
            '-pix_fmt', 'yuv420p',
            '-b:v', '2500k',
            '-maxrate', '3000k',
            '-bufsize', '4000k',
            '-c:a', 'aac',
            '-b:a', '160k',
            '-ar', '48000',
            '-movflags', '+faststart',
            out_mp4
        ]

        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if res.returncode != 0:
            print(f"  [ERROR] FFmpeg failed for {m_name}!")
            print(res.stderr.decode('latin1', 'ignore')[-500:])
            continue

        # 5. Copy to Vita
        if has_vita_drive:
            shutil.copy2(out_mp4, vita_mp4)

        elapsed = time.time() - t0_cut
        sz_mb = os.path.getsize(out_mp4) / (1024 * 1024)
        print(f"  -> Encoded {m_name} ({sz_mb:.1f} MB) in {elapsed:.1f}s")
        success_count += 1

        # 6. Cleanup temporary demuxed files
        for sname in demux_res.keys():
            sp = os.path.join(temp_dir, sname)
            if os.path.exists(sp):
                try:
                    os.remove(sp)
                except:
                    pass
        if os.path.exists(ass_path):
            try:
                os.remove(ass_path)
            except:
                pass

    total_time = time.time() - t0_all
    print("\n" + "=" * 60)
    print(f" COMPLETED: {success_count}/{total} cutscenes successfully subtitled and encoded!")
    print(f" Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print("=" * 60)

if __name__ == '__main__':
    main()
