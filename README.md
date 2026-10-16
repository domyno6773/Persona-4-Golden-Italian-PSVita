# Persona 4 Golden - Traduzione Italiana per PlayStation Vita

![Platform](https://img.shields.io/badge/Platform-PS%20Vita-blue.svg)
![Game](https://img.shields.io/badge/Game-Persona%204%20Golden-yellow.svg)
![Title ID](https://img.shields.io/badge/Title%20ID-PCSB00245%20(EU)-green.svg)
![Version](https://img.shields.io/badge/Release-v1.0.5-orange.svg)
![Language](https://img.shields.io/badge/Language-Italiano-red.svg)
[![Donate with PayPal](https://img.shields.io/badge/Donate-PayPal-00457C.svg?logo=paypal&logoColor=white)](https://www.paypal.com/paypalme/domyno6773)

Patch amatoriale di traduzione italiana per **Persona 4 Golden** su **PlayStation Vita (edizione europea PCSB00245)**.

> **v1.0.5: hotfix confermata sulla console.** La prima battaglia nella nebbia si avvia, i messaggi di sistema sono in italiano e i comandi di battaglia si visualizzano correttamente anche quando selezionati. Include tutte le correzioni di compatibilità delle versioni precedenti. Leggere le [note v1.0.5](release_notes_v1.0.5.md). La prova riguarda queste funzioni; il gioco completo non è stato verificato.

Il progetto porta su console portatile l'intera localizzazione italiana ufficiale realizzata da **Atlus / SEGA** per la versione PC (Steam), integrando correzioni ad hoc per l'hardware della PS Vita, filmati sottotitolati in italiano a risoluzione nativa e texture rielaborate a mano.

---

## 🎮 Caratteristiche della Mod

- **Testi e Dialoghi in Italiano**: Storia principale, tutti i Social Link, richieste secondarie, lezioni ed esami scolastici, descrizioni di abilità, oggetti, equipaggiamento e Personae.
- **Tutti i 26 Filmati con Sottotitoli in Italiano**: I filmati animati e le cutscene parlate sono stati estratti, sottotitolati con la traduzione ufficiale e ricodificati alla risoluzione nativa della PS Vita (**960x544**, H.264 Main Profile @ Level 4.0, AAC Stereo).
- **Interfaccia Grafica e Texture 2D Riadattate**:
  - Comandi di battaglia italiani: Attacco, Abilità, Guardia, Analisi, Tattiche, Oggetti e Fuga, comprese le varianti selezionate.
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
  - Corretta codifica a 8bpp e 4bpp CLUT con palette swizzling specifico per la GPU PowerVR di PS Vita.
  - Compatibilità totale con salvataggi preesistenti della versione europea.

---

## 📋 Requisiti

1. **PlayStation Vita** o **PlayStation TV** con modifica abilitata (**HENkaku / Enso** su firmware 3.60 o 3.65).
2. Copia originale di **Persona 4 Golden (Edizione Europea - Title ID: `PCSB00245`)**, installata in formato digitale o cartuccia fisica.
3. Plugin **`rePatch`** (consigliato `rePatch reLoaded` o `rePatch v3.0`) installato e configurato in `ur0:tai/config.txt`.
4. Plugin **`0syscall6`** (o `NoNpDrm`) per abilitare l'avvio di file e moduli decrittati.
5. Circa **2.8 GB** di spazio libero sulla scheda di memoria della PS Vita (`ux0:`).

---

## 📥 Istruzioni per l'Installazione

### Metodo Rapido (Drag & Drop via USB / FTP)

1. Scarica **entrambi i ZIP** dalla [release v1.0.5](https://github.com/domyno6773/Persona-4-Golden-Italian-PSVita/releases/tag/v1.0.5):
   - [P4G_Italian_Patch_v1.0.5.zip](https://github.com/domyno6773/Persona-4-Golden-Italian-PSVita/releases/download/v1.0.5/P4G_Italian_Patch_v1.0.5.zip): dati corretti, menu di battaglia ed eseguibile italiani.
   - [P4G_Italian_Movies_v1.0.5.zip](https://github.com/domyno6773/Persona-4-Golden-Italian-PSVita/releases/download/v1.0.5/P4G_Italian_Movies_v1.0.5.zip): tutti i 26 filmati sottotitolati a 960×544. I filmati sono gli stessi della v1.0.0; chi li ha già installati può aggiornare solo la patch.
   - `SHA256SUMS.txt` contiene i checksum dei due archivi. I due ZIP si estraggono normalmente: non sono volumi di un archivio diviso.
2. Avvia **VitaShell** sulla tua PS Vita e premi **SELECT** per collegare la console al PC tramite cavo USB (oppure connettiti via client FTP).
3. Estrai entrambi i file `.zip` sul PC nella stessa cartella:
   - Copia la cartella `rePatch` risultante nella radice della partizione **`ux0:`**, unendo le cartelle e sostituendo i file della patch precedente. Non sostituire i file originali in `app/PCSB00245`.
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

### v1.0.5
- Tradotte 31 etichette nel pannello di combattimento, comprese le varianti evidenziate dei comandi.
- Conservati dimensioni, palette, metadati e icone della texture Vita originale.
- Confermati sulla console: avvio del primo combattimento nella nebbia, messaggi di sistema italiani e comandi di battaglia, anche selezionati.

### v1.0.4
- Corretto l'allineamento a 32 byte dei membri ARC che causava il blocco o crash entrando nella prima battaglia.

### v1.0.3
- Ripristinati i contenitori e gli asset nativi Vita per modelli, effetti e audio di battaglia.
- Corrette le tabelle, i messaggi e i metadati CPK, mantenendo il bytecode Vita e adattando i soli testi.

### v1.0.1 (Hotfix)
- **Risolto il crash `C2-12828-1` nella stanza del protagonista a casa Dojima (sera dell'11 aprile e visite successive)**:
  - Il crash era dovuto a chiamate e istruzioni FlowScript PC introdotte da Atlus nell'update 2023 (Salvataggio rapido / Album) non presenti nel motore PS Vita 2012.
  - Implementato `build_vita_bf.py` che preserva al 100% il bytecode e le procedure native di PS Vita su tutti i 1.091 script di gioco (`.bf`), innestandovi dinamicamente l'intera traduzione italiana ufficiale.
  - La conferma dei blocchi segnalati richiede una prova su console; vedere le note v1.0.2.

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
2. Installa i requisiti Python (consigliato Python 3.11+):
   ```bash
   pip install pillow cricodecs
   ```
3. Posiziona nella cartella di lavoro:
   - `clean_vita_data.cpk` (il file `data.cpk` estratto dalla tua copia Vita)
   - `Persona 4 Golden/data_it.cpk` (il file dati della versione PC Steam con lingua italiana)
   - `E:/FAGDec/app/PCSB00245/eboot.bin.elf` (l'ELF decrittato tramite FAGDec)
4. Per la correzione attuale del menu servono anche la build locale v1.0.4 gia' verificata, nella relativa cartella `P4G_Italian_Patch_v1.0.4`, e il suo eseguibile italiano. Le istruzioni della build precedente sono nelle [note v1.0.4](release_notes_v1.0.4.md). Esegui:
   ```bash
   python tools/build_battle_menu_hotfix.py
   python tools/verify_stability_hotfix.py --patch P4G_Italian_Patch_v1.0.5/rePatch/PCSB00245/data/data.cpk --report P4G_Italian_Patch_v1.0.5/verification_report.json
   python tools/package_stability_hotfix.py --folder P4G_Italian_Patch_v1.0.5
   python tools/package_complete_release.py
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
