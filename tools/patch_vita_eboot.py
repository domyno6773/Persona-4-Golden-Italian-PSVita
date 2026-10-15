import struct
import os
import shutil
import subprocess

def patch_eboot():
    base_elf_path = "E:/FAGDec/app/PCSB00245/eboot.bin.elf"
    clean_fself_path = "E:/FAGDec/app/PCSB00245/eboot.bin"
    output_elf_path = "patched_eboot.elf"
    output_fself_path = "patched_eboot.bin"

    print(f"Reading base ELF: {base_elf_path}...")
    with open(base_elf_path, "rb") as f:
        elf = bytearray(f.read())

    # Helper: write fixed-length string padded with nulls
    def write_fixed_str(offset, text, total_len):
        raw = text.encode('latin1')
        assert len(raw) < total_len, f"String '{text}' ({len(raw)} bytes) too long for slot {total_len}"
        slot = raw + b'\x00' * (total_len - len(raw))
        elf[offset : offset + total_len] = slot

    # 1. Name Entry Prompts (0x3b94c8, 0x3b94e0)
    print("Patching Name Entry Prompts...")
    write_fixed_str(0x3b94c8, "Inserisci il cognome", 24)
    write_fixed_str(0x3b94e0, "Inserisci il nome", 24)

    # 2. In-Game Field Locations (0x415dda, 108 entries, each 26 bytes)
    print("Patching Bottom-Left In-Game Field Locations (108 entries)...")
    field_locs = [
        "Edificio aule, 1P",          # 0: Classroom Building, 1F
        "Edificio aule, 2P",          # 1: Classroom Building, 2F
        "Edificio aule, 3P",          # 2: Classroom Building, 3F
        "Edificio laboratori, 1P",    # 3: Practice Building, 1F
        "Edificio laboratori, 2P",    # 4: Practice Building, 2F
        "Aula 1-1",                   # 5: Class 1-1
        "Aula 1-2",                   # 6: Class 1-2
        "Aula 1-3",                   # 7: Class 1-3
        "Aula 1-4",                   # 8: Class 1-4
        "Aula 1-5",                   # 9: Class 1-5
        "Sala docenti",               # 10: Faculty Office
        "Infermeria",                 # 11: Nurse's Office
        "Ufficio consulente",         # 12: Counselor's Office
        "Bagno degli uomini",         # 13: Men's Bathroom
        "Bagno delle donne",          # 14: Women's Bathroom
        "Uscita d'emergenza",         # 15: Emergency Exit
        "Aula 2-1",                   # 16: Class 2-1
        "Aula 2-2",                   # 17: Class 2-2
        "Aula 2-3",                   # 18: Class 2-3
        "Aula 2-4",                   # 19: Class 2-4
        "Aula 2-5",                   # 20: Class 2-5
        "Aula di Calligrafia",        # 21: Calligraphy Room
        "Consiglio studentesco",      # 22: Student Council Room
        "Biblioteca",                 # 23: Library
        "Aula 3-1",                   # 24: Class 3-1
        "Aula 3-2",                   # 25: Class 3-2
        "Aula 3-3",                   # 26: Class 3-3
        "Aula 3-4",                   # 27: Class 3-4
        "Aula 3-5",                   # 28: Class 3-5
        "Sala comunicazioni",         # 29: Announcement Room
        "Aula computer",              # 30: Computer Lab
        "Aula audiovisivi",           # 31: A/V Room
        "Tetto",                      # 32: Roof
        "Aula riunioni",              # 33: Meeting Room
        "Aula di Scienze",            # 34: Science Room
        "Aula Economia domestica",    # 35: Home Ec Room
        "Aula di Cucito",             # 36: Sewing Room
        "Magazzino di Musica",        # 37: Storage Room
        "Aula di Musica",             # 38: Music Room
        "Aula di Biologia",           # 39: Biology Lab
        "Aula di Arte",               # 40: Art Room
        "Laboratorio",                # 41: Workshop
        "Aula di Inglese",            # 42: English Classroom
        "Aula di Sociologia",         # 43: Sociology Classroom
        "Casa Dojima, ingresso",      # 44: Dojima Residence
        "Salotto",                    # 45: Living Room
        "La tua stanza",              # 46: Your Room
        "Area comm. nord",            # 47: Shopping District, North
        "Area comm. sud",             # 48: Shopping District, South
        "Stazione servizio Moel",     # 49: Moel Gas
        "Libreria Yomenaido",         # 50: Yomenaido Bookstore
        "Stanza di Velluto",          # 51: Velvet Room
        "Fonderia Daidara",           # 52: Daidara Metalworks
        "Marukyu Tofu",               # 53: Marukyu Tofu
        "Bottega Shiroku",            # 54: Shiroku Store
        "Fermata dell'autobus",       # 55: Bus Stop
        "Ristorante cinese Aiya",     # 56: Chinese Diner Aiya
        "Bacheca cittadina",          # 57: Town Bulletin Board
        "Souzai Daigaku",             # 58: Souzai Daigaku
        "Marutake Modellismo",        # 59: Marutake Hobby Shop
        "Santuario Tatsuhime",        # 60: Tatsuhime Shrine
        "Tatsumi Tessuti",            # 61: Tatsumi Textiles
        "Konishi Alcolici",           # 62: Konishi Liquors
        "Junes, entrata ovest",       # 63: Junes, West Entrance
        "Ascensore",                  # 64: Elevator
        "Area ristorazione",          # 65: Food Court
        "Banchina fiume Samegawa",    # 66: Samegawa Flood Plain
        "Liceo Yasogami, entrata",    # 67: Yasogami Front Gate
        "Punto di salvataggio",       # 68: Save Point
        "Armadietto scarpe",          # 69: Your Shoe Locker
        "Corridoio palestra",         # 70: Hallway to the Field
        "Esci",                       # 71: Go Outside
        "TV",                         # 72: TV
        "Frigorifero",                # 73: Fridge
        "Futon",                      # 74: Futon
        "Scrivania",                  # 75: Study Desk
        "Tavolo da lavoro",           # 76: Work Table
        "Divano",                     # 77: Sofa
        "Tavolo della cucina",        # 78: Kitchen
        "Laboratorio",                # 79: Science Lab
        "Molo",                       # 80: Dock
        "Cespuglio",                  # 81: Bushes
        "Cassetta della posta",       # 82: Mailbox
        "Distributore automatico",    # 83: Vending Machine
        "Barbiere",                   # 84: Barber
        "Negozio di biciclette",      # 85: Bicycle Shop
        "Scaffali a tre ripiani",     # 86: Shelf
        "Bacheca",                    # 87: Notice Board
        "Cuscino",                    # 88: Cushion
        "Negozio chiuso",             # 89: Closed Store
        "Farmacia",                   # 90: Pharmacy
        "Negozio di elettronica",     # 91: Electronics Store
        "Distributore Gachapon",      # 92: Capsule Machine
        "Decorazione del Tanabata",   # 93: Tanabata Decoration
        "Calendario",                 # 94: Calendar
        "Attrezzi da giardinaggio",   # 95: Gardening Tools
        "Ingresso",                   # 96: Entrance
        "La tua stanza",              # 97: Your Room
        "Attrezzatura per pesca",     # 98: Fishing Equipment
        "Area della scuola",          # 99: School Zone
        "Banchetto ortofrutta",       # 100: Vegetable Stand
        "Poster in negozio",          # 101: Store Poster
        "Riva del fiume",             # 102: Stairs
        "Letto del fiume",            # 103: Stairs
        "Salone principale",          # 104: Main Hall
        "Santuario",                  # 105: Yashiro
        "Banchetto degli ema",        # 106: Ema Hanger
        "Supporto divinazioni"        # 107: Fortune Hanger
    ]
    assert len(field_locs) == 108, f"Expected 108 entries, got {len(field_locs)}"

    field_base = 0x415dda
    stride = 26
    for idx, text in enumerate(field_locs):
        write_fixed_str(field_base + idx * stride, text, stride)

    # 6. Network & System Modals
    print("Patching Network & System Modals (34 dialogs)...")
    PSN = b'\xf5\xc1\x06\x01\x01\x01\x01\x01\x01\x01'
    PRE = b'\xf2\x05\xff\xff\xf1A'

    modal_patches = {
        # 0x3f6204 (slot 172)
        0x3f6204: (172, PRE + b"Da questo punto la trama subira' colpi di\nscena. Ti consigliamo di approfittarne\nper salvare. Vuoi salvare la partita adesso?\n"),
        # 0x3f62c0 (slot 60)
        0x3f62c0: (60, PRE + b"Vuoi continuare senza salvare la partita?\n"),
        # 0x3f62fc (slot 53)
        0x3f62fc: (53, PRE + b"Vuoi salvare i progressi fatti finora?\n"),
        # 0x3f6344 (slot 44)
        0x3f6344: (44, PRE + b"Sei sicuro di non voler salvare?\n"),
        # 0x3f6374 (slot 132)
        0x3f6374: (132, PRE + b"Connettendoti a PlayStation" + PSN + b"Network potrai\nusare varie funzionalita' di gioco.\nVuoi effettuare la connessione?\n"),
        # 0x3f63fc (slot 114)
        0x3f63fc: (114, PRE + b"Avvio del gioco in modalita' online.\nPer giocare offline, imposta in Config:\n\"Funzioni di rete\" su OFF.\n"),
        # 0x3f6470 (slot 77)
        0x3f6470: (77, PRE + b"Avvio del gioco con le funzionalita' di\nrete disattivate. Continuare?\n"),
        # 0x3f64c0 (slot 73)
        0x3f64c0: (73, PRE + b"Connessione a PlayStation" + PSN + b"Network fallita.\nRiprovare?\n"),
        # 0x3f650c (slot 131)
        0x3f650c: (131, PRE + b"Non hai effettuato l'accesso a PSN.\nLe funzioni di soccorso e Vox Populi\nsono disattivate. Vuoi accedere?\n"),
        # 0x3f6590 (slot 116) - PHOTO 1
        0x3f6590: (116, PRE + b"Avvio del gioco in modalita' offline.\nPer giocare online, imposta in Config:\n\"Funzionalita' di rete\" su ON.\n"),
        # 0x3f6604 (slot 124)
        0x3f6604: (124, PRE + b"Connessione a PlayStation" + PSN + b"Network fallita\no interrotta. Vuoi tentare di\nriconnetterti?\n"),
        # 0x3f6680 (slot 72)
        0x3f6680: (72, PRE + b"I dati esistono gia'.\nVuoi sovrascrivere questi dati?\n"),
        # 0x3f66c8 (slot 24)
        0x3f66c8: (24, PRE + b"Salvataggio...\n"),
        # 0x3f66e0 (slot 24)
        0x3f66e0: (24, PRE + b"Salvataggio ok.\n"),
        # 0x3f66f8 (slot 20)
        0x3f66f8: (20, PRE + b"Non salvato.\n"),
        # 0x3f670c (slot 24)
        0x3f670c: (24, PRE + b"Caricare il file?\n"),
        # 0x3f6724 (slot 24)
        0x3f6724: (24, PRE + b"Caricamento...\n"),
        # 0x3f673c (slot 24)
        0x3f673c: (24, PRE + b"Caricato.\n"),
        # 0x3f6754 (slot 20)
        0x3f6754: (20, PRE + b"Non caricato.\n"),
        # 0x3f6768 (slot 32)
        0x3f6768: (32, PRE + b"Eliminare il dato?\n"),
        # 0x3f6788 (slot 20)
        0x3f6788: (20, PRE + b"Rimozione...\n"),
        # 0x3f679c (slot 24)
        0x3f679c: (24, PRE + b"Dato eliminato.\n"),
        # 0x3f67b4 (slot 24)
        0x3f67b4: (24, PRE + b"Eliminazione no.\n"),
        # 0x3f67cc (slot 128)
        0x3f67cc: (128, PRE + b"Per via del filtro contenuti, non puoi\nusare funzioni che richiedono la rete\nPlayStation" + PSN + b"Network.\n"),
        # 0x3f684c (slot 68)
        0x3f684c: (68, PRE + b"L'uso di chat e messaggi non e'\npermesso per questo account.\n"),
        # 0x3f6890 (slot 96)
        0x3f6890: (96, PRE + b"Sei in modalita' offline. Le funzioni\ndi rete sono impostate su OFF\nnel menu Config.\n"),
        # 0x3f68f0 (slot 144)
        0x3f68f0: (144, PRE + b"La modalita' aereo e' attiva. Le funzioni\ndi rete sono state disabilitate e\nimpostate su OFF nel menu Config.\n"),
        # 0x3f6980 (slot 28)
        0x3f6980: (28, PRE + b"Saltare la scena?\n"),
        # 0x3f699c (slot 132) - PHOTO 2
        0x3f699c: (132, PRE + b"Connettendoti a PlayStation" + PSN + b"Network\navrai accesso a novita' in Persona 4 Golden.\nVuoi saperne di piu'?\n"),
        # 0x3f6a20 (slot 120)
        0x3f6a20: (120, PRE + b"La funzione \"Vox Populi\" ti permette di\nvedere le scelte degli altri giocatori\nin vari momenti della partita.\n"),
        # 0x3f6a98 (slot 128)
        0x3f6a98: (128, PRE + b"La \"Richiesta soccorso\" permette agli\naltri di aiutarti nelle difficolta',\ne a te di aiutarli a tua volta.\n"),
        # 0x3f6b18 (slot 128)
        0x3f6b18: (128, PRE + b"\x80\x80\nQueste funzioni non sono disponibili da\nsubito. Si sbloccheranno man mano\nche avanzi nella storia.\n"),
        # 0x3f6b98 (slot 168)
        0x3f6b98: (168, PRE + b"Come ricompensa per il completamento,\npuoi trasferire elementi del salvataggio\nin una nuova partita. Vuoi usarli?\n"),
        # 0x3f6c40 (slot 84)
        0x3f6c40: (84, PRE + b"Vuoi iniziare la partita senza usare i\nbonus del completamento?\n")
    }

    for offset, (slot_len, text) in modal_patches.items():
        assert len(text) <= slot_len, f"Modal string too long at {hex(offset)}: {len(text)} > {slot_len}"
        elf[offset : offset + slot_len] = text + b'\x00' * (slot_len - len(text))

    # 7. Name Entry & System Confirmation Prompts
    print("Patching Name Entry & System Confirmation Prompts...")
    # shdWindow.c Yes/No at 0x3ac7a0
    assert elf[0x3ac7a0 : 0x3ac7a0 + 4] == b'Yes\x00'
    elf[0x3ac7a0 : 0x3ac7a0 + 4] = b"Si'\x00"

    # Battle BMD Yes/No at 0x43046a
    assert elf[0x43046a : 0x43046a + 4] == b'Yes\x00'
    elf[0x43046a : 0x43046a + 4] = b"Si'\x00"

    # Name Entry BMD Yes/No at 0x4648c2
    assert elf[0x4648c2 : 0x4648c2 + 4] == b'Yes\x00'
    elf[0x4648c2 : 0x4648c2 + 4] = b"Si'\x00"

    # Name Entry BMD "> Proceed?\n" at 0x4648fa
    assert elf[0x4648fa : 0x4648fa + 11] == b'> Proceed?\n'
    elf[0x4648fa : 0x4648fa + 11] = b'> Procedi?\n'

    # 8. Midnight Channel TV Listings & Show Titles
    print("Patching Midnight Channel TV Listings & Show Titles...")
    tv_patches = {
        # Notifications
        0x45bd10: (24, b", e' in onda.\x00"),
        0x45bd28: (24, b" e' ora disponibile!\x00"),
        0x45bd40: (16, b" e' aggiornato!\x00"),
        # Channel Names
        0x45bd90: (64, b"Arte e intrattenimento\x00"),
        0x45bdd0: (64, b"TV pubblica di Inaba\x00"),
        0x45be10: (64, b"BigTV\x00"),
        0x45be50: (64, b"Canale V\x00"),
        0x45be90: (64, b"PBS\x00"),
        0x45bed0: (64, b"Tatsu TV\x00"),
        0x45bf10: (64, b"Yasovision\x00"),
        0x45bf50: (64, b"Jacktoons\x00"),
        # Show Titles
        0x45bf90: (64, b"Battaglia musicale 2012\x00"),
        0x45bfd0: (64, b"Insegna in TV: lezione 1\x00"),
        0x45c010: (64, b"Insegna in TV: lezione 2\x00"),
        0x45c050: (64, b"Insegna in TV: lezione 3\x00"),
        0x45c090: (64, b"Insegna in TV: lezione 4\x00"),
        0x45c0d0: (64, b"Insegna in TV: lezione 5\x00"),
        0x45c110: (64, b"Insegna in TV: lezione 6\x00"),
        0x45c150: (64, b"Insegna in TV: lezione 7\x00"),
        0x45c190: (64, b"Insegna in TV: lezione 8\x00"),
        0x45c1d0: (64, b"Insegna in TV: lezione 9\x00"),
        0x45c210: (64, b"Insegna in TV: lezione 10\x00"),
        0x45c250: (64, b"Quiz miracoloso: preliminari\x00"),
        0x45c290: (64, b"Quiz miracoloso: eliminatorie\x00"),
        0x45c2d0: (64, b"Quiz miracoloso: finale\x00"),
        0x45c310: (64, b"Personimazioni del giorno!\x00"),
        0x45c650: (64, b"P4 Golden\x00"),
        0x45c690: (64, b"Un'estate in vacanza\x00"),
        0x45c6d0: (64, b"Giganti di P: parte 1\x00"),
        0x45c710: (64, b"Giganti di P: parte 2\x00"),
        0x45c750: (64, b"Giganti di P: parte 3\x00"),
        0x45c790: (64, b"HEE! HEE! HO! Musica da re!\x00"),
        0x45c7d0: (64, b"HEE! HEE! HO! Musica da re!\x00"),
        0x45c810: (64, b"HEE! HEE! HO! Musica da re!\x00"),
        0x45c850: (64, b"Persona Hits\x00"),
        0x45c890: (64, b"Cos'e' P4 Arena?\x00"),
        0x45c8d0: (64, b"P4 the Animation!\x00"),
    }
    for offset, (slot_len, text) in tv_patches.items():
        assert len(text) <= slot_len, f"TV string too long at {hex(offset)}: {len(text)} > {slot_len}"
        elf[offset : offset + slot_len] = text.ljust(slot_len, b'\x00')

    # Verify identical length
    assert len(elf) == 4906167, f"ELF length changed! {len(elf)} vs 4906167"

    # Write patched ELF
    with open(output_elf_path, "wb") as f:
        f.write(elf)
    print(f"Wrote {output_elf_path} ({len(elf)} bytes, exactly matches original ELF size!).")

    # Inject into clean decrypted FSELF
    print(f"Injecting into clean FSELF: {clean_fself_path} -> {output_fself_path}...")
    shutil.copyfile(clean_fself_path, output_fself_path)
    inject_exe = "eboot_patch_tools/Easy-Vita-P4G-EBOOT-Patch-main/PSVita-RE-Tools/vita-elf-inject.exe"
    res = subprocess.run([inject_exe, output_fself_path, output_elf_path], capture_output=True, text=True)
    print(f"Inject returncode: {res.returncode}")
    if res.stdout: print("stdout:", res.stdout)
    assert res.returncode == 0, "vita-elf-inject failed!"

    # Fix hdr_self_filesize at offset 0x20 in SCE header
    with open(output_fself_path, "r+b") as f:
        f.seek(0, 2)
        actual_sz = f.tell()
        f.seek(0x20)
        f.write(struct.pack('<Q', actual_sz))
    print(f"Fixed hdr_self_filesize at 0x20 to {actual_sz} bytes.")
    print(f"Successfully generated {output_fself_path}!")

    # Copy to workspace and Vita
    dest_repatch = "rePatch_PCSB00245/PCSB00245/eboot.bin"
    shutil.copyfile(output_fself_path, dest_repatch)
    print(f"Copied to {dest_repatch}")
    if os.path.exists("E:/rePatch/PCSB00245"):
        shutil.copyfile(output_fself_path, "E:/rePatch/PCSB00245/eboot.bin")
        print("Copied to E:/rePatch/PCSB00245/eboot.bin")

if __name__ == '__main__':
    patch_eboot()

