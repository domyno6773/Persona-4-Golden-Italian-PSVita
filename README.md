# Persona 4 Golden - Traduzione Italiana per PlayStation Vita

![Platform](https://img.shields.io/badge/Platform-PS%20Vita-blue.svg)
![Game](https://img.shields.io/badge/Game-Persona%204%20Golden-yellow.svg)
![Title ID](https://img.shields.io/badge/Title%20ID-PCSB00245%20(EU)-green.svg)
![Version](https://img.shields.io/badge/Release-v1.0.1-orange.svg)
![Language](https://img.shields.io/badge/Language-Italiano-red.svg)
[![Donate with PayPal](https://img.shields.io/badge/Donate-PayPal-00457C.svg?logo=paypal&logoColor=white)](https://www.paypal.com/paypalme/domyno6773)

Patch di traduzione italiana completa e definitiva per **Persona 4 Golden** su **PlayStation Vita (edizione europea PCSB00245)**.

Il progetto porta su console portatile l'intera localizzazione italiana ufficiale realizzata da **Atlus / SEGA** per la versione PC (Steam), integrando correzioni ad hoc per l'hardware della PS Vita, filmati sottotitolati in italiano a risoluzione nativa e texture rielaborate a mano.

---

## 🎮 Caratteristiche della Mod

- **Testi e Dialoghi al 100% in Italiano**: Storia principale, tutti i Social Link, richieste secondarie, lezioni ed esami scolastici, descrizioni di abilità, oggetti, equipaggiamento e Personae.
- **Tutti i 26 Filmati con Sottotitoli in Italiano**: I filmati animati e le cutscene parlate sono stati estratti, sottotitolati con la traduzione ufficiale e ricodificati alla risoluzione nativa della PS Vita (**960x544**, H.264 Main Profile @ Level 4.0, AAC Stereo), garantendo massima nitidezza e sincronizzazione labiale perfetta.
- **Interfaccia Grafica e Texture 2D Riadattate**:
  - Menu di Salvataggio e Caricamento (`mcPanel.arc`): indicatori di slot, data, livello e tempo di gioco.
  - HUD di gioco: giorni della settimana, orari e comandi del diario/cronologia dialoghi.
  - Indicatore di avanzamento veloce ("SALTA" con icona pristine SELECT).
  - Canale Midnight Channel TV (`channelMain.arc`): guida ai programmi di tutti i canali, incluse le descrizioni esclusive di *Persona Hits*, *Persona 4 Arena* e *Persona 4 the Animation*.
  - Schermate educative del Professor Edogawa (`lesson.pack`).
  - Grafica del Quiz di Mezzanotte (`quiz.arc` e `quiz.pack`).
- **Patch dell'Eseguibile (`eboot.bin`)**:
  - Traduzione dei 108 nomi dei luoghi della mappa in basso a sinistra (aule scolastiche, negozi di Inaba, argine Samegawa, ecc.).
  - Traduzione di tutte le 34 finestre di dialogo modali di rete, PlayStation Network, funzioni Vox Populi e Richiesta di Soccorso.
  - Traduzione dei prompt di conferma sistema e inserimento Nome/Cognome.
  - Traduzione dei titoli di tutte le trasmissioni e dei nomi dei canali TV.
- **Ottimizzazione Hardware PS Vita**:
  - Corretta codifica a 8bpp e 4bpp CLUT con palette swizzling specifico per la GPU PowerVR di PS Vita, azzerando qualsiasi artefatto o glitch visivo.
  - Compatibilità totale con salvataggi preesistenti della versione europea.

---

## 📋 Requisiti

1. **PlayStation Vita** o **PlayStation TV** con modifica abilitata (**HENkaku / Enso** su firmware 3.60 o 3.65).
2. Copia originale di **Persona 4 Golden (Edizione Europea - Title ID: `PCSB00245`)**, installata in formato digitale o cartuccia fisica.
3. Plugin **`rePatch`** (consigliato `rePatch reLoaded` o `rePatch v3.0`) installato e configurato in `ur0:tai/config.txt`.
4. Plugin **`0syscall6`** (o `NoNpDrm`) per abilitare l'avvio di file e moduli decrittati.
5. Circa **2.6 GB** di spazio libero sulla scheda di memoria della PS Vita (`ux0:`).

---

## 📥 Istruzioni per l'Installazione

### Metodo Rapido (Drag & Drop via USB / FTP)

1. Vai nella sezione **[Releases](../../releases)** di questo repository e scarica gli archivi:
   - `P4G_Italian_Patch_v1.0.1.zip` (Testi, texture, interfaccia ed eseguibile patchato - Hotfix incluso)
   - `P4G_Italian_Movies_v1.0.0.zip` (26 filmati con sottotitoli italiani a 960x544)
2. Avvia **VitaShell** sulla tua PS Vita e premi **SELECT** per collegare la console al PC tramite cavo USB (oppure connettiti via client FTP).
3. Estrai entrambi i file `.zip` direttamente nella memoria della console:
   - Trascina la cartella `rePatch` contenuta nei pacchetti nella radice della partizione **`ux0:`**.
4. Verifica che la struttura delle cartelle sulla PS Vita corrisponda esattamente a quanto segue:
   ```text
   ux0:
   └── rePatch/
       └── PCSB00245/
           ├── eboot.bin
           └── data/
               ├── data.cpk
               └── movie/
                   ├── P4CT001.mp4
                   ├── P4CT002.mp4
                   ├── ...
                   └── P4CT041.mp4
   ```
5. Premi **Cerchio** su VitaShell per disconnettere la console.
6. Avvia **Persona 4 Golden** dalla LiveArea e goditi l'avventura interamente in italiano!

---

## 📝 Changelog

### v1.0.1 (Hotfix)
- **Risolto il crash `C2-12828-1` nella stanza del protagonista a casa Dojima (sera dell'11 aprile e visite successive)**:
  - Il crash era dovuto a chiamate e istruzioni FlowScript PC introdotte da Atlus nell'update 2023 (Salvataggio rapido / Album) non presenti nel motore PS Vita 2012.
  - Implementato `build_vita_bf.py` che preserva al 100% il bytecode e le procedure native di PS Vita su tutti i 1.091 script di gioco (`.bf`), innestandovi dinamicamente l'intera traduzione italiana ufficiale.
  - Compatibilità e stabilità verificate su hardware reale sia per PS Vita che per PlayStation TV (PSTV).

### v1.0.0
- Rilascio iniziale con testi, filmati, grafica e audio/video ottimizzati per PS Vita.

---

## 🛠️ Come Ricompilare la Patch dai Sorgenti (Per Modder)

Se desideri rigenerare i file di traduzione autonomamente partendo dal gioco originale e dai file della versione Steam:

1. Clona questo repository:
   ```bash
   git clone https://github.com/domyno6773/Persona-4-Golden-Italian-PSVita.git
   cd Persona-4-Golden-Italian-PSVita
   ```
2. Installa i requisiti Python (consigliato Python 3.10+):
   ```bash
   pip install pillow cricodecs
   ```
3. Posiziona nella cartella di lavoro:
   - `clean_vita_data.cpk` (il file `data.cpk` estratto dalla tua copia Vita)
   - `Persona 4 Golden/data_it.cpk` (il file dati della versione PC Steam con lingua italiana)
   - `E:/FAGDec/app/PCSB00245/eboot.bin.elf` (l'ELF decrittato tramite FAGDec)
4. Esegui gli script di generazione:
   ```bash
   # 1. Patcha e firma l'eseguibile PS Vita
   python tools/patch_vita_eboot.py

   # 2. Genera il pacchetto dati data.cpk localizzato
   python tools/build_full_italian_cpk.py
   ```

---

## 📝 Changelog

### v1.0.0 (Release Iniziale)
- **Traduzione Testi Integrale**: Portati oltre 2.100 file di script, dialoghi, messaggi e tabelle di sistema (`cmpTable`, `fclTable`, `init_free.bin`, `date_change.bin`).
- **Sottotitoli Cutscene**: 26 filmati di intermezzo codificati a 960x544 con sottotitoli italiani sincronizzati.
- **Grafica & UI Completa**:
  - Menu di salvataggio (`mcPanel.arc`) con etichette chiare e tradotte.
  - Texture del menu TV Jacktoons / Canale 8 (`Persona Hits`, `P4 Arena`, `P4 Animation`) create e campionate con palette CLUT a 256 colori.
  - Menu di pausa e calendario con indicatore "SALTA" rifinito.
- **Patch `eboot.bin`**:
  - 108 nomi dei luoghi della mappa tradotti in italiano.
  - 34 messaggi modali di rete e PSN tradotti.
  - Prompt di conferma e inserimento nomi localizzati.
  - 38 titoli dei programmi della guida TV tradotti.

---

## ☕ Supporta il Progetto

Se apprezzi questo lavoro di traduzione e ottimizzazione per PS Vita e desideri supportare lo sviluppo di futuri progetti homebrew e traduzioni, puoi lasciare una donazione libera tramite PayPal:

[![Donate with PayPal](https://img.shields.io/badge/Donate-PayPal-00457C.svg?logo=paypal&logoColor=white&style=for-the-badge)](https://www.paypal.com/paypalme/domyno6773)

Ogni contributo è sinceramente apprezzato! ❤️

---

## ⚖️ Note Legali e Crediti

- **Persona 4 Golden** è un marchio registrato di **ATLUS Co., Ltd. / SEGA Corporation**.
- Questa patch è un progetto amatoriale senza scopo di lucro, realizzato per consentire la fruizione della localizzazione ufficiale sulla versione originale PlayStation Vita.
- Si richiede il possesso legittimo di una copia originale del gioco per PlayStation Vita e della versione PC per l'utilizzo di questa mod.
