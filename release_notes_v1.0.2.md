# v1.0.2 - Correzioni di compatibilita' Vita/PSTV

Le segnalazioni di crash nella stanza di Dojima e al primo scontro nella nebbia
hanno portato a controllare anche i contenitori che la v1.0.1 non riconosceva.
Sono state corrette incompatibilita' reali nei file; manca la conferma su console
che i due punti segnalati siano entrambi superati.

## Modifiche

- **AI di battaglia:** `AICALC.TBL` contiene due BF incorporati. Il secondo nella
  patch precedente usava ancora codice PC (42.669 istruzioni contro le 42.663
  Vita). Ora entrambi mantengono tutte le sezioni native, traducendo i messaggi.
- **Dati di battaglia:** conservati `ENCOUNT.TBL`, effetti BED e dati dummy Vita.
- **Scene PM1:** tradotta solo la sezione MSG1, con ID e scelte originali. I dati
  nativi e i puntatori interni delle altre sezioni restano ai loro indirizzi.
  Quando necessario la sezione messaggi viene aggiunta in coda, allineata a 16
  byte, e viene aggiornato il suo descrittore. Questo conserva anche i puntatori
  assoluti nei blocchi di animazione e modelli senza tentare di reinterpretarli.
- **Nomi nelle tabelle:** mantenute le dimensioni Vita in `MSG.TBL` (23 byte per
  abilita', 21 per nemici) e `itemtbl.bin` (24 byte per oggetto). Il PC usa campi
  piu' ampi. Due nomi vengono abbreviati per rientrare nei limiti console.
- **BVP:** traduzione per nome del dialogo, preservando la directory Vita.
- **BMD:** sistemati layout dei messaggi vuoti, codifica delle relocation,
  indici dei parlanti, conflitti tra messaggi e scelte e conversione degli accenti
  senza toccare gli argomenti dei comandi.
- I convertitori gestiti falliscono esplicitamente in caso di errore.
- Texture, filmati e versione dell'eseguibile della v1.0.1 vengono conservati.

## Verifiche

Sette test di regressione superati. Sul CPK prodotto sono stati controllati:

- tutti i 12.334 file della directory CPK;
- 1.271 FlowScript, inclusi quelli nelle tabelle, confrontando le sezioni native;
- 1.164 scene PM1 e 100.574 dialoghi;
- relocation, ID dei dialoghi, scelte e indici dei parlanti;
- quattro BVP, tre tabelle di battaglia, dimensioni dei nomi degli oggetti e
  900 effetti/dati dummy nativi.

**Nessun test su hardware o emulatore eseguito.** Non dichiarare questa versione
confermata su PS Vita/PSTV finche' non sono state provate stanza, sonno, nebbia,
primo scontro e mattina successiva. Per i messaggi assenti o incompatibili nel PC
viene mantenuta la corrispondente voce Vita, che puo' restare in inglese.

Il formato e' stato confrontato anche con il progetto primario
[Atlus Script Tools](https://github.com/tge-was-taken/Atlus-Script-Tools).

## Generazione e controllo

Eseguire dalla cartella che contiene i dati personali estratti e gli asset della
traduzione gia' assemblata:

```powershell
python tools/build_stability_hotfix.py --vita clean_vita_data.cpk --pc "Persona 4 Golden/data_it.cpk" --base rePatch_PCSB00245/PCSB00245/data/data.cpk --eboot rePatch_PCSB00245/PCSB00245/eboot.bin
python tools/verify_stability_hotfix.py
python -m unittest discover -s tools -p test_stability_hotfix.py -v
```

L'output va in `P4G_Italian_Patch_v1.0.2/rePatch/PCSB00245/`. Il generatore rifiuta
di sovrascrivere input o un output esistente e non copia dati su console.
I report JSON e gli hash SHA-256 documentano il risultato.
