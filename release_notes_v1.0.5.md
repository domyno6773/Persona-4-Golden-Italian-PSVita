# v1.0.5 - Hotfix completa e comandi di battaglia italiani

La v1.0.5 risolve il blocco/crash all'ingresso della prima battaglia nella nebbia
e traduce il menu di combattimento, comprese le voci selezionate:
**Attacco, Abilità, Guardia, Analisi, Tattiche, Persona, Oggetti e Fuga**.
Include l'eseguibile con i messaggi di sistema italiani e tutti i **26 filmati
sottotitolati**, già distribuiti nella versione 1.0.0.

## Correzioni incluse

- Ripristinati i formati e gli asset nativi Vita nei pacchetti di battaglia:
  nessuna sostituzione generica con modelli, effetti o contenitori della versione PC.
- Conservati bytecode, istruzioni e strutture Vita; adattati i testi italiani.
- Corretti l'allineamento a 32 byte dei membri ARC, le tabelle di messaggi
  e i metadati CPK nativi.
- Tradotte 31 etichette grafiche del pannello di battaglia senza cambiare
  dimensioni, palette, icone o coordinate della texture Vita.
- Inclusi `data.cpk`, `eboot.bin` italiano e i 26 filmati a 960×544.

## Verifiche

Confermati dall'utente sulla console: avvio della prima battaglia nella nebbia,
messaggi di sistema italiani e visualizzazione corretta dei comandi di battaglia,
anche quando selezionati. I filmati inclusi sono quelli già distribuiti;
non sono stati riprovati durante questa verifica. Non è una prova dell'intero gioco.

Superati 21 test automatici e la verifica di 23.303 risorse, inclusi 8.563 membri
ARC allineati e i controlli sui file nativi di battaglia. Il pacchetto completo
contiene i checksum SHA-256 dei dati, dell'eseguibile e di tutti i filmati.

## Download

Scarica **entrambi** gli archivi allegati alla release:

- `P4G_Italian_Patch_v1.0.5.zip`: `data.cpk`, eseguibile italiano e rapporti di verifica.
- `P4G_Italian_Movies_v1.0.5.zip`: tutti i 26 filmati sottotitolati.
- `SHA256SUMS.txt`: checksum SHA-256 dei due ZIP.

Sono due ZIP normali, da estrarre nella stessa cartella sul PC.
Chi ha già i filmati della v1.0.0 può conservare quelli e aggiornare soltanto la patch.
La distribuzione è separata per rispettare il limite di dimensione dei file di GitHub.

## Installazione e aggiornamento

Chiudi il gioco e conserva una copia dei salvataggi e della patch precedente.
Estrai il pacchetto sul PC, poi copia la cartella `rePatch` nella radice di `ux0:`
con VitaShell, unendo le cartelle e sostituendo i file della patch precedente.
Il percorso finale deve essere `ux0:rePatch/PCSB00245/`, con `eboot.bin`,
`data/data.cpk` e `data/movie/*.mp4`.
Non sostituire i file originali del gioco in `app/PCSB00245`.
Completa il trasferimento, espelli l'unità ed esci dalla modalità USB prima di avviare.

## Sorgenti

Gli strumenti di costruzione, verifica e aggiornamento sono nella cartella `tools`.
Per ricostruire servono i file estratti dalle proprie copie Vita e PC;
vedere il README e le note v1.0.4 per la build di base.
