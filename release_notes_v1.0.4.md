# v1.0.4 - Padding degli archivi ARC

La v1.0.3 verificata e attiva sulla Vita ha provocato C2-12828-1 all'inizio
della prima battaglia nel sogno nella nebbia. I messaggi di sistema erano
in inglese perche' il relativo eseguibile italiano era stato disattivato.

Il confronto con l'originale ha rilevato un difetto del generatore ARC:
tutti gli 8.563 membri originali hanno dimensioni multiple di 32 byte,
ma i BF e BMD tradotti venivano scritti senza il padding. Nella v1.0.3
59 script o messaggi successivi iniziavano a indirizzi non multipli di 4,
compresi i messaggi di `battle/result/shuffle.arc`.

La v1.0.4 reinserisce il padding nei dati e nelle dimensioni della directory.
Il validatore controlla tutti i membri ARC e rifiuta la vecchia struttura.
L'utente ha poi confermato l'avvio della prima battaglia nella nebbia e i
messaggi di sistema italiani con questa versione. Il resto del gioco non e'
stato verificato integralmente.

E' incluso nuovamente l'eseguibile italiano gia' presente nel progetto:
torneranno tradotti i messaggi di sistema e i nomi dei luoghi. I filmati
non vengono modificati da questa build.

I pacchetti di battaglia restano da 1.001.920 e 997.184 byte decompressi,
con i pannelli Vita originali; non sono stati reintrodotti gli ARC PC da 13 MB.

## Verifiche

- 16 test superati, inclusi rilevamento dell'allineamento errato, aggiornamento
  binario, rifiuto di una base diversa e ripristino dopo un aggiornamento troncato.
- Confronto completo di 23.303 risorse, con 8.563 membri ARC allineati.
- 100.574 dialoghi, 1.271 FlowScript e 1.164 scene PM1 controllati.
- Metadati CPK Vita, bytecode e binari non testuali conservati.
- SHA-256 del CPK: `cfa1e6370b942511a124bbddcf81cc3328a8c63a074ca52f75f7be1e9d4d3d01`.
- **Riscontro hardware dell'utente:** prima battaglia nella nebbia avviata e messaggi di sistema italiani. Nessuna verifica integrale del gioco.

## Ricostruzione locale

```powershell
python tools/build_stability_hotfix.py --eboot patched_eboot.bin
python tools/verify_stability_hotfix.py
python -m unittest discover -s tools -p test_stability_hotfix.py
python -m unittest discover -s tools -p test_v104_delta.py
python tools/package_stability_hotfix.py
```

L'installatore `install_v104_delta.py` richiede i CPK locali completi delle
versioni 1.0.3 e 1.0.4 e il relativo rapporto di verifica. Verifica integralmente
la copia installata, conserva un journal sul PC e applica solo gli intervalli
che differiscono sotto un nome di staging. Riattiva il CPK solo quando il suo
SHA-256 completo coincide con la nuova build. Non elimina backup dalla Vita
e non modifica i salvataggi o i file originali dell'applicazione.
