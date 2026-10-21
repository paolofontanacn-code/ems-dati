# EMS Cismondi - simulazione su GitHub

**SOLO SIMULAZIONE**: nessun comando viene inviato all'inverter Huawei.

**Pagina con i grafici**: https://paolofontanacn-code.github.io/ems-dati/ (giorno per giorno: reale, senza batteria, automatico, F0, F0R;
si aggiorna a ogni giro). I file che legge sono nella cartella `pannello/`, preparati da `ml/pannello.py`.

Ogni 30 minuti (programmati; GitHub ne ritarda o salta alcuni) GitHub esegue **lo stesso programma che girerà sul Mango** (cartella `mango/`, in Lua) e misura il
carico di lavoro che il Mango avrebbe. I dati dell'impianto arrivano dallo **storico Huawei a 5 minuti**: le letture
vengono "rigiocate" una per una, come se il Mango le leggesse in tempo reale ogni 5 minuti. Il machine learning
gira in Python (cartella `ml/`).

## Scenari simulati (dal 21/10/2026)

| Scenario | Descrizione |
|---|---|
| Senza batteria | solo autoconsumo istantaneo del FV: il resto si compra, l'eccedenza si cede |
| Automatico | batteria in massimo autoconsumo, senza ottimizzatore (come funziona oggi) |
| **F0** - senza carica da rete | batteria gestita dall'ottimizzatore, carica solo da FV |
| **F0R** - con carica da rete | come F0, piu' carica dalla rete fino a 1 kW di giorno |

Acquisto: prezzo fisso monorario F0 0,12 EUR/kWh + perdite 10 %, dispacciamento (non ancora noto, per ora 0),
trasporto 0,014730, oneri di sistema 0,033153, accise 0,0227 EUR/kWh, IVA 10 % = 0,2228 EUR/kWh.
Cessioni (RID): prezzo zonale NORD del quarto d'ora, senza imposte. Usura batteria: 0,02 EUR per kWh scaricato.
Ogni scenario ha la sua batteria simulata (SOC proprio). Ogni 15 minuti l'ottimizzatore sceglie tra autoconsumo,
carica ritardata, carica forzata e scarica forzata (1, 2, 3 o 5 kW), con al massimo 14 periodi forzati e 1 ciclo
(15 kWh) di scarica forzata al giorno; ogni ora sopra il 90 % di SOC ha un piccolo costo (0,01 EUR). Ogni cambiamento
di funzionamento ha un costo attribuito di 0,10 EUR. I giorni fino al 21/10/2026 hanno i vecchi scenari A, B, C.
Ogni giorno GitHub manda il resoconto via email (Gmail) ai destinatari di `impostazioni/email_destinatari.txt`.

Tutti i valori sono in `mango/config.lua`.

## Dove guardare

| File / cartella | Contenuto |
|---|---|
| `ULTIMO_REPORT.md` | report dell'ultimo giorno chiuso |
| `riepilogo.csv` | una riga per giorno: costi, ricavi, benefici per scenario, errori di previsione, carico del Mango |
| `dati/AAAA-MM-GG/` | dataset per l'IA (`dataset.csv.gz`, una riga ogni 5 minuti, circa 180 colonne), periodi di carica/scarica, piano della sera, meteo previsto, prezzi, carico di lavoro del Mango, report |
| `modelli/ULTIMO_ADDESTRAMENTO.md` | esito dell'ultimo addestramento e confronto con le previsioni del Mango |
| `modelli/coefficienti_mango.json` | coefficienti nel formato del Mango (usati solo se migliori) |
| `previsioni/` | previsioni di consumi e FV per il giorno dopo calcolate qui |
| `storico/` | storico FusionSolar importato il giorno 0 e meteo storico |
| `misure/` | benchmark per convertire i tempi di GitHub in tempi del Mango |
| `segreti/` | token Huawei **cifrato** (la chiave è un segreto del repository) |
| `backup/` | copia giornaliera della memoria del programma (ultimi 7 giorni) |

## Carico di lavoro del Mango

Ogni report riporta: tempo di CPU per ciclo e per il calcolo del piano, memoria, byte scritti al giorno nella memoria
interna e chiamate che il Mango farebbe a Huawei, GME, Open-Meteo e GitHub. I tempi sono misurati qui: per avere
quelli del Mango serve il fattore di velocità. Si ottiene **una volta sola**: lanciare `benchmark_su_mango.bat`
dal PC (esegue `mango/benchmark_mango.lua` sul Mango via SSH), poi caricare il file prodotto
`misure/benchmark_mango.txt` nel repository. Da quel momento i report mostrano anche i tempi stimati sul Mango.

## Funzionamento

1. **Giorno 0**: il programma importa lo storico FusionSolar a 5 minuti (fino a 450 giorni, 2 chiamate per giorno),
   il meteo storico, e addestra i modelli. Poi parte la simulazione.
2. **Ogni 30 minuti** (`.github/workflows/ems.yml`): scarica lo storico Huawei delle ultime ore (3 chiamate per giorno
   coinvolto), rigioca le letture ogni 5 minuti con il programma del Mango, scarica prezzi GME (dalle 13:30) e meteo,
   ottimizza, registra, chiude i giorni finiti; poi il machine learning riaddestra i modelli e prepara le previsioni.
3. Le chiamate reali a Huawei sono circa 70-110 al giorno (il Mango ne farebbe circa 870 con le letture ogni 5 minuti).
4. Ogni giro dura indicativamente 2-4 minuti. Il repository e' pubblico (serve alla pagina con i grafici): i minuti
   di GitHub Actions sui runner standard dei repository pubblici non hanno il limite di 2.000 al mese.

Avvio manuale: tab **Actions** > **EMS simulazione** > **Run workflow**.

## Installazione

Si fa dal PC con `INSTALLA_EMS.bat` (pacchetto Installa_EMS): crea o prepara questo repository, carica i file,
imposta segreti e permessi, avvia il primo giro e ne controlla l'esito. Se si rilancia, riparte da zero
con una nuova autorizzazione Huawei.

## Prossimi aggiornamenti (annotati)

Fatti nella fase 1 (GitHub): profilo F0 con e senza carica da rete, cessione al quarto d'ora senza imposte,
usura 0,02 EUR/kWh, scenario senza batteria, curve nascoste che restano, limite di 1 ciclo forzato al giorno e costo
per SOC alto, meteo con secondo tentativo, email giornaliera. Restano per la fase 2: il Mango, i pulsanti e i comandi.


- **Scenario 0 - senza batteria**: FV senza accumulo, autoconsumo solo istantaneo, il resto acquistato dalla rete
  al prezzo fisso F0 (vedi sotto) e l'eccedenza ceduta al prezzo NORD orario pieno. Da calcolare nel programma
  del Mango come gli altri scenari e da mostrare nella pagina accanto a reale, automatico e scenario ottimizzato.
- **Pagina - curve nascoste**: quando si cambia giorno le curve nascoste dalla legenda devono restare nascoste
  (oggi tornano tutte visibili perche' i grafici vengono ridisegnati). La scelta dei pannelli invece resta gia'.
- **Un solo profilo di acquisto (decisione del 21/10/2026)**: si simula solo il prezzo fisso monorario F0 a 0,12 EUR/kWh
  (contratto di 20 anni: nessun effetto sui calcoli), con le stesse componenti dell'attuale profilo A: [0,12 x 1,10 perdite + dispacciamento + trasporto
  + oneri di sistema + accise] x 1,10 IVA. I profili B (PUN mensile per fascia) e C (PUN orario) vanno tolti dalla
  simulazione, dai resoconti e dalla pagina.
- **Cessione senza imposte (decisione del 21/10/2026)**: l'energia ceduta vale il prezzo zonale NORD orario pieno,
  senza togliere il 40 % di imposte (IMPOSTA_CESSIONI da 0,40 a 0, in simulazione, resoconti e pagina).
- **Costo di carica/usura batteria (decisione del 21/10/2026)**: 0,02 EUR/kWh al posto dell'attuale
  6000 EUR / (6000 cicli x 15 kWh) = 0,0667 EUR/kWh.
- **Token GitHub**: non scade (scelta dell'utente); quello salvato sul PC in %USERPROFILE%\.ems_cismondi\github_token.txt
  va considerato sempre valido e riusato da tutte le procedure.
- **Da verificare**: giorni 18/10 e 19/10 chiusi con beneficio negativo per B e C (-2,12 e -4,00 EUR il 18/10):
  uno scenario ottimizzato non dovrebbe fare peggio dell'automatico; da analizzare sui dati del giorno.
- **Mango (progetto del 21/10/2026)**: Mango 192.168.1.1 raggiunto in VPN; legge Huawei ogni 5 minuti, rinnova il token,
  invia i dati a GitHub e avvia il giro; GitHub analizza, pubblica e prepara il piano comandi; il Mango invia i comandi
  a Huawei AL MASSIMO OGNI 2 ORE, solo se attivati da un pulsante protetto (soluzione da scegliere). Token Huawei solo sul Mango.
- **Pulsante comandi (scelta del 21/10/2026: soluzione a)**: sulla pagina GitHub; la pagina scrive la richiesta
  "attiva/disattiva" con il token GitHub salvato solo nel browser dell'utente; la richiesta e' firmata con la password
  del pulsante; il Mango verifica la firma prima di obbedire. Comandi spenti all'inizio; senza piano recente il Mango
  rimette l'inverter in automatico.
- **Due profili sempre calcolati (21/10/2026)**: prezzo fisso F0, (1) SENZA carica da rete e (2) CON carica da rete
  (max 1 kW, di giorno). La pagina li mostra entrambi; un secondo pulsante "abilita carica da rete" sceglie quale
  piano il Mango invia a Huawei (pulsante comandi spento = nessun invio).
- **Invio comandi (21/10/2026)**: il Mango invia a Huawei un programma (TOU, max 14 finestre) al massimo ogni 2 ore;
  dentro il programma le finestre usano la durata minima della simulazione (15 minuti).
- **Ciclo ogni 2 ore (21/10/2026)**: il Mango invia i dati e avvia il giro su GitHub, lascia a GitHub il tempo per meteo,
  dati e ottimizzazione, poi scarica il piano e invia il programma a Huawei. Orizzonte del piano sempre fino all'ultimo
  prezzo GME noto (prezzi conservati solo su GitHub). Se il piano nuovo non arriva in tempo: resta valido quello
  precedente finche' copre l'ora attuale, altrimenti automatico.
- **Pulsante "Abilita carica da rete"**: protetto come quello dei comandi (token GitHub nel browser + firma con password
  verificata dal Mango).
- **Eccezioni approvate (21/10/2026)**: scelta manuale nell'app FusionSolar = PRIORITA' (il Mango sospende i comandi
  finche' l'utente non li riattiva dalla pagina); comandi con scadenza automatica se Huawei li prevede (da verificare),
  altrimenti solo finestre delle prossime ore e controllo al ritorno della linea; letture in buffer a scorrimento e
  recupero dallo storico; tentativi limitati e chiamate di comando di riserva per tornare in automatico; avviso nella
  pagina se il token Huawei viene rifiutato; avviso se GitHub tace da oltre 4 ore; controlli di sicurezza sul piano e
  piano firmato da GitHub (chiave segreta GitHub+Mango); richieste dei pulsanti con scadenza 10 minuti e stato
  "richiesto/confermato dal Mango"; stato e piano in memoria permanente, nessun comando prima di avere l'ora corretta;
  rilettura da Huawei dopo ogni invio; ultimo contatto del Mango nella pagina e segnalazione se tace da oltre 30 minuti.
- **Ottimizzazioni approvate (21/10/2026)**: prezzi GME al quarto d'ora per le decisioni (cessione); nuovo programma
  solo se cambia piu' di 0,10 EUR; prova a secco prima dei comandi reali, poi primo giorno con una sola finestra;
  misura dell'effetto reale dei comandi (ritardo, potenze) per il machine learning; limite di un ciclo equivalente
  al giorno per i comandi forzati e niente soste lunghe sopra il 90 %; meteo con attese brevi, secondo tentativo e
  ultima previsione valida; pagina con il risparmio reale dei comandi; controlli interni sul Mango (errori ripetuti,
  dati compressi, versione del formato del piano). NIENTE riserva di backup (impianto senza backup).
- **Email giornaliera**: GitHub invia ogni giorno il resoconto a un indirizzo impostabile (file nel repository), tramite
  Gmail (smtp.gmail.com, password per le app nei segreti di GitHub; mittente e destinatario: paolo.fontana.cn@gmail.com).
