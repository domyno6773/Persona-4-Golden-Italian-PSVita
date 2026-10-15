import os
import struct
from PIL import Image, ImageFont, ImageDraw, ImageFilter
import cricodecs.cpk as cpk

def encode_4bpp_rgba(img, pal_raw):
    pal_rgba = []
    for i in range(16):
        r, g, b, a = pal_raw[i*4:(i+1)*4]
        pal_rgba.append((r, g, b, min(255, a * 2)))

    trans_indices = [i for i, c in enumerate(pal_rgba) if c[3] < 10]
    if not trans_indices:
        trans_indices = [min(range(16), key=lambda i: pal_rgba[i][3])]
    trans_idx = trans_indices[0]

    w, h = img.size
    pix = img.load()
    encoded = bytearray((w * h) // 2)
    for y in range(h):
        for x in range(0, w, 2):
            p0 = pix[x, y]
            p1 = pix[x+1, y]
            
            if p0[3] < 15:
                c0 = trans_idx
            else:
                c0 = min(range(16), key=lambda i: (
                    (pal_rgba[i][0] - p0[0])**2 +
                    (pal_rgba[i][1] - p0[1])**2 +
                    (pal_rgba[i][2] - p0[2])**2 +
                    (pal_rgba[i][3] - p0[3])**2 * 2
                ))
            if p1[3] < 15:
                c1 = trans_idx
            else:
                c1 = min(range(16), key=lambda i: (
                    (pal_rgba[i][0] - p1[0])**2 +
                    (pal_rgba[i][1] - p1[1])**2 +
                    (pal_rgba[i][2] - p1[2])**2 +
                    (pal_rgba[i][3] - p1[3])**2 * 2
                ))
            encoded[(y * w + x) // 2] = c0 | (c1 << 4)
    return bytes(encoded)

def encode_4bpp_nibbles(alpha_img, pal_alphas):
    w, h = alpha_img.size
    pixels = alpha_img.load()
    encoded = bytearray((w * h) // 2)
    for y in range(h):
        for x in range(0, w, 2):
            a0 = pixels[x, y]
            a1 = pixels[x+1, y]
            c0 = min(range(16), key=lambda i: abs(pal_alphas[i] - a0))
            c1 = min(range(16), key=lambda i: abs(pal_alphas[i] - a1))
            encoded[(y * w + x) // 2] = c0 | (c1 << 4)
    return bytes(encoded)

def build_localized_title_spr(orig_spr_bytes, pc_title_png_path):
    print("Building localized p4g_menu01spr.spr...")
    spr = bytearray(orig_spr_bytes)
    tmx_pos = spr.find(b'TMX0')
    tmx = spr[tmx_pos:]
    pal_raw = tmx[0x38:0x78]
    pal_alphas = [min(255, pal_raw[i*4 + 3] * 2) for i in range(16)]

    # Load PC texture
    pc_img = Image.open(pc_title_png_path)
    pc_a = pc_img.split()[3]

    # Create new 256x256 alpha channel starting with blank
    new_a = Image.new('L', (256, 256), 0)

    # Copy star icon from original Vita texture
    v_orig_pix = tmx[0x78:0x78+32768]
    for y in range(153, 235):
        for x in range(1, 80):
            byte_idx = (y * 256 + x) // 2
            b = v_orig_pix[byte_idx]
            c = (b & 0x0f) if (x % 2 == 0) else ((b >> 4) & 0x0f)
            new_a.putpixel((x, y), pal_alphas[c])

    # Crop and downscale items from PC
    def get_slot(box, target_w, target_h):
        crop_a = pc_a.crop(box)
        bb = crop_a.getbbox()
        c = crop_a.crop(bb)
        scale = min(target_w / c.width, target_h / c.height)
        new_w = int(c.width * scale)
        new_h = int(c.height * scale)
        scaled = c.resize((new_w, new_h), Image.Resampling.LANCZOS)
        slot = Image.new('L', (target_w, target_h), 0)
        slot.paste(scaled, (0, (target_h - new_h) // 2))
        return slot

    s0 = get_slot((13, 0, 420, 76), 192, 37)
    s1 = get_slot((13, 76, 420, 152), 192, 37)
    s2 = get_slot((13, 152, 420, 228), 189, 37)
    s3 = get_slot((13, 228, 420, 304), 164, 37)

    new_a.paste(s0, (1, 1))
    new_a.paste(s1, (1, 39))
    new_a.paste(s2, (1, 77))
    new_a.paste(s3, (1, 115))

    new_pix = encode_4bpp_nibbles(new_a, pal_alphas)
    pix_offset = tmx_pos + 0x78
    spr[pix_offset : pix_offset + len(new_pix)] = new_pix
    print("Localized p4g_menu01spr.spr built successfully.")
    return bytes(spr)

def build_localized_press_button_tmx(orig_tmx_bytes, pc_title_files):
    print("Building localized PRESS_ANY_BUTTONmoji.tmx...")
    p_btn = pc_title_files['PRESS_ANY_BUTTONmoji.tmx']
    p_pix = p_btn[0x40 : 0x40 + 2048*128*4]
    p_img = Image.frombytes('RGBA', (2048, 128), p_pix)
    p_down = p_img.resize((1024, 64), Image.Resampling.LANCZOS)

    pal_raw = orig_tmx_bytes[0x40:0x80]
    pal_alphas = [min(255, pal_raw[i*4 + 3] * 2) for i in range(16)]

    new_pix = encode_4bpp_nibbles(p_down.split()[3], pal_alphas)
    new_btn = bytearray(orig_tmx_bytes)
    new_btn[0x80 : 0x80 + len(new_pix)] = new_pix
    assert len(new_btn) == len(orig_tmx_bytes)
    print("Localized PRESS_ANY_BUTTONmoji.tmx built successfully.")
    return bytes(new_btn)

def build_localized_calender_spr(orig_spr_bytes, pc_calender_png_path):
    print("Building localized calender.spr...")
    spr = bytearray(orig_spr_bytes)
    tmx_pos = spr.find(b'TMX0')
    tmx = spr[tmx_pos:]
    pal_raw = tmx[0x38:0x78]
    pal_alphas = [min(255, pal_raw[i*4 + 3] * 2) for i in range(16)]

    pc_img = Image.open(pc_calender_png_path)
    down = pc_img.resize((512, 128), Image.Resampling.LANCZOS)
    down_a = down.split()[3]

    new_pix = encode_4bpp_nibbles(down_a, pal_alphas)
    pix_offset = tmx_pos + 0x78
    spr[pix_offset : pix_offset + len(new_pix)] = new_pix
    print("Localized calender.spr built successfully.")
    return bytes(spr)

def build_localized_event_skip_spr(orig_spr_bytes, pc_skip_bytes):
    print("Building localized event_skip.spr (pristine SELECT icon + localized SALTA)...")
    new_skip = bytearray(orig_spr_bytes)

    # Vita Tex 1 at 0xae8: 256x32 8bpp
    # Keep TMX header and palette (0xae8 to 0xae8+0x438) 100% UNTOUCHED
    pal_raw = orig_spr_bytes[0xae8+0x38 : 0xae8+0x438]
    pal_rgba = []
    for i in range(256):
        r, g, b, a = pal_raw[i*4:(i+1)*4]
        pal_rgba.append((r, g, b, min(255, a*2)))

    # Get "Salta" text from PC at (286, 2, 398, 62) (size 112x60)
    p_pix = pc_skip_bytes[0x10e8+0x40 : 0x10e8+0x40 + 512*64*4]
    im_p = Image.frombytes('RGBA', (512, 64), p_pix)
    crop_salta = im_p.crop((286, 2, 398, 62))
    salta_down = crop_salta.resize((56, 30), Image.Resampling.LANCZOS)

    # Pixel array for Tex 1 starts at 0xae8+0x438 (256x32 = 8192 bytes)
    pix_start = 0xae8 + 0x438
    # Start with original Vita pixel indices:
    # Keeps Sprite 7 (SELECT oval button at x=1..79) and Sprite 12 (START button at x=80..142) 100% INTACT!
    v_pix = bytearray(orig_spr_bytes[pix_start : pix_start + 256*32])

    bg_idx = 179 # Background color index for Sprite 13 (SKIP)
    # Replace ONLY Sprite 13 area (x=143..199, y=1..31)
    for y in range(30):
        for x in range(56):
            target_x = 143 + x
            target_y = 1 + y
            r, g, b, a = salta_down.getpixel((x, y))
            if a < 25:
                best_idx = bg_idx
            else:
                best_idx = min(range(256), key=lambda i: (
                    (pal_rgba[i][0] - r)**2 +
                    (pal_rgba[i][1] - g)**2 +
                    (pal_rgba[i][2] - b)**2 +
                    (pal_rgba[i][3] - a)**2 * 2
                ))
            v_pix[target_y * 256 + target_x] = best_idx

    new_skip[pix_start : pix_start + len(v_pix)] = v_pix
    assert len(new_skip) == len(orig_spr_bytes)
    print("Localized event_skip.spr built successfully.")
    return bytes(new_skip)

def build_localized_cmain_spr(orig_spr_bytes, pc_cmain_bytes):
    print("Building localized c_main01x2.spr (HUD days & times, backlog help controls)...")
    new_cmain = bytearray(orig_spr_bytes)

    # Decode PC Tex 0 (0x1c198, 512x512)
    p_pix0 = pc_cmain_bytes[0x1c198+0x40 : 0x1c198+0x40 + 512*512*4]
    p_im0 = Image.frombytes('RGBA', (512, 512), p_pix0)

    # A) Tex 0: Camp/System Menu (256x128 4bpp at 0x15c78)
    # Start with clean Vita Tex 0 pixel indices (keeps kado, check_maru, and arrow 100% authentic)
    pix_raw0 = bytearray(orig_spr_bytes[0x15c78+0x78 : 0x15c78+0x78 + 256*128//2])

    def set_nibble0(arr, x, y, val):
        byte_idx = (y * 256 + x) // 2
        b = arr[byte_idx]
        if x % 2 == 0:
            arr[byte_idx] = (b & 0xf0) | (val & 0x0f)
        else:
            arr[byte_idx] = (b & 0x0f) | ((val & 0x0f) << 4)

    # Replace ONLY the 6 menu option text slots using native Index 3 as background:
    menu_slots = [
        ('quest',      (1*2, 1*2, 84*2, 25*2),     (1, 1, 84, 25)),
        ('config',     (85*2, 1*2, 174*2, 25*2),   (85, 1, 174, 25)),
        ('load',       (1*2, 26*2, 149*2, 50*2),   (1, 26, 132, 50)),
        ('delete',     (1*2, 51*2, 156*2, 75*2),   (1, 51, 156, 75)),
        ('title',      (1*2, 76*2, 189*2, 100*2),  (1, 76, 189, 100)),
        ('difficulty', (1*2, 101*2, 125*2, 125*2), (1, 101, 125, 125)),
    ]
    for name, pc_box, v_box in menu_slots:
        w_slot = v_box[2] - v_box[0]
        h_slot = v_box[3] - v_box[1]
        for y in range(v_box[1], v_box[3]):
            for x in range(v_box[0], v_box[2]):
                set_nibble0(pix_raw0, x, y, 3) # Index 3 is neutral transparent background
        crop_pc = p_im0.crop(pc_box)
        bb = crop_pc.getbbox()
        if bb:
            t_crop = crop_pc.crop(bb)
            max_w = w_slot - 4
            max_h = h_slot - 4
            scale = min(max_w / t_crop.width, max_h / t_crop.height, 0.5)
            w_fit = int(t_crop.width * scale)
            h_fit = int(t_crop.height * scale)
            scaled_t = t_crop.resize((w_fit, h_fit), Image.Resampling.LANCZOS)
            px0 = v_box[0] + 2
            py0 = v_box[1] + (h_slot - h_fit) // 2
            for ty in range(h_fit):
                for tx in range(w_fit):
                    r, g, b, a = scaled_t.getpixel((tx, ty))
                    if a < 30:
                        idx = 3
                    elif a < 90:
                        idx = 15
                    elif a < 160:
                        idx = 14
                    elif r > 220:
                        idx = 13
                    else:
                        idx = 11
                    set_nibble0(pix_raw0, px0 + tx, py0 + ty, idx)

    new_cmain[0x15c78+0x78 : 0x15c78+0x78+len(pix_raw0)] = pix_raw0

    # B) Tex 2: IN-GAME FIELD HUD DAYS (512x512 4bpp at 0x21d98)
    p_pix2 = pc_cmain_bytes[0x13c278+0x40 : 0x13c278+0x40 + 1024*1024*4]
    p_im2 = Image.frombytes('RGBA', (1024, 1024), p_pix2)
    p_down2 = p_im2.resize((512, 512), Image.Resampling.LANCZOS)
    pal_raw2 = orig_spr_bytes[0x21d98+0x38 : 0x21d98+0x78]
    new_pix2 = encode_4bpp_rgba(p_down2, pal_raw2)
    new_cmain[0x21d98+0x78 : 0x21d98+0x78+len(new_pix2)] = new_pix2

    # Tex 3 (0x41e28): DO NOT OVERWRITE! Vita's physical PlayStation controller buttons!

    # C) Tex 4: HELP ACTION LABELS (512x256 4bpp at 0x45eb8)
    p_pix4 = pc_cmain_bytes[0x57c718+0x40 : 0x57c718+0x40 + 1024*1024*4]
    p_im4 = Image.frombytes('RGBA', (1024, 1024), p_pix4)
    p_down4 = p_im4.crop((0, 0, 1024, 512)).resize((512, 256), Image.Resampling.LANCZOS)
    pal_raw4 = orig_spr_bytes[0x45eb8+0x38 : 0x45eb8+0x78]
    new_pix4 = encode_4bpp_rgba(p_down4, pal_raw4)
    new_cmain[0x45eb8+0x78 : 0x45eb8+0x78+len(new_pix4)] = new_pix4

    # D) Tex 5: CONFIRMATION PROMPTS (256x256 4bpp at 0x55f48) -> "Sì", "No", "Cambia", "Dettagli"
    p_pix5 = pc_cmain_bytes[0x97c768+0x40 : 0x97c768+0x40 + 512*512*4]
    p_im5 = Image.frombytes('RGBA', (512, 512), p_pix5)
    p_down5 = p_im5.resize((256, 256), Image.Resampling.LANCZOS)
    pal_raw5 = orig_spr_bytes[0x55f48+0x38 : 0x55f48+0x78]
    new_pix5 = encode_4bpp_rgba(p_down5, pal_raw5)
    new_cmain[0x55f48+0x78 : 0x55f48+0x78+len(new_pix5)] = new_pix5

    # NEW: Tex 12: IN-GAME HUD TIME OF DAY + Sistema menu header (512x512 4bpp at 0x70ab8)
    p_pix12 = pc_cmain_bytes[0xaa4b18+0x40 : 0xaa4b18+0x40 + 1024*1024*4]
    p_im12 = Image.frombytes('RGBA', (1024, 1024), p_pix12)
    p_down12 = p_im12.resize((512, 512), Image.Resampling.LANCZOS)
    # Erase PC Xbox [A] and circle [O] buttons on right side of c_system_L
    draw12 = ImageDraw.Draw(p_down12)
    draw12.rectangle([245, 266, 298, 340], fill=(0, 0, 0, 0))

    pal_raw12 = orig_spr_bytes[0x70ab8+0x38 : 0x70ab8+0x78]
    new_pix12 = encode_4bpp_rgba(p_down12, pal_raw12)
    new_cmain[0x70ab8+0x78 : 0x70ab8+0x78+len(new_pix12)] = new_pix12

    # NEW: Tex 19: FIELD INTERACT PROMPT (Official full "ESAMINA!!" text only) (128x32 4bpp at 0xe98a8)
    p_pix19 = pc_cmain_bytes[0x19aad88+0x40 : 0x19aad88+0x40 + 256*64*4]
    im_p19 = Image.frombytes('RGBA', (256, 64), p_pix19)
    # Full Italian word "ESAMINA!!" starts at x=5, ends at x=248
    esamina_crop = im_p19.crop((5, 6, 248, 55))
    bb19 = esamina_crop.getbbox()
    c_text19 = esamina_crop.crop(bb19)
    scale_19 = min(120.0 / c_text19.width, 26.0 / c_text19.height)
    w_19, h_19 = int(c_text19.width * scale_19), int(c_text19.height * scale_19)
    esamina_scaled = c_text19.resize((w_19, h_19), Image.Resampling.LANCZOS)

    new_tex19 = Image.new('RGBA', (128, 32), (0, 0, 0, 0))
    pos_x = (128 - w_19) // 2
    pos_y = (32 - h_19) // 2
    new_tex19.paste(esamina_scaled, (pos_x, pos_y))

    pal_raw19 = orig_spr_bytes[0xe98a8+0x38 : 0xe98a8+0x78]
    new_pix19 = encode_4bpp_rgba(new_tex19, pal_raw19)
    new_cmain[0xe98a8+0x78 : 0xe98a8+0x78+len(new_pix19)] = new_pix19

    # Tex 23 (0xebae8): DO NOT OVERWRITE! Vita's pristine menu cursor bracket!

    # F) Tex 24: CONTROLS HELP ("Riproduci", "Seleziona", "Aiuto", "ON", "OFF") (128x128 4bpp at 0xedb78)
    p_pix24 = pc_cmain_bytes[0x19c9018+0x40 : 0x19c9018+0x40 + 256*256*4]
    p_im24 = Image.frombytes('RGBA', (256, 256), p_pix24)

    selez = p_im24.crop((25, 7, 198, 55))
    ripro = p_im24.crop((27, 74, 194, 128))
    aiuto = p_im24.crop((26, 133, 148, 180))
    on_img = p_im24.crop((17, 196, 90, 251))
    off_img = p_im24.crop((95, 196, 186, 251))

    new_tex24 = Image.new('RGBA', (128, 128), (0, 0, 0, 0))

    # 1. Riproduci: fit in (1, 1, 52, 34) -> max w=50, max h=28
    scale_r = min(50.0 / ripro.width, 28.0 / ripro.height)
    r_w, r_h = int(ripro.width * scale_r), int(ripro.height * scale_r)
    r_down = ripro.resize((r_w, r_h), Image.Resampling.LANCZOS)
    new_tex24.paste(r_down, (1, 1 + (32 - r_h)//2))

    # 2. Seleziona: fit in (54, 1, 118, 31) -> width 62, height 24 (stops well before edge, no SELECT overlap!)
    s_down = selez.resize((62, 24), Image.Resampling.LANCZOS)
    new_tex24.paste(s_down, (54, 1 + (30 - 24)//2))

    # 3. Aiuto: fit in (1, 66, 79, 98) -> max w=76, max h=28
    scale_a = min(76.0 / aiuto.width, 28.0 / aiuto.height)
    a_w, a_h = int(aiuto.width * scale_a), int(aiuto.height * scale_a)
    a_down = aiuto.resize((a_w, a_h), Image.Resampling.LANCZOS)
    new_tex24.paste(a_down, (1, 66 + (32 - a_h)//2))

    # 4. ON: fit in (1, 100, 45, 127) -> max w=40, max h=24
    scale_on = min(40.0 / on_img.width, 24.0 / on_img.height)
    on_w, on_h = int(on_img.width * scale_on), int(on_img.height * scale_on)
    on_down = on_img.resize((on_w, on_h), Image.Resampling.LANCZOS)
    new_tex24.paste(on_down, (1, 100 + (26 - on_h)//2))

    # 5. OFF: fit in (49, 100, 103, 127) -> max w=50, max h=24
    scale_off = min(50.0 / off_img.width, 24.0 / off_img.height)
    off_w, off_h = int(off_img.width * scale_off), int(off_img.height * scale_off)
    off_down = off_img.resize((off_w, off_h), Image.Resampling.LANCZOS)
    new_tex24.paste(off_down, (49, 100 + (26 - off_h)//2))

    pal_raw24 = orig_spr_bytes[0xedb78+0x38 : 0xedb78+0x78]
    new_pix24 = encode_4bpp_rgba(new_tex24, pal_raw24)
    new_cmain[0xedb78+0x78 : 0xedb78+0x78+len(new_pix24)] = new_pix24

    # NEW: Tex 25: IN-GAME HUD "Doposcuola" / "Pausa pranzo" (256x64 4bpp at 0xefc08)
    p_pix25 = pc_cmain_bytes[0x1a09068+0x40 : 0x1a09068+0x40 + 512*128*4]
    p_im25 = Image.frombytes('RGBA', (512, 128), p_pix25)
    p_down25 = p_im25.resize((256, 64), Image.Resampling.LANCZOS)
    pal_raw25 = orig_spr_bytes[0xefc08+0x38 : 0xefc08+0x78]
    new_pix25 = encode_4bpp_rgba(p_down25, pal_raw25)
    new_cmain[0xefc08+0x78 : 0xefc08+0x78+len(new_pix25)] = new_pix25

    # Update sprite table coordinates from PC for localized Italian text width
    v_num_tex, v_num_spr, v_tex_off_ptr, v_spr_off_ptr = struct.unpack('<HHII', orig_spr_bytes[0x14:0x20])
    p_num_tex, p_num_spr, p_tex_off_ptr, p_spr_off_ptr = struct.unpack('<HHII', pc_cmain_bytes[0x14:0x20])
    
    # Update coordinates for:
    # - Sprites 127..140, 147..157 (Action labels in Tex 4)
    # - Sprites 208..214 (Field HUD Time of Day in Tex 12 & Tex 25)
    target_sprites = list(range(127, 141)) + list(range(147, 158)) + list(range(208, 215))
    for spr_idx in target_sprites:
        if spr_idx < v_num_spr and spr_idx < p_num_spr:
            v_off = struct.unpack('<II', new_cmain[v_spr_off_ptr + spr_idx*8 : v_spr_off_ptr + (spr_idx+1)*8])[1]
            p_off = struct.unpack('<II', pc_cmain_bytes[p_spr_off_ptr + spr_idx*8 : p_spr_off_ptr + (spr_idx+1)*8])[1]
            new_cmain[v_off+0x54 : v_off+0x64] = pc_cmain_bytes[p_off+0x54 : p_off+0x64]

    # Set clean Vita-compatible coordinates for Tex 24 sprites:
    # Sprite 166: Riproduci (1, 1, 1 + r_w, 1 + r_h)
    off166 = struct.unpack('<II', new_cmain[v_spr_off_ptr + 166*8 : v_spr_off_ptr + 167*8])[1]
    struct.pack_into('<4I', new_cmain, off166+0x54, 1, 1, 1 + r_w, 1 + r_h)

    # Sprite 647: Seleziona (54, 1, 54 + 62, 1 + 24) -> (54, 1, 116, 25)
    off647 = struct.unpack('<II', new_cmain[v_spr_off_ptr + 647*8 : v_spr_off_ptr + 648*8])[1]
    struct.pack_into('<4I', new_cmain, off647+0x54, 54, 1, 116, 25)

    # Sprite 644: Aiuto (1, 66, 1 + a_w, 66 + a_h)
    off644 = struct.unpack('<II', new_cmain[v_spr_off_ptr + 644*8 : v_spr_off_ptr + 645*8])[1]
    struct.pack_into('<4I', new_cmain, off644+0x54, 1, 66, 1 + a_w, 66 + a_h)

    # Sprite 645: ON (1, 100, 1 + on_w, 100 + on_h)
    off645 = struct.unpack('<II', new_cmain[v_spr_off_ptr + 645*8 : v_spr_off_ptr + 646*8])[1]
    struct.pack_into('<4I', new_cmain, off645+0x54, 1, 100, 1 + on_w, 100 + on_h)

    # Sprite 646: OFF (49, 100, 49 + off_w, 100 + off_h)
    off646 = struct.unpack('<II', new_cmain[v_spr_off_ptr + 646*8 : v_spr_off_ptr + 647*8])[1]
    struct.pack_into('<4I', new_cmain, off646+0x54, 49, 100, 49 + off_w, 100 + off_h)

    assert len(new_cmain) == len(orig_spr_bytes)
    print("Localized c_main01x2.spr built successfully.")
    return bytes(new_cmain)

def build_localized_save_spr(orig_spr_bytes, pc_savespr_bytes):
    print("Building localized p4g_savespr01.spr (Save/Load screen)...")
    new_spr = bytearray(orig_spr_bytes)

    # Tex 0 at 0x1968 (512x512) from PC Tex 0 (1024x1024 32bpp)
    p_pix0 = pc_savespr_bytes[0x1968+0x40 : 0x1968+0x40 + 1024*1024*4]
    p_im0 = Image.frombytes('RGBA', (1024, 1024), p_pix0)
    p_down0 = p_im0.resize((512, 512), Image.Resampling.LANCZOS)
    pal_raw0 = orig_spr_bytes[0x1968+0x38 : 0x1968+0x78]
    new_pix0 = encode_4bpp_rgba(p_down0, pal_raw0)
    new_spr[0x1968+0x78 : 0x1968+0x78+len(new_pix0)] = new_pix0

    # Tex 2 at 0x21b08 (256x128 4bpp): Italian Banners
    # ("Quale dato vuoi caricare?", "Scegli uno slot dove salvare", "Quale dato vuoi eliminare?", "Conferma", "Indietro")
    p_pix2 = pc_savespr_bytes[0x401ac8+0x40 : 0x401ac8+0x40 + 512*512*4]
    im_p2 = Image.frombytes('RGBA', (512, 512), p_pix2)
    b0 = im_p2.crop((9, 4, 305, 43))      # Save prompt
    b1 = im_p2.crop((333, 62, 401, 106))   # Conferma
    b2 = im_p2.crop((333, 125, 448, 168))  # Indietro
    b3 = im_p2.crop((11, 208, 385, 251))   # Load prompt
    b4 = im_p2.crop((11, 288, 399, 331))   # Delete prompt

    def d50(im):
        return im.resize((im.width // 2, im.height // 2), Image.Resampling.LANCZOS)

    d0, d1, d2, d3, d4 = d50(b0), d50(b1), d50(b2), d50(b3), d50(b4)
    new_tex2 = Image.new('RGBA', (256, 128), (0, 0, 0, 0))
    new_tex2.paste(d0, (2, 2))
    new_tex2.paste(d3, (2, 27))
    new_tex2.paste(d1, (190, 27))
    new_tex2.paste(d2, (190, 56))
    new_tex2.paste(d4, (2, 80))

    pal_raw2 = orig_spr_bytes[0x21b08+0x38 : 0x21b08+0x78]
    new_pix2 = encode_4bpp_rgba(new_tex2, pal_raw2)
    new_spr[0x21b08+0x78 : 0x21b08+0x78+len(new_pix2)] = new_pix2

    # Update sprite table for Tex 2 banners
    coords_map = {
        29: (2, 2, 2 + d0.width, 2 + d0.height),
        30: (2, 27, 2 + d3.width, 27 + d3.height),
        31: (0, 0, 0, 0),
        32: (2, 80, 2 + d4.width, 80 + d4.height),
        33: (190, 27, 190 + d1.width, 27 + d1.height),
        34: (190, 56, 190 + d2.width, 56 + d2.height)
    }
    v_num_tex, v_num_spr, v_tex_off_ptr, v_spr_off_ptr = struct.unpack('<HHII', orig_spr_bytes[0x14:0x20])
    for spr_id, coords in coords_map.items():
        off = struct.unpack('<II', new_spr[v_spr_off_ptr + spr_id*8 : v_spr_off_ptr + (spr_id+1)*8])[1]
        struct.pack_into('<4I', new_spr, off + 0x54, *coords)

    # Tex 7 at 0x2a7d8 (128x256) from PC Tex 7 at 0x514558 (256x512 32bpp)
    p_pix7 = pc_savespr_bytes[0x514558+0x40 : 0x514558+0x40 + 256*512*4]
    p_im7 = Image.frombytes('RGBA', (256, 512), p_pix7)
    p_down7 = p_im7.resize((128, 256), Image.Resampling.LANCZOS)
    pal_raw7 = orig_spr_bytes[0x2a7d8+0x38 : 0x2a7d8+0x78]
    new_pix7 = encode_4bpp_rgba(p_down7, pal_raw7)
    new_spr[0x2a7d8+0x78 : 0x2a7d8+0x78+len(new_pix7)] = new_pix7

    assert len(new_spr) == len(orig_spr_bytes)
    print("Localized p4g_savespr01.spr built successfully.")
    return bytes(new_spr)

def build_localized_date_change_spr(orig_spr_bytes, decoded_vita_date_change_png):
    print("Building localized date_change01.spr...")
    spr = bytearray(orig_spr_bytes)
    tmx_pos = spr.find(b'TMX0')
    tmx = spr[tmx_pos:]
    pal_raw = tmx[0x38:0x78]
    pal_alphas = [min(255, pal_raw[i*4 + 3] * 2) for i in range(16)]

    v_img = Image.open(decoded_vita_date_change_png).convert('RGBA')
    new_v = v_img.copy()

    # Clear x=1..48, y=68..207
    draw = ImageDraw.Draw(new_v)
    draw.rectangle([1, 68, 48, 207], fill=(0, 0, 0, 0))

    try:
        font = ImageFont.truetype("arialbd.ttf", 18)
    except Exception:
        font = ImageFont.load_default()

    ita_days = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"]
    y_slots = [
        (68, 87), (88, 107), (108, 127), (128, 147),
        (148, 167), (168, 187), (188, 207)
    ]

    for (y_top, y_bot), day in zip(y_slots, ita_days):
        bbox = draw.textbbox((0, 0), day, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        xc = (1 + 48) // 2
        yc = (y_top + y_bot) // 2
        x = xc - tw // 2 - bbox[0]
        y = yc - th // 2 - bbox[1]
        draw.text((x, y), day, font=font, fill=(255, 255, 255, 255))

    new_a = new_v.split()[3]
    new_pix = encode_4bpp_nibbles(new_a, pal_alphas)
    pix_offset = tmx_pos + 0x78
    spr[pix_offset : pix_offset + len(new_pix)] = new_pix
    print("Localized date_change01.spr built successfully.")
    return bytes(spr)

def build_localized_game_help_spr(orig_spr_bytes, pc_game_help_png_path):
    print("Building localized game_helpx2.spr...")
    spr = bytearray(orig_spr_bytes)
    tmx_pos = spr.find(b'TMX0')
    tmx = spr[tmx_pos:]
    pal_raw = tmx[0x38:0x78]
    pal_alphas = [min(255, pal_raw[i*4 + 3] * 2) for i in range(16)]

    pc_img = Image.open(pc_game_help_png_path)
    down = pc_img.resize((512, 128), Image.Resampling.LANCZOS)
    down_a = down.split()[3]

    new_pix = encode_4bpp_nibbles(down_a, pal_alphas)
    pix_offset = tmx_pos + 0x78
    spr[pix_offset : pix_offset + len(new_pix)] = new_pix
    print("Localized game_helpx2.spr built successfully.")
    return bytes(spr)

def swizzle_palette_index(idx):
    block = idx // 32
    sub = idx % 32
    if 8 <= sub < 16:
        sub += 8
    elif 16 <= sub < 24:
        sub -= 8
    return block * 32 + sub

def build_localized_picture_tmx(orig_vita_bytes, pc_bytes):
    pc_tmx = pc_bytes[8:]
    w, h = struct.unpack('<HH', pc_tmx[10:14])
    pix = pc_tmx[0x38:0x38 + w*h*4]
    im = Image.frombytes('RGBA', (w, h), pix)

    im_down = im.resize((512, 256), Image.Resampling.LANCZOS)
    im_p = im_down.convert('P', palette=Image.Palette.ADAPTIVE, colors=256)

    pal = im_p.getpalette()
    pal_bytes = bytearray(1024)
    for i in range(256):
        sw_i = swizzle_palette_index(i)
        pal_bytes[sw_i*4] = pal[i*3]
        pal_bytes[sw_i*4 + 1] = pal[i*3 + 1]
        pal_bytes[sw_i*4 + 2] = pal[i*3 + 2]
        pal_bytes[sw_i*4 + 3] = 128

    pix_bytes = bytes(list(im_p.getdata()))
    v_hdr = orig_vita_bytes[:8 + 56]
    new_tmx = v_hdr + pal_bytes + pix_bytes
    assert len(new_tmx) == len(orig_vita_bytes)
    return new_tmx

def encode_8bpp_tmx(rgba_img, tex_name_bytes, orig_fmt=0x13):
    w, h = rgba_img.size
    
    # Normalize alpha
    r, g, b, a = rgba_img.split()
    max_a = max(a.getdata())
    if 0 < max_a <= 128:
        a = a.point(lambda v: min(255, v * 2))
        norm_img = Image.merge('RGBA', (r, g, b, a))
    else:
        norm_img = rgba_img
    
    q = norm_img.quantize(colors=255)
    pal_bytes = q.palette.tobytes()
    num_colors = len(pal_bytes) // 4
    
    tmx_pal = bytearray(1024)
    for i in range(num_colors):
        pr = pal_bytes[i*4]
        pg = pal_bytes[i*4 + 1]
        pb = pal_bytes[i*4 + 2]
        pa = pal_bytes[i*4 + 3]
        pa_tmx = min(128, int(round(pa * 128.0 / 255.0)))
        
        sw_i = swizzle_palette_index(i)
        tmx_pal[sw_i*4 : sw_i*4 + 4] = bytes([pr, pg, pb, pa_tmx])
        
    pix_bytes = q.tobytes()
    assert len(pix_bytes) == w * h
    
    wrap_size = 0x440 + w * h
    hdr = bytearray(64)
    struct.pack_into('<I', hdr, 0x00, 2)
    struct.pack_into('<I', hdr, 0x04, wrap_size)
    hdr[0x08:0x0c] = b'TMX0'
    struct.pack_into('<H', hdr, 0x10, 1)
    struct.pack_into('<H', hdr, 0x12, w)
    struct.pack_into('<H', hdr, 0x14, h)
    hdr[0x16] = orig_fmt
    hdr[0x17] = 0
    struct.pack_into('<I', hdr, 0x18, 0xff000000)
    
    name_clean = tex_name_bytes[:28].ljust(28, b'\x00')
    hdr[0x24:0x40] = name_clean
    
    tmx_data = bytes(hdr) + bytes(tmx_pal) + pix_bytes
    assert len(tmx_data) == wrap_size
    return tmx_data

def decode_pc_tmx_to_rgba(p_tmx):
    p_w, p_h = struct.unpack('<HH', p_tmx[0x12:0x16])
    p_fmt = p_tmx[0x16]
    if p_fmt == 0x00:
        off = 0x40 if p_tmx[8:12] == b'TMX0' else 0x38
        pix = p_tmx[off : off + p_w * p_h * 4]
        return Image.frombytes('RGBA', (p_w, p_h), pix)
    elif p_fmt == 0x13:
        pal_raw = p_tmx[0x40 : 0x440]
        pal = [(pal_raw[i*4], pal_raw[i*4+1], pal_raw[i*4+2], min(255, pal_raw[i*4+3]*2)) for i in range(256)]
        pix = p_tmx[0x440 : 0x440 + p_w * p_h]
        im = Image.new('RGBA', (p_w, p_h))
        im.putdata([pal[idx] for idx in pix])
        return im
    elif p_fmt == 0x14:
        pal_raw = p_tmx[0x38 : 0x78]
        pal = [(pal_raw[i*4], pal_raw[i*4+1], pal_raw[i*4+2], min(255, pal_raw[i*4+3]*2)) for i in range(16)]
        pix_raw = p_tmx[0x78 : 0x78 + (p_w * p_h)//2]
        im = Image.new('RGBA', (p_w, p_h))
        pixels = []
        for b in pix_raw:
            pixels.append(pal[b & 0x0f])
            pixels.append(pal[(b >> 4) & 0x0f])
        im.putdata(pixels)
        return im
    else:
        raise ValueError(f"Unsupported PC TMX format: {hex(p_fmt)}")

def decode_vita_8bpp_tmx(tmx_bytes):
    w, h = struct.unpack('<HH', tmx_bytes[0x12:0x16])
    pal_raw = tmx_bytes[0x40:0x440]
    pal = [None]*256
    for i in range(256):
        r, g, b, a = pal_raw[i*4:(i+1)*4]
        pal[i] = (r, g, b, min(255, a*2))
    pal_unsw = [pal[swizzle_palette_index(i)] for i in range(256)]
    pix = tmx_bytes[0x440:0x440 + w*h]
    im = Image.new('RGBA', (w, h))
    im.putdata([pal_unsw[idx] for idx in pix])
    return im

def draw_inv_triangle(draw, x, y, size=8, color=(255, 255, 255, 255)):
    pts = [(x, y), (x + size, y), (x + size / 2.0, y + size * 0.85)]
    draw.polygon(pts, outline=color)

def make_ch8_tex10(im):
    crop = im.crop((45, 20, 428, 138))
    w, h = crop.size
    
    new_pix = []
    for y in range(h):
        for x in range(w):
            t = y / float(h)
            r = int(32 * (1 - t) + 40 * t)
            g = int(36 * (1 - t) + 44 * t)
            b = int(40 * (1 - t) + 48 * t)
            new_pix.append((r, g, b, 255))
    clean = Image.new('RGBA', (w, h))
    clean.putdata(new_pix)
    
    mask = Image.new('L', (w, h), 255)
    for i in range(12):
        val = int(255 * (i / 12.0))
        for x in range(w):
            mask.putpixel((x, i), min(mask.getpixel((x, i)), val))
            mask.putpixel((x, h - 1 - i), min(mask.getpixel((x, h - 1 - i)), val))
        for y in range(h):
            mask.putpixel((i, y), min(mask.getpixel((i, y)), val))
            mask.putpixel((w - 1 - i, y), min(mask.getpixel((w - 1 - i, y)), val))
            
    res = Image.composite(clean, crop, mask)
    im.paste(res, (45, 20))
    
    draw = ImageDraw.Draw(im)
    try:
        font_reg = ImageFont.truetype('segoeui.ttf', 16)
        font_bold = ImageFont.truetype('segoeuib.ttf', 15)
        font_caps = ImageFont.truetype('segoeuib.ttf', 14)
    except:
        font_reg = ImageFont.load_default()
        font_bold = ImageFont.load_default()
        font_caps = ImageFont.load_default()
        
    draw.text((54, 25), "Rivivi la storia della celebre serie RPG", font=font_reg, fill=(0, 0, 0, 220))
    draw.text((53, 24), "Rivivi la storia della celebre serie RPG", font=font_reg, fill=(255, 255, 255, 255))
    
    draw.text((54, 46), "Persona con i capitoli che hanno preceduto P4G:", font=font_reg, fill=(0, 0, 0, 220))
    draw.text((53, 45), "Persona con i capitoli che hanno preceduto P4G:", font=font_reg, fill=(255, 255, 255, 255))

    y3 = 68
    x = 53
    draw_inv_triangle(draw, x, y3 + 4, size=9)
    x += 12
    draw.text((x + 1, y3 + 1), "PERSONA", font=font_caps, fill=(0, 0, 0, 220))
    draw.text((x, y3), "PERSONA", font=font_caps, fill=(255, 255, 255, 255))
    x += int(draw.textlength("PERSONA", font=font_caps)) + 3
    draw_inv_triangle(draw, x, y3 + 4, size=9)
    x += 15
    draw.text((x + 1, y3 + 1), "PERSONA 3", font=font_caps, fill=(0, 0, 0, 220))
    draw.text((x, y3), "PERSONA 3", font=font_caps, fill=(255, 255, 255, 255))
    x += int(draw.textlength("PERSONA 3", font=font_caps)) + 3
    draw_inv_triangle(draw, x, y3 + 4, size=9)

    y4 = 90
    x = 53
    draw_inv_triangle(draw, x, y4 + 4, size=9)
    x += 12
    draw.text((x + 1, y4 + 1), "PERSONA 3 PORTABLE", font=font_caps, fill=(0, 0, 0, 220))
    draw.text((x, y4), "PERSONA 3 PORTABLE", font=font_caps, fill=(255, 255, 255, 255))
    x += int(draw.textlength("PERSONA 3 PORTABLE", font=font_caps)) + 3
    draw_inv_triangle(draw, x, y4 + 4, size=9)

    y5 = 112
    x = 53
    draw.text((x + 1, y5 + 1), "PERSONA 4", font=font_caps, fill=(0, 0, 0, 220))
    draw.text((x, y5), "PERSONA 4", font=font_caps, fill=(255, 255, 255, 255))
    x += int(draw.textlength("PERSONA 4", font=font_caps)) + 16
    draw.text((x + 1, y5 + 1), "...e molti altri!", font=font_bold, fill=(0, 0, 0, 220))
    draw.text((x, y5), "...e molti altri!", font=font_bold, fill=(255, 255, 255, 255))
    return im

def make_ch8_tex11(im):
    grad = Image.new('RGBA', im.size, (0, 0, 0, 0))
    draw_g = ImageDraw.Draw(grad)

    for y in range(5, 145):
        t = (y - 5) / (145 - 5)
        r = int(0 * (1 - t) + 0 * t)
        g = int(200 * (1 - t) + 95 * t)
        b = int(255 * (1 - t) + 210 * t)
        draw_g.line([(60, y), (430, y)], fill=(r, g, b, 255))

    mask = Image.new('L', im.size, 0)
    draw_m = ImageDraw.Draw(mask)
    poly = [(63, 6), (430, 6), (430, 130), (250, 130), (250, 142), (63, 142)]
    draw_m.polygon(poly, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=2.5))

    im_blended = Image.composite(grad, im, mask)

    draw = ImageDraw.Draw(im_blended)
    try:
        font = ImageFont.truetype('segoeuib.ttf', 15)
    except:
        font = ImageFont.load_default()

    lines = [
        ("Un nuovo, sorprendente capitolo della serie", 15),
        ("Persona! I personaggi di P3 e P4 tornano", 34),
        ("in una lotta per la sopravvivenza!", 53),
        ("Perché combattono? Cosa ha fatto tornare", 72),
        ("il Canale di Mezzanotte? Scoprilo", 91),
        ("in Persona 4 Arena!", 110),
    ]
    for text, y_pos in lines:
        draw.text((68, y_pos), text, font=font, fill=(235, 20, 45, 255), stroke_width=2, stroke_fill=(255, 255, 255, 255))
    return im_blended

def make_ch8_tex12(im):
    crop = im.crop((35, 10, 425, 180))
    clean = crop.filter(ImageFilter.MaxFilter(size=9)).filter(ImageFilter.GaussianBlur(radius=1.2))
    im.paste(clean, (35, 10))
    
    draw = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype('segoeuib.ttf', 16)
        font_nt = ImageFont.truetype('segoeuib.ttf', 14)
    except:
        font = ImageFont.load_default()
        font_nt = ImageFont.load_default()
        
    lines = [
        ("Chie, Yosuke, Yukiko e gli altri tornano...", font, 18),
        ("in versione animata! Rivivi i giorni d'oro", font, 40),
        ("del caso di Inaba in Persona 4 the Animation.", font, 62),
        ("NOTA: Questo è un trailer giapponese", font_nt, 108),
        ("con informazioni sull'uscita della serie", font_nt, 128),
        ("in Giappone.", font_nt, 148),
    ]
    for text, fnt, y_pos in lines:
        draw.text((55, y_pos), text, font=fnt, fill=(30, 15, 0, 255), stroke_width=2, stroke_fill=(255, 180, 20, 255))
    return im

def build_localized_channel_main(v_arc_bytes, p_arc_bytes):
    print("Building localized channelMain.arc (TV Listings Guide)...")
    from build_full_italian_cpk import parse_arc, build_arc
    v_files = parse_arc(v_arc_bytes)
    p_files = parse_arc(p_arc_bytes)
    
    v_spr = bytearray(v_files['tv_listings02spr.spr'])
    p_spr = p_files['tv_listings02spr.spr']
    
    v_num_tex, _, v_tex_off_ptr, _ = struct.unpack('<HHII', v_spr[0x14:0x20])
    p_num_tex, _, p_tex_off_ptr, _ = struct.unpack('<HHII', p_spr[0x14:0x20])
    
    replace_indices = [2, 3, 4, 6, 7, 8, 9, 13, 14]
    for tidx in replace_indices:
        v_t_off = struct.unpack('<II', v_spr[v_tex_off_ptr + tidx*8 : v_tex_off_ptr + (tidx+1)*8])[1]
        p_t_off = struct.unpack('<II', p_spr[p_tex_off_ptr + tidx*8 : p_tex_off_ptr + (tidx+1)*8])[1]
        
        v_tmx = v_spr[v_t_off:]
        v_w, v_h = struct.unpack('<HH', v_tmx[0x12:0x16])
        v_wrap_sz = struct.unpack('<I', v_tmx[4:8])[0]
        v_name = v_tmx[0x24:0x40]
        
        p_tmx = p_spr[p_t_off:]
        p_img = decode_pc_tmx_to_rgba(p_tmx)
        p_down = p_img.resize((v_w, v_h), Image.Resampling.LANCZOS)
        
        new_tmx = encode_8bpp_tmx(p_down, v_name, orig_fmt=v_tmx[0x16])
        assert len(new_tmx) == v_wrap_sz
        v_spr[v_t_off : v_t_off + len(new_tmx)] = new_tmx
        
    # Localize Tex 1 (Live concert description)
    t1_off = struct.unpack('<II', v_spr[v_tex_off_ptr + 1*8 : v_tex_off_ptr + 2*8])[1]
    t1_tmx = v_spr[t1_off:]
    t1_w, t1_h = struct.unpack('<HH', t1_tmx[0x12:0x16])
    t1_name = t1_tmx[0x24:0x40]
    pal_raw1 = t1_tmx[0x40:0x440]
    pal1 = [None]*256
    for i in range(256):
        r, g, b, a = pal_raw1[i*4:(i+1)*4]
        pal1[i] = (r, g, b, min(255, a*2))
    pal1_unsw = [pal1[swizzle_palette_index(i)] for i in range(256)]
    pix1 = t1_tmx[0x440:0x440 + t1_w*t1_h]
    im1 = Image.new('RGBA', (t1_w, t1_h))
    im1.putdata([pal1_unsw[idx] for idx in pix1])
    for y in range(105):
        for x in range(480):
            im1.putpixel((x, y), (0, 0, 0, 0))
    d1 = ImageDraw.Draw(im1)
    try:
        f1 = ImageFont.truetype('arialbd.ttf', 16)
    except:
        f1 = ImageFont.load_default()
    lines1 = [
        'I filmati esclusivi dei concerti live di Persona',
        'ti portano tra il pubblico degli indimenticabili',
        'show del 2008 al BLITZ e del 2009 a Wel City!'
    ]
    y_c = 25
    for l in lines1:
        d1.text((50, y_c), l, font=f1, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(88, 64, 224, 255))
        y_c += 22
    new_t1_tmx = encode_8bpp_tmx(im1, t1_name, orig_fmt=t1_tmx[0x16])
    assert len(new_t1_tmx) == struct.unpack('<I', t1_tmx[4:8])[0]
    v_spr[t1_off : t1_off + len(new_t1_tmx)] = new_t1_tmx

    # Localize Tex 10, 11, 12 (Channel 8: Jacktoons show descriptions)
    ch8_generators = [(10, make_ch8_tex10), (11, make_ch8_tex11), (12, make_ch8_tex12)]
    for tidx, gen_func in ch8_generators:
        v_t_off = struct.unpack('<II', v_spr[v_tex_off_ptr + tidx*8 : v_tex_off_ptr + (tidx+1)*8])[1]
        v_tmx = v_spr[v_t_off:]
        v_wrap_sz = struct.unpack('<I', v_tmx[4:8])[0]
        v_name = v_tmx[0x24:0x40]
        
        orig_img = decode_vita_8bpp_tmx(v_tmx)
        loc_img = gen_func(orig_img)
        new_tmx = encode_8bpp_tmx(loc_img, v_name, orig_fmt=v_tmx[0x16])
        assert len(new_tmx) == v_wrap_sz
        v_spr[v_t_off : v_t_off + len(new_tmx)] = new_tmx

    v_files['tv_listings02spr.spr'] = bytes(v_spr)
    return build_arc(v_files)

def build_localized_lesson_pack(v_pac_bytes, p_pac_bytes):
    print("Building localized title/lesson.pack (Edogawa Lessons)...")
    from build_full_italian_cpk import parse_pac, build_pac, parse_arc, build_arc, replace_accents_safe
    v_files, v_order = parse_pac(v_pac_bytes)
    p_files, _ = parse_pac(p_pac_bytes)
    
    v_ed_spr = bytearray(v_files['edogawaTitle.spr'])
    p_ed_spr = p_files['edogawaTitle.spr']
    
    v_num_tex, _, v_tex_off_ptr, _ = struct.unpack('<HHII', v_ed_spr[0x14:0x20])
    p_num_tex, _, p_tex_off_ptr, _ = struct.unpack('<HHII', p_ed_spr[0x14:0x20])
    
    v_t_off = struct.unpack('<II', v_ed_spr[v_tex_off_ptr + 8 : v_tex_off_ptr + 16])[1]
    p_t_off = struct.unpack('<II', p_ed_spr[p_tex_off_ptr + 8 : p_tex_off_ptr + 16])[1]
    
    p_tmx = p_ed_spr[p_t_off:]
    p_img = decode_pc_tmx_to_rgba(p_tmx)
    p_down = p_img.resize((512, 512), Image.Resampling.LANCZOS)
    
    pal_raw = v_ed_spr[v_t_off + 0x38 : v_t_off + 0x78]
    new_pix = encode_4bpp_rgba(p_down, pal_raw)
    assert len(new_pix) == 512 * 512 // 2
    v_ed_spr[v_t_off + 0x78 : v_t_off + 0x78 + len(new_pix)] = new_pix
    v_files['edogawaTitle.spr'] = bytes(v_ed_spr)
    
    for fn in v_order:
        if fn.startswith('lesson') and fn.endswith('.arc') and fn in p_files:
            v_arc = parse_arc(v_files[fn])
            p_arc = parse_arc(p_files[fn])
            if 'lesson.bmd' in p_arc:
                v_arc['lesson.bmd'] = replace_accents_safe(p_arc['lesson.bmd'])
            v_files[fn] = build_arc(v_arc)
            
    return build_pac(v_files, v_order)

def build_localized_art_ch_arc(v_arc_bytes, p_arc_bytes):
    print("Building localized title/artCh.arc (Art Gallery)...")
    from build_full_italian_cpk import parse_arc, build_arc, replace_accents_safe
    v_files = parse_arc(v_arc_bytes)
    p_files = parse_arc(p_arc_bytes)
    
    v_spr = bytearray(v_files['artTitle.spr'])
    p_spr = p_files['artTitle.spr']
    
    v_num_tex, _, v_tex_off_ptr, _ = struct.unpack('<HHII', v_spr[0x14:0x20])
    p_num_tex, _, p_tex_off_ptr, _ = struct.unpack('<HHII', p_spr[0x14:0x20])
    
    for tidx in [0, 1, 3]:
        v_t_off = struct.unpack('<II', v_spr[v_tex_off_ptr + tidx*8 : v_tex_off_ptr + (tidx+1)*8])[1]
        p_t_off = struct.unpack('<II', p_spr[p_tex_off_ptr + tidx*8 : p_tex_off_ptr + (tidx+1)*8])[1]
        
        v_tmx = v_spr[v_t_off:]
        v_w, v_h = struct.unpack('<HH', v_tmx[0x12:0x16])
        v_wrap_sz = struct.unpack('<I', v_tmx[4:8])[0]
        v_name = v_tmx[0x24:0x40]
        
        p_tmx = p_spr[p_t_off:]
        p_img = decode_pc_tmx_to_rgba(p_tmx)
        p_down = p_img.resize((v_w, v_h), Image.Resampling.LANCZOS)
        
        new_tmx = encode_8bpp_tmx(p_down, v_name, orig_fmt=v_tmx[0x16])
        assert len(new_tmx) == v_wrap_sz
        v_spr[v_t_off : v_t_off + len(new_tmx)] = new_tmx
        
    v_files['artTitle.spr'] = bytes(v_spr)
    if 'artCh.bmd' in p_files:
        v_files['artCh.bmd'] = replace_accents_safe(p_files['artCh.bmd'])
        
    return build_arc(v_files)

def build_localized_quiz_pack(v_pac_bytes, p_pac_bytes):
    print("Building localized title/quiz.pack (Midnight Quiz)...")
    from build_full_italian_cpk import parse_pac, build_pac
    v_files, v_order = parse_pac(v_pac_bytes)
    p_files, _ = parse_pac(p_pac_bytes)
    
    v_spr = bytearray(v_files['quizTitle.spr'])
    p_spr = p_files['quizTitle.spr']
    v_num_tex, _, v_tex_off_ptr, _ = struct.unpack('<HHII', v_spr[0x14:0x20])
    p_num_tex, _, p_tex_off_ptr, _ = struct.unpack('<HHII', p_spr[0x14:0x20])
    
    for tidx in [0, 1]:
        v_t_off = struct.unpack('<II', v_spr[v_tex_off_ptr + tidx*8 : v_tex_off_ptr + (tidx+1)*8])[1]
        p_t_off = struct.unpack('<II', p_spr[p_tex_off_ptr + tidx*8 : p_tex_off_ptr + (tidx+1)*8])[1]
        
        v_tmx = v_spr[v_t_off:]
        v_w, v_h = struct.unpack('<HH', v_tmx[0x12:0x16])
        v_wrap_sz = struct.unpack('<I', v_tmx[4:8])[0]
        v_name = v_tmx[0x24:0x40]
        
        p_tmx = p_spr[p_t_off:]
        p_img = decode_pc_tmx_to_rgba(p_tmx)
        p_down = p_img.resize((v_w, v_h), Image.Resampling.LANCZOS)
        
        new_tmx = encode_8bpp_tmx(p_down, v_name, orig_fmt=v_tmx[0x16])
        assert len(new_tmx) == v_wrap_sz
        v_spr[v_t_off : v_t_off + len(new_tmx)] = new_tmx
    v_files['quizTitle.spr'] = bytes(v_spr)
    
    for k in ['telop_00_in.spr', 'telop_00_out.spr', 'telop_01_in.spr', 'telop_01_out.spr', 'telop_02_in.spr', 'telop_02_out.spr']:
        if k in v_files and k in p_files:
            v_t_spr = bytearray(v_files[k])
            p_t_spr = p_files[k]
            
            v_t_off = struct.unpack('<II', v_t_spr[0x20:0x28])[1]
            p_t_off = struct.unpack('<II', p_t_spr[0x20:0x28])[1]
            
            p_tmx = p_t_spr[p_t_off:]
            p_img = decode_pc_tmx_to_rgba(p_tmx)
            p_down = p_img.resize((1024, 1024), Image.Resampling.LANCZOS)
            
            pal_raw = v_t_spr[v_t_off + 0x38 : v_t_off + 0x78]
            new_pix = encode_4bpp_rgba(p_down, pal_raw)
            assert len(new_pix) == 1024 * 1024 // 2
            v_t_spr[v_t_off + 0x78 : v_t_off + 0x78 + len(new_pix)] = new_pix
            v_files[k] = bytes(v_t_spr)
            
    return build_pac(v_files, v_order)

def build_localized_music_ch_arc(v_arc_bytes, p_arc_bytes):
    print("Building localized title/musicCh.arc (Music Channel)...")
    from build_full_italian_cpk import parse_arc, build_arc
    v_files = parse_arc(v_arc_bytes)
    p_files = parse_arc(p_arc_bytes)
    
    # 1. misic_ch.spr Tex 0 ("Raccolta battaglie/dungeon", "Raccolta eventi", "Raccolta voci")
    if 'misic_ch.spr' in v_files and 'misic_ch.spr' in p_files:
        v_m_spr = bytearray(v_files['misic_ch.spr'])
        p_m_spr = p_files['misic_ch.spr']
        v_m_off = struct.unpack('<II', v_m_spr[0x20:0x28])[1]
        p_m_off = struct.unpack('<II', p_m_spr[0x20:0x28])[1]
        p_m_tmx = p_m_spr[p_m_off:]
        p_m_img = decode_pc_tmx_to_rgba(p_m_tmx)
        p_m_down = p_m_img.resize((512, 128), Image.Resampling.LANCZOS)
        pal_raw_m = v_m_spr[v_m_off + 0x38 : v_m_off + 0x78]
        new_m_pix = encode_4bpp_rgba(p_m_down, pal_raw_m)
        v_m_spr[v_m_off + 0x78 : v_m_off + 0x78 + len(new_m_pix)] = new_m_pix
        v_files['misic_ch.spr'] = bytes(v_m_spr)
    
    # 2. heyheihoo_spr01.spr: Tex 1 and Tex 3 (Persona 3 show banners)
    v_spr = bytearray(v_files['heyheihoo_spr01.spr'])
    p_spr = p_files['heyheihoo_spr01.spr']
    
    v_num_tex, _, v_tex_off_ptr, _ = struct.unpack('<HHII', v_spr[0x14:0x20])
    p_num_tex, _, p_tex_off_ptr, _ = struct.unpack('<HHII', p_spr[0x14:0x20])
    
    for tidx in [1, 3]:
        v_t_off = struct.unpack('<II', v_spr[v_tex_off_ptr + tidx*8 : v_tex_off_ptr + (tidx+1)*8])[1]
        p_t_off = struct.unpack('<II', p_spr[p_tex_off_ptr + tidx*8 : p_tex_off_ptr + (tidx+1)*8])[1]
        
        v_tmx = v_spr[v_t_off:]
        v_w, v_h = struct.unpack('<HH', v_tmx[0x12:0x16])
        v_wrap_sz = struct.unpack('<I', v_tmx[4:8])[0]
        v_name = v_tmx[0x24:0x40]
        
        p_tmx = p_spr[p_t_off:]
        p_img = decode_pc_tmx_to_rgba(p_tmx)
        p_down = p_img.resize((v_w, v_h), Image.Resampling.LANCZOS)
        
        new_tmx = encode_8bpp_tmx(p_down, v_name, orig_fmt=v_tmx[0x16])
        assert len(new_tmx) == v_wrap_sz
        v_spr[v_t_off : v_t_off + len(new_tmx)] = new_tmx
        
    v_files['heyheihoo_spr01.spr'] = bytes(v_spr)
    return build_arc(v_files)

def build_localized_live_ch_arc(v_arc_bytes, p_arc_bytes):
    print("Building localized title/liveCh.arc (Persona Live)...")
    from build_full_italian_cpk import parse_arc, build_arc
    v_files = parse_arc(v_arc_bytes)
    p_files = parse_arc(p_arc_bytes)
    
    v_spr = bytearray(v_files['liveTitle.spr'])
    p_spr = p_files['liveTitle.spr']
    
    v_t_off = struct.unpack('<II', v_spr[0x20:0x28])[1]
    p_t_off = struct.unpack('<II', p_spr[0x20:0x28])[1]
    
    v_tmx = v_spr[v_t_off:]
    v_w, v_h = struct.unpack('<HH', v_tmx[0x12:0x16])
    v_wrap_sz = struct.unpack('<I', v_tmx[4:8])[0]
    v_name = v_tmx[0x24:0x40]
    
    p_tmx = p_spr[p_t_off:]
    p_img = decode_pc_tmx_to_rgba(p_tmx)
    p_down = p_img.resize((v_w, v_h), Image.Resampling.LANCZOS)
    
    new_tmx = encode_8bpp_tmx(p_down, v_name, orig_fmt=v_tmx[0x16])
    assert len(new_tmx) == v_wrap_sz
    v_spr[v_t_off : v_t_off + len(new_tmx)] = new_tmx
    
    v_files['liveTitle.spr'] = bytes(v_spr)
    return build_arc(v_files)

def build_localized_anim_ch_arc(v_arc_bytes, p_arc_bytes):
    print("Building localized title/animCh.arc (Persona Animation)...")
    from build_full_italian_cpk import parse_arc, build_arc, replace_accents_safe
    v_files = parse_arc(v_arc_bytes)
    p_files = parse_arc(p_arc_bytes)
    
    v_spr = bytearray(v_files['peraniland_01spr.spr'])
    p_spr = p_files['peraniland_01spr.spr']
    v_num_tex, _, v_tex_off_ptr, _ = struct.unpack('<HHII', v_spr[0x14:0x20])
    p_num_tex, _, p_tex_off_ptr, _ = struct.unpack('<HHII', p_spr[0x14:0x20])
    
    for tidx in [0, 1]:
        v_t_off = struct.unpack('<II', v_spr[v_tex_off_ptr + tidx*8 : v_tex_off_ptr + (tidx+1)*8])[1]
        p_t_off = struct.unpack('<II', p_spr[p_tex_off_ptr + tidx*8 : p_tex_off_ptr + (tidx+1)*8])[1]
        
        v_tmx = v_spr[v_t_off:]
        v_w, v_h = struct.unpack('<HH', v_tmx[0x12:0x16])
        v_wrap_sz = struct.unpack('<I', v_tmx[4:8])[0]
        v_name = v_tmx[0x24:0x40]
        
        p_tmx = p_spr[p_t_off:]
        p_img = decode_pc_tmx_to_rgba(p_tmx)
        p_down = p_img.resize((v_w, v_h), Image.Resampling.LANCZOS)
        
        new_tmx = encode_8bpp_tmx(p_down, v_name, orig_fmt=v_tmx[0x16])
        assert len(new_tmx) == v_wrap_sz
        v_spr[v_t_off : v_t_off + len(new_tmx)] = new_tmx
        
    v_files['peraniland_01spr.spr'] = bytes(v_spr)
    if 'animCh.bmd' in p_files:
        v_files['animCh.bmd'] = replace_accents_safe(p_files['animCh.bmd'])
        
    return build_arc(v_files)

def build_localized_quiz_arc(v_arc_bytes, p_arc_bytes):
    print("Building localized title/quiz.arc (Quiz in-game)...")
    from build_full_italian_cpk import parse_arc, build_arc, replace_accents_safe
    v_files = parse_arc(v_arc_bytes)
    p_files = parse_arc(p_arc_bytes)
    
    v_spr = bytearray(v_files['quiz.spr'])
    p_spr = p_files['quiz.spr']
    v_num_tex, _, v_tex_off_ptr, _ = struct.unpack('<HHII', v_spr[0x14:0x20])
    p_num_tex, _, p_tex_off_ptr, _ = struct.unpack('<HHII', p_spr[0x14:0x20])
    
    for tidx in [0, 4]: # Tex 0: question_pn ("Corretto", "Punti", "Avanti"), Tex 4: time_guage ("Tempo limite")
        v_t_off = struct.unpack('<II', v_spr[v_tex_off_ptr + tidx*8 : v_tex_off_ptr + (tidx+1)*8])[1]
        p_t_off = struct.unpack('<II', p_spr[p_tex_off_ptr + tidx*8 : p_tex_off_ptr + (tidx+1)*8])[1]
        
        v_tmx = v_spr[v_t_off:]
        v_w, v_h = struct.unpack('<HH', v_tmx[0x12:0x16])
        v_wrap_sz = struct.unpack('<I', v_tmx[4:8])[0]
        v_name = v_tmx[0x24:0x40]
        
        p_tmx = p_spr[p_t_off:]
        p_img = decode_pc_tmx_to_rgba(p_tmx)
        p_down = p_img.resize((v_w, v_h), Image.Resampling.LANCZOS)
        
        new_tmx = encode_8bpp_tmx(p_down, v_name, orig_fmt=v_tmx[0x16])
        assert len(new_tmx) == v_wrap_sz
        v_spr[v_t_off : v_t_off + len(new_tmx)] = new_tmx
        
    v_files['quiz.spr'] = bytes(v_spr)
    
    for bmd_name in ['msg_quiz.bmd', 'msg_quiz_system.bmd', 'msg_quiz_answer.bmd']:
        if bmd_name in p_files:
            v_files[bmd_name] = replace_accents_safe(p_files[bmd_name])
            
    return build_arc(v_files)
