# v1.0.3 - Contenitori e metadati Vita

**Prova hardware fallita: C2-12828-1 all'inizio della battaglia nella nebbia.**
Il file v1.0.3 e' stato verificato tramite SHA-256 e attivato dopo aver trovato
inizialmente attiva la vecchia patch. Il successivo riscontro dell'utente
conferma il crash. Vedere le [note v1.0.4](release_notes_v1.0.4.md) per il
difetto di padding ARC individuato in seguito.

**La v1.0.2 e' ritirata.** Il precedente validatore controllava i contenuti
riconosciuti, ma non rifiutava un diverso tipo di contenitore o una modifica a
un binario non riconosciuto. Questo ha lasciato passare file incompatibili.

## Riscontri e correzioni

- `battle_pack.bin/panel/btlpanel.bin` e la sua copia nel secondo pacchetto
  erano ARC PC da 12.651.212 byte al posto di PAC Vita da 543.744 byte.
  Ora la struttura e i pannelli sono quelli originali Vita.
- `mariko.pack`, precedentemente ridotto a 256 byte, torna al pacchetto nativo
  da 862.016 byte. Non vengono piu' copiati pacchetti PC vuoti o di altro tipo.
- Rimossa la sostituzione automatica dei file PC non riconosciuti. Modelli,
  audio, effetti, dati di campo e altri binari restano identici all'originale.
- Conservati nomi, ordine e formato delle directory di ogni ARC e PAC.
- Gli script BF vengono ricostruiti nell'ordine Vita e mantengono la relativa
  convenzione del campo FileSize, senza duplicare il blocco messaggi.
- Le tabelle dei Social Link, delle statistiche, dei libri e degli acquisti
  importano solo le stringhe, entro i campi Vita e senza cambiare i metadati.
- Il salvataggio CPK generico introduceva un'intestazione di 44 campi,
  revisione 7.14, e riduceva l'indice ETOC a una sola riga. La v1.0.3 preserva
  i 35 campi originali, revisione 7.0, i 12.335 record ETOC e gli ID e l'ordine
  originali della TOC. Vengono aggiornati solo offset e dimensioni necessari.

Le dimensioni decompresse dei pacchetti di battaglia ora sono:

| File | Vita originale | v1.0.3 |
| --- | ---: | ---: |
| battle_pack.bin | 998.592 | 1.001.920 |
| battle_pack2.bin | 995.904 | 997.184 |

La piccola crescita e' dovuta ai messaggi italiani. Nelle versioni precedenti
i due pacchetti superavano 13 MB a causa dei pannelli PC.

## Verifiche

11 test di regressione superati. Il CPK salvato supera un confronto completo
con i dati Vita: 23.303 risorse, 1.271 FlowScript, 1.164 scene PM1 e 100.574
dialoghi. Verificati anche 15.061 binari non adattati, directory dei contenitori,
metadati CPK, campi numerici e limiti delle tabelle di testo.

**La precedente prova di avvio era condizionata dal gioco corrotto.**
La reinstallazione ha risolto C2-10362-2 secondo il riscontro dell'utente.
Dopo la verifica e l'attivazione del CPK 1.0.3, la console ha invece mostrato
C2-12828-1 all'inizio del primo combattimento nel sogno nella nebbia.

Il pacchetto contiene solo `data.cpk` e usa l'eseguibile originale del gioco.
L'eboot personalizzato va lasciato con nome `.off`: alcuni nomi di luoghi e
messaggi di sistema restano quindi in inglese durante questa verifica.

## Comandi

Dalla cartella dei dati personali estratti e della precedente build:

```powershell
python tools/build_stability_hotfix.py
python tools/verify_stability_hotfix.py
python -m unittest discover -s tools -p test_stability_hotfix.py -v
python tools/package_stability_hotfix.py
```

Non viene modificata alcuna release precedente. L'installazione esplicita su E:
usa `install_v103_vita.py`, controlla il checksum letto dalla console prima di
attivare il file e conserva quello precedente come `data.cpk.pre_v1.0.3.bak`.
