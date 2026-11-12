# EMS Cismondi - simulazione su GitHub

Revisione R04 - 24/10/2026 (elenco delle revisioni: REVISIONI.txt)

**SOLO SIMULAZIONE**: nessun comando viene inviato all'inverter Huawei.

**Pagina con i grafici**: https://paolofontanacn-code.github.io/ems-dati/ (giorno per giorno: condizioni 0, 1 reale, 2, 2a-2e e controllo automatico simulato; pulsante Aiuto con le descrizioni;
si aggiorna a ogni giro). I file che legge sono nella cartella `pannello/`, preparati da `ml/pannello.py`.

Ogni 30 minuti (programmati; GitHub ne ritarda o salta alcuni) GitHub esegue **lo stesso programma che girerà sul Mango** (cartella `mango/`, in Lua) e misura il
carico di lavoro che il Mango avrebbe. I dati dell'impianto arrivano dallo **storico Huawei a 5 minuti**: le letture
vengono "rigiocate" una per una, come se il Mango le leggesse in tempo reale ogni 5 minuti. Il machine learning
gira in Python (cartella `ml/`).

## Condizioni simulate (dal 22/10/2026)

| Condizione | Descrizione |
|---|---|
| **0** - senza batteria | solo autoconsumo istantaneo del FV: il resto si compra, l'eccedenza si cede |
| **1** - batteria senza ottimizzazione (oggi) | DATI REALI misurati da Huawei finche' l'inverter e' in automatico, piu' l'usura sui kWh scaricati; con i comandi attivi (fase 2) torna simulata |
| **2** - ottimizzazione, senza carica AC | batteria gestita dall'ottimizzatore, carica solo da FV |
| **2a / 2b / 2c / 2d / 2e** | come 2, piu' carica AC dalla rete fino a 1 / 2 / 3 / 4 / 5 kW (livelli graduati), a qualsiasi ora |
| controllo: automatico simulato | l'automatico rifatto dal simulatore, per verificare che il simulatore stia vicino alla condizione 1 |

Nei file le condizioni 2...2e si chiamano C2, C2a, C2b, C2c, C2d, C2e. Se una condizione con piu' potenza AC
trova un piano peggiore di una con meno potenza, adotta quel piano (puo' sempre usare meno potenza).
Prelievo massimo 7 kW: se si supera, si riduce prima la carica AC.

Acquisto: prezzo fisso monorario F0 0,12 EUR/kWh + perdite 10 %, dispacciamento (non ancora noto, per ora 0),
trasporto 0,014730, oneri di sistema 0,033153, accise 0,0227 EUR/kWh, IVA 10 % = 0,2228 EUR/kWh.
Cessioni (RID): prezzo zonale NORD del quarto d'ora, senza imposte. Usura batteria: 0,02 EUR per kWh scaricato.
Ogni condizione 2...2e ha la sua batteria simulata (SOC proprio). Ogni 15 minuti l'ottimizzatore sceglie tra autoconsumo,
carica ritardata, carica forzata e scarica forzata (1, 2, 3 o 5 kW), con al massimo 14 periodi forzati e 1 ciclo
(15 kWh) di scarica forzata al giorno; ogni ora sopra il 90 % di SOC ha un piccolo costo (0,01 EUR). Ogni cambiamento
di funzionamento ha un costo attribuito di 0,10 EUR. I giorni precedenti hanno i vecchi scenari (A, B, C fino al
21/10/2026, poi F0 e F0R): nella pagina compaiono come "Vecchia".
Ogni giorno GitHub manda il resoconto via email (Gmail) ai destinatari di `impostazioni/email_destinatari.txt`.

Tutti i valori sono in `mango/config.lua`.

## Cessione totale 20 kW (dal 23/10/2026, pagina `cessione.html`) - revisione R04

Simulazione a parte, solo calcolo: impianto ipotetico da 20 kW in cessione totale (prodotto = ceduto), venduto in RID
al prezzo orario zonale NORD (PO NORD).
- **Impianto**: 20 kW a Ovest, inclinazione 2 gradi; 2 x SUN2000-10KTL-M1 e 2 batterie da 15 kWh calcolati come un
  inverter da 20 kW con batteria da 30 kWh (carica e scarica max 10 kW, perdita 5 %); rete max 17 kW; nessun prelievo,
  nessuna carica da AC. Modello fisico non lineare (R04): perdita in piu' a bassa potenza di scarica, potenza ridotta
  vicino a batteria piena o vuota.
- **Produzione**: Cismondi (11 kW, Sud, 2 gradi) x 20 / 11 x rapporto irraggiamento Ovest / Sud.
- **Decisione ogni 2 ore** (`ml/cessione_live.py` + `ml/cessione_ottimizza.py`, nel giro dei 30 minuti, fino a 90 s):
  previsione di produzione (piu' modelli meteo, il migliore per orizzonte, correzioni imparate) con 3 scenari; prezzi
  noti + previsti dallo storico fino a fine domani; piano con una modalita' Huawei per fascia di 2 ore (anche diverse
  nello stesso giorno) e fasce TOU / comandi per ora, cercato con algoritmo evolutivo partendo da programmazione
  lineare, logica fuzzy, modalita' pure e piano precedente. Il contesto di ogni decisione e' salvato in
  `cessione/live/contesti/`.
- **Autoapprendimento** (`ml/cessione_apprendimento.py`, workflow separato `cessione_apprendimento.yml` ogni 2 ore,
  fino a 45 minuti): rigioca le decisioni delle ultime 2 settimane con altri parametri (algoritmo evolutivo sui
  parametri) e li adotta solo se avrebbero reso di piu' (`cessione/live/apprendimento.json`).
- **Ottimo teorico dei giorni passati** (`ml/cessione_totale.py`): produzione e prezzi noti in anticipo (limite massimo).
- Ancora da chiarire: limite ai cambi di modalita' al giorno (per ora nessun limite; parametro "costo_cambio").
Da fare: costo dell'impianto e payback.

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

- **Revisioni (23/10/2026)**: da ora ogni consegna ha un numero di revisione, scritto in ogni file modificato
  (intestazione), in un elenco delle revisioni con le modifiche (REVISIONI.txt nello zip), in alto nella pagina e
  nel nome del file zip consegnato (es. Installa_EMS_R01.zip). Le consegne precedenti NON si ricostruiscono: si parte
  da R01 con la prossima consegna.

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
- **Pagina - colori accessibili (21/10/2026)**: niente colori simili tra le curve; tavolozza adatta a daltonici
  (es. Okabe-Ito) e a ipovedenti: oltre al colore, curve distinte anche per tratteggio/spessore e marcatori,
  contrasto alto su sfondo chiaro e scuro.
- **Pagina - testi piu' grandi** per gli ipovedenti (numeri, etichette degli assi e legende).
- **Pagina - produzione attesa (21/10/2026)**: curva della produzione FV prevista con il meteo atteso, dall'ora
  attuale fino alla fine dell'orizzonte del piano (oggi e domani), a quarti d'ora, insieme a consumo previsto e
  radiazione prevista; il giorno dopo la curva prevista resta confrontata con la produzione reale.
- **Fascia di incertezza** sulla produzione attesa: confermata (21/10/2026).
- **Tavolozza proposta (Okabe-Ito)**: scenari - reale nero (chiaro nel tema scuro) pieno spesso; senza batteria
  azzurro #56B4E9 a puntini; automatico porpora #CC79A7 a trattini; F0 blu #0072B2 pieno; F0R vermiglio #D55E00
  pieno con triangoli. Flussi - FV arancio #E69F00; consumo verde-blu #009E73; rete azzurro #56B4E9; batteria porpora
  #CC79A7; previsto = stesso colore a trattini, sera prima a puntini. Prezzi - acquisto blu; NORD nero (orario a
  puntini, quarto d'ora pieno); cessione verde-blu spesso. Meteo - temperatura vermiglio, radiazione arancio.
  Azioni - carica FV verde-blu a righe, carica rete arancio a quadretti, scarica vermiglio pieno, ritardata azzurro
  a puntini. Giallo non usato per le linee (poco contrasto).
- **Pagina - solo F0 e F0R (21/10/2026)**: togliere dalla pagina anche i vecchi profili A, B, C dei giorni passati.
- **Nomi delle simulazioni (22/10/2026)**: condizione 0 = impianto senza batteria; condizione 1 = batteria senza
  ottimizzazione (come oggi, "automatico"); condizione 2 = batteria con ottimizzazione di carica/scarica, acquisto a
  prezzo fisso F0. Usare questi nomi in pagina, resoconti ed email.
- **Condizioni 2, 2a-2e (22/10/2026)**: 2 = ottimizzazione senza carica AC; 2a/2b/2c/2d/2e = carica AC dalla rete
  fino a 1/2/3/4/5 kW (livelli graduati fino al massimo), a QUALSIASI ORA (tolto il vincolo "solo di giorno": l'energia
  costa uguale giorno e notte). Limiti: batteria 5 kW, prelievo 7 kW (si riduce prima la carica AC). Il pulsante
  "abilita carica da rete" diventa la scelta della potenza massima di carica AC (0-5 kW) = condizione inviata.
- **Condizione 1 = reale misurato (22/10/2026)**: finche' l'inverter e' in automatico la condizione 1 si calcola con i
  dati Huawei misurati del giorno; con i comandi attivi torna simulata. Descrizioni delle condizioni nell'aiuto della pagina.
- **Scelta automatica della condizione da inviare (22/10/2026)**: l'automatismo valuta le condizioni 0, 1, 2, 2a-2e e
  invia all'inverter la piu' conveniente tra quelle eseguibili (1 = automatico, 2-2e = programma con carica AC fino a
  0-5 kW); la 0 e' solo riferimento (la batteria non si puo' togliere). Il pulsante protetto resta solo per
  attivare/disattivare i comandi (da confermare: niente scelta manuale della potenza AC).
- **Scala dei tempi sempre di 24 ore (23/10/2026)**: nei grafici del giorno l'asse dei tempi deve restare fisso da 00:00
  a 24:00 anche quando i dati coprono solo una parte del giorno (giorno in corso, giorno dell'aggiornamento, letture
  mancanti); oggi la scala si adatta ai soli dati presenti (con una sola lettura il grafico resta vuoto).
- **Grafico unico con piu' grandezze (23/10/2026)**: potenze, SOC, meteo e prezzi devono poter essere attivati
  insieme sullo stesso grafico (scelta di quali curve mostrare), ognuno con la sua scala sull'asse y (W, %, gradi /
  W/m2, EUR/kWh). Colori adatti a ipovedenti e daltonici (tavolozza Okabe-Ito, gia' annotata) piu' tratteggi diversi,
  cosi' le curve si distinguono anche senza colore. Asse dei tempi sempre 00:00-24:00 (vedi sopra).
- **Energie come grafico a barre (23/10/2026)**: le energie (kWh: FV, consumo, prelievo, immissione, carica/scarica
  batteria, per condizione) vanno disegnate a barre, non a linee; le potenze (W), il SOC e i prezzi restano a linee.
  Intervallo delle barre e quali energie: da definire.
- **Cessione totale - scarica batteria (23/10/2026, dopo R02, da chiarire prima del codice)**: scarica della batteria
  al massimo 5 kW; uscita dell'inverter A al massimo 10 kW. Chiarito: i pannelli di A hanno la precedenza e possono
  dare fino a 10 kW; la batteria scarica solo nello spazio che resta (scarica <= min(5 kW, 10 kW - potenza dei
  pannelli di A in uscita)); non si taglia mai produzione dei pannelli per scaricare la batteria. Nell'inverter reale
  questo controllo forse lo fa l'inverter stesso (da verificare sui dati del costruttore).
- **Cessione totale - inverter (23/10/2026)**: 2 x Huawei SUN2000-10KTL-M1 (scheda Huawei: uscita 10.000 W, 11.000 VA
  massimi; FV consigliato max 15.000 Wp; batteria max 10.000 W in carica e in scarica lato inverter; batterie
  compatibili LUNA2000-5/10/15-S0 e 7/14/21-S1). La LUNA2000-15-S0 da scheda: 15 kWh utili, uscita max 5 kW
  (picco 7 kW per 10 s). La precedenza dei pannelli sulla scarica non e' indicata nelle schede: da verificare.
  Manuale d'uso SUN2000-(3KTL-10KTL)-M1, Issue 28 del 30/03/2026: 10KTL-M1 potenza nominale 10.000 W, potenza
  attiva massima 11.000 W (cos phi = 1), 11.000 VA; 2 MPPT, max 8,8 kW per MPPT (oltre, l'inverter limita la potenza
  dei pannelli); batteria 600-1100 Vdc, max 16,7 A; con batteria al massimo 3 inverter in cascata, la batteria sta
  sull'inverter collegato allo Smart Dongle. Il manuale NON descrive le modalita' della batteria ne' la precedenza
  pannelli/scarica: rimanda ai manuali di messa in servizio (Smart Dongle Networking and Inverter Direct
  Connection Commissioning Manual / SmartAssistant / Smart Guard).
  Manuale "Residential Smart PV Solution (Smart Dongle Networking & Inverter Direct Connection)" V05 25/07/2025,
  par. 6.2: modalita' Maximum self-consumption, TOU, Fully fed to grid, Third-party dispatch; potenza massima di
  carica e di scarica impostabili; "Charge from AC" disattivata di serie; in Fully fed to grid il FV va prima in rete
  e "When the maximum output power of the inverter is reached, the surplus energy is used to charge the batteries".
  Nessuna frase sulla riduzione della scarica quando i pannelli producono molto: ancora da verificare.
  "FusionSolar App and SUN2000 App Device Commissioning Guide" Issue 09 del 22/10/2026, tab. 4-20 Battery control:
  - Fully fed to grid: massimizza l'immissione; il FV oltre la capacita' di uscita dell'inverter carica la batteria;
    quando il FV e' sotto la capacita' di uscita, la batteria scarica per portare l'uscita al massimo. La rete non
    puo' caricare la batteria. (Non segue i prezzi.)
  - TOU: fino a 14 fasce orarie di carica/scarica impostate a mano, ciclo settimanale; fuori dalle fasce la batteria
    non carica e non scarica dalla rete; "Priority of excess PV energy" = Fed to grid (FV prima in rete, eccedenza
    oltre l'uscita massima in batteria) oppure Charge.
  - Third-party dispatch: carica/scarica comandate da piattaforma esterna; in carica il FV va prima in batteria;
    "During discharging, batteries are preferentially discharged, and surplus PV energy is discarded" (in scarica la
    batteria ha la precedenza e il FV in eccesso si PERDE: il contrario della regola annotata sopra).
  - Charge from AC: disattivata di serie; con Fully fed to grid e Maximum self-consumption "The grid cannot charge
    the ESS".
- **Cessione totale - versione finale (23/10/2026, da valutare, NIENTE CODICE)**: impianto 20 kW, 2 inverter identici
  SUN2000-10KTL-M1, 2 batterie da 15 kWh (una per inverter), nessuna carica da AC. Scenari: senza batteria (produzione
  di Cismondi in proporzione) e con batteria (2 x 15 kWh). Il sistema sceglie la modalita' migliore tra quelle
  Huawei (Fully fed to grid, TOU, Third-party dispatch), la rivaluta ogni 2 ore con i nuovi dati dell'inverter,
  prevede meteo e produzione, aggiorna i prezzi di vendita; la giornata e' una serie di simulazioni ogni 2 ore che
  correggono il piano precedente; autoapprendimento dalle scelte precedenti; obiettivo: massimo ricavo di vendita;
  rispetto dei limiti di carica/scarica delle batterie.
  Decisioni (23/10/2026): limite verso la rete 17 kW; ogni batteria carica e scarica al massimo 5 kW; uscita di ogni
  inverter 10 kW (nominale); simulazione ogni 2 ore solo da oggi in avanti (si salvano le previsioni da ora; per i
  giorni passati resta il calcolo attuale, ottimo teorico). Valutazione: Maximum self-consumption esclusa (nessun
  carico); Fully fed to grid quasi uguale a senza batteria (picco Cismondi 7.173 W -> circa 6,2 kW per inverter, sotto
  i 10 kW: la batteria non si caricherebbe); da confrontare TOU (priorita' "Charge", max 14 fasce) e Third-party
  dispatch (in scarica il FV in eccesso si perde). Da verificare: in TOU la scarica va anche in rete o solo ai carichi?
  Autoapprendimento (23/10/2026): il sistema deve imparare dalle scelte precedenti e migliorarsi. Proposta (da
  confermare): (1) previsione di produzione corretta con l'errore misurato (per ora del giorno e tipo di cielo);
  (2) ogni piano a 2 ore salvato e confrontato a fine giornata con il risultato reale e con l'ottimo a posteriori
  (rimpianto in EUR); (3) per ogni modalita' si registra quando avrebbe vinto (stagione, nuvolosita', differenza tra
  prezzo massimo e minimo) e la scelta successiva ne tiene conto; (4) margini di prudenza (energia tenuta in batteria,
  anticipo/ritardo della scarica) regolati in base agli errori passati; (5) in pagina l'andamento del rimpianto e della
  quota dell'ottimo raggiunta, per vedere se migliora davvero.
  Precisazione (23/10/2026): NON si vuole una misura del miglioramento. Ogni 2 ore la simulazione rivaluta tutto e
  decide cosa fare; obiettivo unico: massimo ricavo, vendendo nelle ore a prezzo piu' alto. Previsione della
  produzione col metodo piu' preciso. Proposta: irraggiamento sul piano dei pannelli (GTI, con inclinazione e
  orientamento) da piu' modelli meteo Open-Meteo (ItaliaMeteo ARPAE ICON-2I 2 km fino a 3 giorni; MeteoFrance AROME
  a 15 minuti; un modello globale per l'orizzonte lungo) + modello imparato sui dati reali di Cismondi (produzione
  vera contro previsioni salvate) + correzione in giornata a ogni giro con la produzione misurata dall'inverter e la
  radiazione da satellite (Open-Meteo Satellite Radiation API, DWD MTG, ritardo circa 20 minuti). Si tiene, per ogni
  orizzonte di previsione, la combinazione con l'errore misurato piu' basso.
  Orientamento (23/10/2026): Cismondi 11 kW, Sud, inclinazione 2 gradi. Impianto simulato: vedi CORREZIONE sotto
  (tutto a Ovest 2 gradi). Si lavora sui dati di Cismondi (i piu' freschi disponibili): la produzione E e O si ricava da quella
  misurata a Sud con il rapporto tra l'irraggiamento sul piano E (o O) e quello sul piano S, quarto d'ora per quarto
  d'ora (con 2 gradi di inclinazione la differenza e' piccola: da quantificare).
  Decisioni (23/10/2026): proporzione con Cismondi = 11 kW (fattore 20 / 11 = 1,818; prima 11,48).
  CORREZIONE (23/10/2026): tutto l'impianto da 20 kW e' a OVEST, inclinazione 2 gradi (non meta' Est e meta' Ovest):
  2 inverter da 10 kW, ognuno con 10 kW di pannelli a Ovest e la sua batteria da 15 kWh. La produzione si ricava da
  quella misurata a Sud a Cismondi con il rapporto tra irraggiamento sul piano Ovest 2 gradi e sul piano Sud 2 gradi.
  Semplificazione approvata (23/10/2026): i due inverter sono identici e con lo stesso orientamento, quindi la
  simulazione li tratta come un solo inverter da 20 kW con una batteria da 30 kWh (carica max 10 kW, scarica max
  10 kW), limite verso la rete 17 kW, nessuna carica da AC.
  TOU (23/10/2026, indicazione dell'utente): nelle fasce di scarica la batteria cede in rete, massimizzando la vendita
  (impianto in cessione totale, senza carichi). Punto chiuso per la simulazione.
- **Cessione totale - apprendimento dagli errori di gestione della batteria (23/10/2026, dopo R03, NIENTE CODICE
  finche' non richiesto)**: a fine giornata confrontare la simulazione ogni 2 ore con l'ottimo a posteriori (stessa
  produzione e stessi prezzi, stessa energia in batteria a inizio giorno) e misurare il "rimpianto" in EUR e le sue
  cause (scarica troppo presto o troppo tardi, energia tenuta a mezzanotte, carica mancata); usare questi errori per
  correggere le decisioni successive: valore dell'energia lasciata in batteria a fine orizzonte (oggi fisso = prezzo
  medio), margine di prudenza sulla previsione, scelta e forma delle fasce TOU.
- **Cessione totale - prezzi e prova prima di cambiare (23/10/2026, dopo R03, NIENTE CODICE finche' non richiesto)**:
  (6) usare SEMPRE tutti i prezzi gia' noti (oggi; domani appena pubblicati dal GME, verso le 13) e, oltre l'ultimo
  prezzo noto, una PREVISIONE dei prezzi imparata dallo storico (giorno della settimana, stagione, ultimi giorni), cosi'
  l'orizzonte delle decisioni arriva sempre almeno a fine domani; la previsione viene sostituita dai prezzi veri appena
  arrivano. Nota: oggi i prezzi di domani li scarica la simulazione principale dalle 13:30 (ORA_PREZZI, poi ogni 30
  minuti) e la simulazione ogni 2 ore li legge da li': valutare un tentativo dalle 13:00.
  (9) prima di adottare una modifica delle regole, rigiocare i giorni gia' vissuti con le previsioni salvate, con la
  regola vecchia e con la nuova; adottare la nuova solo se rende di piu' (controllo interno, non un rapporto).
- **Cessione totale - molte simulazioni e autoapprendimento evolutivo (23/10/2026, dopo R03, NIENTE CODICE finche'
  non richiesto)**: fino a 1 ora di calcolo su GitHub. Le tre modalita' possono alternarsi nello stesso giorno (fasce di
  2 ore): valutare le combinazioni (3^12 = 531.441 sequenze in 24 ore, troppe da provare una per una) con
  programmazione dinamica sulle fasce di 2 ore + algoritmo evolutivo (sequenze di modalita', fasce TOU, potenze,
  parametri) + logica fuzzy come regola in gara; modello fisico non lineare (rendimento variabile, riduzione di potenza
  vicino a pieno/vuoto, FV perso in scarica); piu' scenari di produzione; prezzi mancanti stimati dallo storico.
  Proposta di organizzazione: workflow separato ogni 2 ore (timeout 60 minuti, gruppo di concorrenza proprio) per
  l'apprendimento lungo (rigioco dei giorni vissuti e taratura evolutiva), cosi' non blocca il giro di 30 minuti;
  la decisione ogni 2 ore resta veloce e usa i parametri gia' tarati. Da chiarire: limite ai cambi di modalita' al giorno.
- **Avvio dei giri dal Mango (24/10/2026, fase 2, NIENTE CODICE finche' non richiesto)**: GitHub avvia i giri programmati
  in modo irregolare (notte 23-24/10: solo 3 giri su 16 previsti, tutti riusciti; gli altri mai avviati). Scelta
  dell'utente: sara' il Mango ad avviare i giri ogni 30 minuti (chiamata "workflow_dispatch" a GitHub, dopo la lettura
  Huawei), gia' previsto nella fase 2. Fino ad allora i giri restano quelli di GitHub (irregolari) piu' quelli a mano.
- **Stabilita' della programmazione (24/10/2026, NIENTE CODICE finche' non richiesto)**: nella scelta della simulazione
  migliore NON si cambia la programmazione gia' spedita all'inverter se il nuovo piano, nelle 4 ore successive, non
  rende almeno il 10 % in piu' delle stesse 4 ore del piano in vigore (entrambi valutati con i dati nuovi: previsione,
  prezzi, energia in batteria). Scopo: evitare cambi troppo frequenti. Vale per la cessione totale (simulazione ogni
  2 ore) e, in fase 2, per i comandi veri dal Mango. Soglia minima (24/10/2026): 0,10 EUR = costo attribuito a un cambio
  di programmazione delle 2 ore seguenti. Si cambia solo se il nuovo piano, nelle 4 ore successive, rende almeno il 10 %
  in piu' E il guadagno supera 0,10 EUR (il costo del cambio, come la penalita' di 0,10 EUR per cambiamento gia' usata
  nella simulazione di Cismondi).
  Costo dei cambi di modalita' DENTRO il piano (tra fasce di 2 ore): resta un parametro tarato dall'apprendimento
  (parte da 0 EUR, limiti 0-0,50 EUR), su indicazione dell'utente (24/10/2026).
  Da inserire nella prossima revisione (R05), quando richiesto: la R04 consegnata NON contiene ancora la regola
  4 ore / 10 % / 0,10 EUR.
  Decisione dell'utente (24/10/2026): la R04 NON viene installata; si aspetta la R05 (contenuto R04 + questa regola).
- **R05 - meteo nel grafico delle potenze (24/10/2026, NIENTE CODICE finche' non richiesto)**: le curve del meteo
  (irraggiamento, nuvolosita', temperatura) si possono mostrare nello stesso grafico delle potenze, selezionabili dalla
  legenda, con il proprio asse y (vedi anche "Grafico unico con piu' grandezze", colori per ipovedenti, asse 24 ore).
  Deciso (24/10/2026): in ENTRAMBE le pagine (Cismondi e cessione), con visualizzazioni simili tra le due pagine
  (stessi tipi di grafico, stessi colori e tratteggi, stessa legenda selezionabile, stesso asse 24 ore).
  Le due pagine useranno lo STESSO metodo di disegno dei grafici (oggi: Cismondi con uPlot, cessione con disegno
  proprio). Deciso (24/10/2026): uPlot per entrambe (zoom, valori al passaggio del mouse); anche i grafici a barre
  della cessione passano a uPlot.
- **R05 - revisione mostrata nelle pagine (24/10/2026, NIENTE CODICE finche' non richiesto)**: la pagina di Cismondi
  mostra "Revisione R01" anche con la R03 installata, perche' il numero scritto in pagina e' quello dell'ultima modifica
  di index.html (R01; R02 e R03 non l'hanno toccato). Proposta: in alto in ogni pagina la revisione INSTALLATA (letta
  da un file unico aggiornato a ogni consegna) e, accanto, quella della pagina. CONFERMATO dall'utente (24/10/2026).
- **Third-party dispatch: come ottenerlo sull'inverter (24/10/2026, DA VERIFICARE prima di usarlo per decidere)**: la
  guida "FusionSolar App and SUN2000 App Device Commissioning Guide" Issue 09 (par. 4.4.5) descrive la modalita'
  Third-party dispatch per lo SmartAssistant: un EMS esterno collegato (oggetti previsti, es. GridX) manda istruzioni,
  la batteria passa in Third-party dispatch e al termine torna alla modalita' di prima; scegliendo GridX si abilitano
  HTTP e Modbus TCP ("may have network security risks"). Non e' documentato come farlo con il solo Smart Dongle, ne'
  con l'API FusionSolar. Strade da verificare: Modbus TCP in rete locale (Mango sulla stessa rete; MAI porta 502 esposta
  su Internet), API FusionSolar, dispositivo SmartAssistant/EMMA. Finche' non e' verificato, la simulazione lo usa come
  ipotesi.
  Verifica API (24/10/2026): nel "SmartPVMS 25.1.0 Northbound API Reference" di Huawei esiste la pagina "API for
  Delivering Battery Charge and Discharge Tasks" (e nella 25.4.0 "API for Delivering an Inverter Active Power Setting
  Task"), ma il contenuto non e' leggibile da qui (sito Huawei bloccato agli strumenti automatici): parametri, limiti e
  permessi da leggere. Da progetti pubblici: la carica/scarica forzata (Stop/Charge/Discharge, durata o energia,
  potenza) e' comandabile via Modbus (Smart Dongle in rete locale) o con richieste del portale web FusionSolar (non API
  ufficiale); un progetto dichiara che nell'OpenAPI la batteria ha solo valori in lettura (forse versione precedente).
  Indice del "SmartPVMS 26.2.0 NBI Reference" Issue 03 (23/10/2026), mandato dall'utente: API di comando 5.2.1 compiti
  di carica e scarica della batteria (pag. 244), 5.2.3 impostazione della modalita' della batteria (253), 5.2.5 parametri
  della batteria (268), 5.2.7 potenza attiva dell'inverter (276), 5.2.9 compiti di carica/scarica "dispatch-based" (286);
  4 limiti alle chiamate (65-77); 7.5 esempi di programmazione della batteria (314); FAQ 8.16 "The device does not
  support this setting" (338) e 8.20 taglio del FV e limite di corrente in carica/scarica forzata (340). Da leggere il
  contenuto di queste pagine.
  LETTO (24/10/2026) dal "SmartPVMS 26.2.0 北向接口参考" (versione cinese, documento 01 del 30/06/2026, gia' allegato):
  - 5.2.3 modalita' della batteria via API: SOLO "maximumSelfConsumption", "TOU", "thirdPartyDispatch" (Fully fed to grid
    NON impostabile via API). TOU: max 14 finestre HH:MM non sovrapposte, giorni di ripetizione, redundantPVEnergyPriority
    = fedToGridPreference / chargePreference, allowedAcChargePower (Dongle 0-50 kW). Per "thirdPartyDispatch" la batteria
    va in attesa dei comandi; supportato con Dongle, SmartAssistant, inverter diretto (non con datalogger).
  - 5.2.9 comando in thirdPartyDispatch: solo potenza in W (>0 carica, <0 scarica, 0 fermo), resta valido finche' non
    cambia; niente durata ne' SOC. Prima va impostata la modalita' con 5.2.3.
  - 5.2.1 carica/scarica forzata: potenza, durata (0-1440 min) o SOC obiettivo; non cambia la modalita'; Huawei lo indica
    come funzione di prova, sconsigliata nell'uso normale (per fasce fisse: TOU).
  - Limiti (4.2): ogni API di comando e di verifica 1 chiamata al minuto per account; non ripetere per lo stesso impianto
    finche' il compito non e' finito.
  - Vincoli thirdPartyDispatch (7.5): M1 SINGOLO + LUNA2000 S0/S1 + Dongle (= Cismondi, SUN2000-10KTL-M1 compreso nella
    lista); M1 IN PARALLELO + LUNA + SmartAssistant (= impianto da 20 kW con 2 inverter: serve SmartAssistant). Possibili
    limitazioni: controllo della potenza al punto di connessione, autodiagnosi, calibrazione SOH annuale, protezioni della
    batteria; Huawei consiglia di abilitare l'acquisto dalla rete in thirdPartyDispatch, altrimenti le potenze possono
    differire dal comando (contrasta con "nessun prelievo" della cessione totale: da verificare).
  - Nota: la versione inglese dell'utente e' l'Issue 03 del 23/10/2026: possibili differenze.
- **Mango aggiuntivo (24/10/2026, decisione dell'utente, NIENTE CODICE)**: sara' programmato un Mango aggiuntivo, collegato
  al router, che conterra' anche il programma gia' discusso (fase 2); sul Mango sara' installata la VPN per l'accesso
  dall'esterno; dettagli da definire. Nota: secondo il documento Huawei (7.5) il comando Third-party dispatch via API con
  2 inverter in parallelo richiede uno SmartAssistant, a prescindere da chi manda i comandi; il Mango non lo sostituisce
  via API (via Modbus in rete locale: non documentato qui, da verificare).
- **Obiettivo finale (24/10/2026, PUNTO FERMATO)**: comandare l'impianto di Cismondi (1 inverter, 1 batteria) via API.
  Secondo il documento Huawei e' una configurazione supportata (M1 singolo + LUNA2000 S0/S1 + Dongle), a condizione di:
  modello esatto e firmware compatibili, permessi di comando dell'account API, pagina di configurazione del portale che
  permetta di impostare la modalita' della batteria (FAQ 8.16). Verifica senza comandi possibile: API di lettura della
  modalita' della batteria (5.1.5.1). Simulazione da 20 kW: resta simulazione (SmartAssistant necessario per 2 inverter).
- **R05 - niente accensioni/spegnimenti dentro la stessa ora (26/10/2026, NIENTE CODICE finche' non richiesto)**: il 24/10
  la R03 ha scaricato 18:00-20:00 a 10 kW, si e' fermata 20:00-20:30 e ha ripreso 20:30-21:00 (4,9 e 10 kW); anche alle
  11:45 la carica e' scesa a 0,65 kW per un solo quarto d'ora. COMPORTAMENTO DA EVITARE (indicazione dell'utente).
  Causa (verificata sui dati pubblicati): il prezzo RID e' orario, quindi i 4 quarti d'ora di un'ora valgono uguale e la
  programmazione lineare sceglie a caso dove mettere la scarica dentro l'ora (piani 16:29 e 19:35: "scarica 18:00-20:15;
  20:45-21:00" e "19:15-20:00; 20:30-21:00"). Rimedi per la R05: comando costante per ogni ora (gia' cosi' nella R04 per
  Third-party dispatch), a parita' di ricavo preferire il piano con meno cambi e scarica/carica continue, regola
  4 ore / 10 % / 0,10 EUR per non cambiare il piano spedito.
  Correzione dell'utente (26/10/2026): non e' mai stato detto di scaricare a piena potenza. Variabile della simulazione
  per ridurre i cambi: potenza ceduta dalla batteria MODULABILE tra 2 e 5 kW (scelta dal programma, costante a tratti).
  Verifica sul documento Huawei (SmartPVMS 26.2.0, versione cinese 01 del 30/06/2026): possibile.
  - Third-party dispatch (5.2.9): "dispatchPower" in W, qualsiasi valore entro i limiti (es. -2000 ... -5000 W).
  - Carica/scarica forzata (5.2.1): "powerDispatch" in W.
  - TOU (5.2.3): le finestre non hanno una potenza propria; la potenza massima di scarica (e di carica) della batteria si
    imposta a parte con 5.2.5 "maximumDischargePower" / "maximumChargePower" (W, da 200 W al massimo del dispositivo)
    e vale per tutte le finestre finche' non la si cambia.
  - Ogni API di comando: 1 chiamata al minuto per account.
  Deciso (26/10/2026): CARICA modulabile da 0 a 5 kW (anche sotto i 2 kW, con la produzione disponibile); SCARICA
  modulabile tra 2 e 5 kW, oppure ferma.
  Ambito (26/10/2026, corretto): i limiti valgono PER OGNI BATTERIA dell'impianto da 20 kW (2 batterie da 15 kWh, una per
  inverter): ognuna carica 0-5 kW e scarica 2-5 kW o ferma. Impianto intero: carica 0-10 kW; scarica 2-10 kW (una sola
  batteria 2-5 kW, entrambe 4-10 kW). Massimi totali invariati (10 kW).
  Cismondi (26/10/2026): stessi limiti anche nella simulazione di Cismondi: carica 0-5 kW, scarica 2-5 kW o ferma (al
  posto dei livelli di scarica forzata 1, 2, 3, 5 kW e della carica a 5 kW).
- **Regola di lavoro (23/10/2026)**: il codice si scrive solo su richiesta esplicita; le indicazioni si annotano e si
  chiariscono prima con domande.
- **Simulazione su richiesta (22/10/2026)**: dalla pagina si impostano i parametri di una simulazione e la si avvia
  subito (avvio di un giro dedicato su GitHub con il token salvato nel browser); risultati mostrati nella pagina a
  parte, senza toccare le simulazioni normali ne' i comandi all'inverter. Parametri e periodo: da definire.

## Revisione R05 (26/10/2026) - realizzata su richiesta ("crea codice")
- Regola di stabilita' 4 ore / +10 % / 0,10 EUR: ml/cessione_ottimizza.py `stabilita()`. Confronto con i dati nuovi su tutto
  l'orizzonte (fino a fine domani) tra piano nuovo e "piano spedito per 4 ore, poi piano nuovo"; soglia = max(0,10 EUR;
  10 % del ricavo delle 4 ore del piano spedito). Esito registrato in ogni decisione (campo "stabilita").
  Prova simulata 21-22/10 (dati di prova): dopo la prima decisione il piano spedito e' sempre stato mantenuto (guadagni
  sotto la soglia). Risultato 22/10: beneficio +2,25 EUR; la R04 senza regola aveva reso di piu' nella stessa prova
  (2,61 EUR in due giorni) perche' il 21/10 aveva messo da parte energia per la mattina del 22/10. DA VALUTARE con i dati
  veri: la regola e' dell'utente; il comportamento conservativo e' atteso con guadagni piccoli.
- Potenze modulabili: carica 0-10 kW, scarica 2-10 kW o ferma (zona morta sotto 2 kW nel modello); gene "potenza TOU"
  2-10 kW; costo 0,002 EUR per cambio di comando tra ore. Cismondi: LIVELLI_SCARICA_W = 2, 3, 4, 5 kW; P_MIN_SCARICA_W 2 kW.
- Pagine: uPlot anche per cessione.html (barre disegnate in proprio dentro uPlot, motivi a righe/quadri/punti);
  meteo nei grafici delle potenze di entrambe le pagine (radiazione blu/verde tratteggio, temperatura rosa puntini,
  nuvolosita' grigio tratto-punto, scale proprie a destra; sul telefono le scale del meteo sono nascoste, i valori
  restano nella legenda); revisione installata da versione.json.
- Non ancora fatto (note congelate): grafico unico di Cismondi con tutte le grandezze, energie a barre in index.html,
  asse 24 ore in index.html, apprendimento dagli errori di gestione della batteria (rimpianto), avvio dei giri dal Mango.

## Richieste per la pagina della cessione (26/10/2026, NIENTE CODICE finche' non richiesto)
- Prezzi: nel grafico del giorno della simulazione ogni 2 ore la curva del prezzo arriva oggi solo fino all'ultimo quarto
  d'ora simulato. Va riportata fino all'ultimo prezzo noto (i prezzi NORD del giorno dopo arrivano verso le 13); una volta
  letti non cambiano.
- Batteria: oltre ai kWh, riportare la carica della batteria in % (capacita' 30 kWh).
- Pulsanti "giorno precedente" e "giorno successivo"; cambiando giorno le curve scelte restano (oggi la scelta e' gia'
  ricordata per grafico: da verificare anche tra un mese e l'altro).
- Scale "confuse" (segnalazione dell'utente con un'immagine non arrivata): da chiarire quale grafico e cosa confonde
  (oggi: sinistra kW/kWh; destra €/kWh, W/m², °C, % nuvolosita').
  Risposte dell'utente (26/10/2026): batteria in % INSIEME ai kWh (curva in piu', selezionabile); domani selezionabile
  come giorno quando i prezzi ci sono (prezzi e piano previsto); scale: l'utente rimanda l'immagine.
  Immagine dell'utente (26/10/2026, pagina installata R03, grafico del giorno con produzione vera e prezzo accesi):
  1) scala sinistra con valori ripetuti "0, 1, 1, 2" (tacche ogni 0,5 scritte senza decimali);
  2) la curva del prezzo (€/kWh) e' disegnata sulla scala destra, che nell'immagine non si vede: sembra letta sulla
     scala dei kW. Nella R05 (uPlot): decimali secondo il passo delle tacche e scala destra colorata come la sua curva;
     da verificare sulla pagina vera dopo l'installazione.

## R06 - evoluzione dei piani (26/10/2026, proposta dell'utente, NIENTE CODICE finche' non richiesto)
- Vedere come cambia il piano migliore per i giorni futuri: per la decisione dell'ora x poter scegliere anche i piani
  calcolati alle ore x-2, x-4, x-6 (al massimo 3 periodi indietro) e confrontarli.
- Stato attuale (R05, verificato nel codice): per ogni decisione si salvano il contesto (previsione di produzione,
  incertezza, prezzi noti e previsti: cessione/live/contesti/<t>.json) e, nel registro delle decisioni, solo il
  riassunto a testo del piano. Il piano completo quarto per quarto e' salvato solo per l'ultima decisione (stato.json,
  sovrascritto) e le curve attese (energia in batteria, potenza in rete) non sono salvate. Quindi per la R06 serve
  salvare a ogni decisione il piano completo e le curve attese; i piani calcolati prima dell'installazione della R06
  non si possono rivedere.
- Con la regola delle 4 ore ci sono due piani per decisione: quello calcolato (migliore) e quello spedito (le 4 ore del
  piano precedente se il guadagno e' sotto soglia).
- Gia' in lista per la R06: pulsanti giorno precedente/successivo con le curve scelte che restano; prezzi fino
  all'ultimo noto; batteria anche in %; domani selezionabile quando i prezzi ci sono; scale (immagine dell'utente).
- Risposte dell'utente (26/10/2026): curve per ogni decisione = energia in batteria, potenza in rete, carica/scarica,
  produzione prevista (tutte); vista UNA DECISIONE ALLA VOLTA (scelta da menu: x, x-2, x-4, x-6); per ogni decisione si
  salvano e si mostrano ENTRAMBI i piani, calcolato e spedito.
- Precisazione dell'utente (26/10/2026): per ogni decisione si registra e si mostra il piano migliore delle 10 ORE
  SUCCESSIVE all'ora della decisione (es. decisione delle 14: dalle 14 alle 24). CONFERMATO (26/10/2026): il calcolo resta fino a
  fine domani; solo questo grafico (evoluzione dei piani) ha l'asse dei tempi di 10 ore dall'ora della decisione, anche
  oltre la mezzanotte (decisione delle 22:00: dalle 22:00 alle 08:00 del giorno dopo). Gli altri grafici restano a 24 ore.
- Proposta dell'utente (26/10/2026, NIENTE CODICE): sull'asse dei tempi del grafico un pallino per ogni decisione,
  all'ora in cui la simulazione e' finita. Passando il mouse su un pallino si accendono le curve del piano migliore
  calcolato in quel momento, di quello precedente e di quello successivo. Esempio dell'utente: il pallino delle 14:00
  accenderebbe solo il piano della simulazione precedente inviata (da chiarire).
  Fattibilita' (uPlot): pallini disegnati con un "draw hook" sotto l'asse x; passaggio del mouse letto con gli eventi
  del grafico; curve dei piani aggiunte come serie temporanee. Sul telefono il mouse non c'e': servirebbe il tocco.
  Richiede i piani completi salvati a ogni decisione (R06).
  Chiarito (26/10/2026): il pallino va all'ora in cui la simulazione e' FINITA davvero (es. decisione della fascia delle
  14 finita alle 14:30 -> pallino alle 14:30). Prima di quell'ora vale il piano della simulazione precedente.
  Stato R05 (verificato nel codice): nel registro delle decisioni ci sono "ora" (ora del giro in cui si decide) e
  "secondi" (durata della ricerca del piano); l'ora di fine non e' registrata: nella R06 va salvata.
  CONFERMATO (26/10/2026): in simulazione l'ora di fine della simulazione e' l'ora in cui il piano e' "inviato".
  Mouse sul pallino (26/10/2026, utente): dall'ora di fine dei calcoli si vedono il piano appena calcolato e il piano
  migliore della simulazione precedente (2 piani).
  Risposta dell'utente (26/10/2026): sul telefono i pallini NON ci sono (solo PC con mouse).
  Risposta dell'utente (26/10/2026): pallini in TUTTI E DUE i grafici (giorno della simulazione ogni 2 ore, asse 24 ore;
  evoluzione dei piani, asse 10 ore).
  Risposta dell'utente (26/10/2026): i piani x-2, x-4, x-6 si mostrano sulla STESSA finestra della decisione x (es. x =
  14:00: tutti dalle 14:00 alle 24:00). Conseguenza: per coprire x+10 ore il piano di x-6 deve essere registrato per
  16 ore dalla sua decisione (non 10): da decidere quante ore registrare.

### R06 - riepilogo concordato con l'utente (26/10/2026) - sostituisce le note R06 sopra dove diverse
1. Prezzi: curva del prezzo fino all'ultimo prezzo noto (non solo fino all'ultima simulazione).
2. Batteria: anche in % oltre ai kWh.
3. Pulsanti giorno precedente/successivo; le curve scelte restano; domani selezionabile quando ci sono i prezzi.
4. A ogni simulazione si registrano il piano migliore calcolato e quello spedito, con l'ora di fine dei calcoli.
5. Pallino (solo PC, mouse) per ogni simulazione all'ora di fine dei calcoli: passandoci sopra si vedono il piano
   appena calcolato e il migliore della simulazione precedente.
ANNULLATO dall'utente (26/10/2026): grafico di 10 ore e scelta dei piani x-2, x-4, x-6 (e quindi la domanda su quante
ore registrare per x-6 e su quale finestra mostrare).
- Utente (26/10/2026): il riassunto a testo del piano non serve (oggi e' nel registro delle decisioni e nella colonna
  "Piano" della tabella delle decisioni). Da chiarire se togliere anche la colonna dalla pagina.
- Utente (26/10/2026): a ogni simulazione si salvano ENTRAMBI i piani completi (calcolato e spedito). Mouse sul
  pallino: piano appena calcolato + piano SPEDITO del pallino precedente.
  Confermato (26/10/2026): mouse sul pallino -> 3 piani: calcolato del pallino, spedito del pallino, spedito del
  pallino precedente.

## Revisione R06 (26/10/2026) - realizzata su richiesta ("crea revisione dei files e codice")
Contenuto: punti 1-5 del riepilogo R06 sopra, piu' le risposte dell'utente (entrambi i piani salvati; sul pallino 3 piani:
calcolato e spedito della simulazione, spedito della precedente; solo potenza in rete; niente pallini sul telefono;
tolto il riassunto a testo e la colonna "Piano").
- I piani sono salvati per tutto l'orizzonte del calcolo (fino a fine domani), con la produzione prevista dello scenario
  probabile: circa 80 kB al giorno nel repository (prova simulata).
- Il pallino e' all'ora di fine dei calcoli: ora del giro + durata del calcolo. Il pallino della prima simulazione
  dopo l'installazione non ha il piano precedente (i piani prima della R06 non sono salvati).
- Pallini solo nel grafico della simulazione ogni 2 ore (il grafico di 10 ore e' stato annullato).
- Prova simulata 21-22/10 (dati di prova): beneficio -3,58 EUR il 21/10 e +5,93 EUR il 22/10 (2,36 EUR in due giorni);
  con la R05 nella prova precedente -0,12 e +2,25 EUR. La R06 non cambia il codice della decisione. La ricerca evolutiva e'
  a tempo (6 s nella prova): sullo stesso contesto ha fatto 275, 254 e 233 generazioni in tre prove, quindi i piani
  possono cambiare da una prova all'altra. Non verificato che sia l'unica causa della differenza.

## Prossima revisione (R07) - Cismondi (27/10/2026, richieste dell'utente, NIENTE CODICE finche' non richiesto)
- Prezzi di acquisto: non servono simulazioni con prezzi di acquisto diversi dal prezzo fisso (F0).
  Stato attuale (verificato nel codice): le condizioni simulate C2...C2e usano gia' tutte il prezzo fisso F0
  (config.lua). Restano: le medie mensili del PUN per fascia calcolate "solo come informazione" (prezzi_acquisto.lua)
  e, nella pagina, le simulazioni delle versioni precedenti dei giorni vecchi (F0/F0R, A, B, C "Vecchia ...").
  Da decidere cosa togliere.
- Stima dei consumi nel grafico delle potenze (index.html): curva dei consumi stimati, calcolata con LOGICA FUZZY
  autoapprendente e automigliorante, che puo' partire subito dai dati pregressi di consumo reale (storico).
  Nella logica fuzzy:
  - variabilita' dovuta alla pompa di calore, ripetuta per il RISCALDAMENTO e per l'ACQUA CALDA SANITARIA (ACS);
  - incidenza sul consumo stimato di: consumi pregressi, temperatura esterna, inerzia termica di tutta la casa.
  Stato attuale (verificato nel codice): previsione dei consumi del Mango (modelli.lua: profilo per quarto d'ora e tipo
  di giorno + pompa di calore con regressione giornaliera su gradi sotto 18 C con media delle ultime 3 ore, vento,
  sole) e modello di GitHub (ml/addestra.py: gradient boosting, accettato solo se sbaglia meno sugli ultimi 7 giorni).
  Nessuna logica fuzzy per i consumi. I consumi previsti oggi si vedono nel pannello "Previsto e reale", non in
  "Potenze".
  Risposte dell'utente (27/10/2026): la stima fuzzy si AFFIANCA alle attuali: si confrontano e per le decisioni si usa
  quella che sbaglia meno. Dati della pompa di calore: c'e' solo il consumo TOTALE della casa (riscaldamento e ACS non
  sono misurati a parte: la logica fuzzy li deve riconoscere dall'andamento del consumo totale).
  ACS (27/10/2026, utente): orari di produzione non noti, ma l'andamento e' in parte ripetitivo: la logica fuzzy deve
  imparare dai dati gli orari e l'ampiezza tipici dei cicli ACS.
- Prezzi di acquisto (27/10/2026, utente): TOGLIERE tutte le simulazioni e tutto quanto, nelle simulazioni, si riferisce
  a prezzi di acquisto diversi dal prezzo fisso F0. Trovato nel codice (27/10/2026):
  - mango/prezzi_acquisto.lua: medie mensili del PUN per fascia (aggiungi_giorno, PUN medio della fascia) e il PUN
    passato a PA.costi; chiamate in mango/ems_sim.lua (righe ~101, 210, 312, 614-615);
  - mango/gme.lua: lettura del PUN orario oltre al NORD (il NORD resta: e' il prezzo di vendita);
  - index.html: nomi, colori e grafici delle simulazioni vecchie (F0/F0R, A, B, C "Vecchia ...", costo_A/B/C nel
    pannello prezzi);
  - ml/email_report.py: nomi delle simulazioni vecchie (F0, F0R).
  Il prezzo NORD di vendita (cessione) resta.
  Confermato (28/10/2026): nei giorni vecchi della pagina di Cismondi restano visibili solo i dati reali.
- Costo di acquisto (28/10/2026, utente): DISPACCIAMENTO = 0,017 EUR/kWh (oggi 0, "non noto" in mango/config.lua).
  Nuovo costo del kWh prelevato = [0,12 x 1,10 + 0,017 + 0,014730 + 0,033153 + 0,0227] x 1,10 = circa 0,2415 EUR/kWh
  (oggi circa 0,2228). Le altre voci restano.
  Confermato (28/10/2026): 0,017 EUR/kWh e' senza IVA e senza perdite (si somma e poi si applica l'IVA del 10 %).

## Revisione R07 (31/10/2026) - realizzata su richiesta ("crea codice e file di installazione per simulazione")
- Prezzi: tolto tutto quello che si riferiva a prezzi di acquisto diversi dal fisso F0 (PUN per fascia, PUN dal GME,
  colonne pun, simulazioni vecchie in pagina ed email). Dispacciamento 0,017 EUR/kWh.
- Consumi con logica fuzzy (ml/consumi_fuzzy.py, chiamato da ml/addestra.py). Prova sui dati veri del repository
  (copia del 31/10/2026, ultimi 7 giorni, errore medio dei consumi): fuzzy 532 W, modello completo 575 W, previsioni
  del Mango 616 W -> nella prova la fuzzy e' stata scelta per le decisioni. Attenzione: fuzzy e modello completo sono
  verificati con il meteo MISURATO dei giorni di prova, le previsioni del Mango erano fatte con il meteo PREVISTO
  (stesso metodo di verifica gia' usato per il modello completo); il confronto e' quindi favorevole ai primi due.
  Inerzia della casa scelta nella prova: 12 ore (provate 3, 6, 12, 24, 48). La stima e' liscia: non riproduce i picchi
  brevi (cicli della pompa di calore di 2-3 kW).
- Stime fuzzy per la pagina: previsioni/fuzzy/AAAA-MM-GG.json (giorno prima: si aggiorna fino all'inizio del giorno;
  giorni passati: rigiocati fuori campione col meteo misurato, al massimo 7 per giro, ultimi 21 giorni).

## Prossima revisione (R08) - annotazioni (NIENTE CODICE finche' non richiesto)
- Verifica della logica fuzzy con il meteo PREVISTO (31/10/2026, utente: si), per confrontarla con le previsioni del
  Mango a parita' di condizioni. Dato disponibile: richieste/richiesta_AAAAMMGG.json con il meteo previsto la sera prima.
  Confermato (31/10/2026): anche il modello completo di GitHub si verifica con il meteo previsto (tre modelli
  confrontati allo stesso modo).
- Cismondi (07/11/2026, utente): ELIMINARE dalla simulazione la carica da rete, cioe' le condizioni 2a, 2b, 2c, 2d, 2e
  (carica AC dalla rete fino a 1-5 kW). Resta la condizione 2 (senza carica AC). Da applicare in config.lua (PROFILI,
  PROFILI_CARICA_RETE_W), pagina index.html, email.
- Tesi "Analisi dei metodi di ricostruzione delle curve di carico" (Dabbicco, PoliTo 2022), allegata dall'utente il
  07/11/2026 con la richiesta "studia e applichiamo i concetti". Concetti della tesi:
  1. oltre agli ingressi "temporali" servono le potenze medie dell'ora (e del minuto) di giorni precedenti;
  2. ripetitivita' settimanale piu' forte di quella giornaliera: meglio lo stesso giorno della settimana prima (o di due
     settimane prima) che il giorno prima;
  3. media di piu' modelli: nessun vantaggio nella tesi;
  4. carichi ripetitivi (impulsi notturni, gradini serali...): si ricostruisce un andamento tipo (NON la media dei giorni:
     se un carico c'e' 2 giorni su 4 la media ne dimezza l'ampiezza) e lo si inserisce nella previsione solo quando e'
     quasi certo (tesi: carico presente 25 giorni su 30 si', 16 su 30 no);
  5. un carico inserito all'ora sbagliata raddoppia l'errore; le oscillazioni incerte della previsione vanno livellate;
  6. su intervalli brevi, con i dati prima e dopo noti, la ricostruzione con l'andamento tipo funziona bene (simile alla
     correzione in giornata).
  Verifica sui dati veri di Cismondi (repository al 07/11/2026, 51 giorni dal 15/09 al 06/11, medie orarie dei consumi):
  - profilo orario del giorno prima: errore medio 449 W, correlazione 0,15; stesso giorno della settimana prima: 415 W,
    0,23; due settimane prima: 431 W, 0,23 -> come nella tesi la settimana prima va un po' meglio, ma la ripetitivita'
    dei consumi di Cismondi e' bassa;
  - quarti d'ora sopra 2 kW (cicli della pompa di calore?): al massimo nel 43 % dei giorni (ore 7 e 20), 41 % alle 19,
    sotto il 15 % di notte -> nessun carico ripetitivo "quasi certo" secondo il criterio della tesi.
  Applicazioni da decidere con l'utente.
- Simulazione delle condizioni esistenti sui dati pregressi del 2026 (07/11/2026, domanda dell'utente). Verificato:
  lo storico Huawei importato va dal 12/09/2026 (memoria del Mango: importazione finita il 08/09 dopo 3 giorni vuoti di
  fila = Huawei non restituisce dati prima, con l'account API). Dal 17/10 la simulazione gira davvero; dal 12/09 al 16/10
  ci sono solo i dati reali (fv, carico, contatore a 5 minuti; senza SOC). Prima del 12/09/2026: nessun dato nel
  repository. Da decidere con l'utente.
- Verifica dell'apprendimento della logica fuzzy (07/11/2026, domanda dell'utente "come quantifichiamo il
  miglioramento?"). La R07 non e' ancora installata (sul repository c'e' la R06): sul sistema vero la fuzzy non ha
  ancora girato. Prova fatta qui, "giorno per giorno" sui dati veri (copia del repository al 07/11): per ogni giorno
  dal 27/09 al 06/11 addestramento SOLO sui giorni prima (con la scelta automatica di inerzia e oblio sui 7 giorni
  prima) e stima del giorno. Risultati (errore medio sui consumi a quarti d'ora):
  - 19 giorni con le previsioni registrate del Mango (19/10-06/11): fuzzy 558 W, Mango 624 W; fuzzy migliore in 16
    giorni su 19;
  - con il meteo previsto la sera prima (richieste) o con il meteo del dataset i risultati sono quasi uguali (il meteo
    del dataset e' quello usato dal Mango in quel momento, da previsioni Open-Meteo);
  - l'errore in W CRESCE nel tempo (27/09-16/10: 362 W; 17/10-06/11: 560 W) pur con piu' giorni di addestramento,
    perche' i consumi crescono con il riscaldamento: l'errore in W da solo non misura l'apprendimento.
  Proposta per misurare il miglioramento: indice di bravura giornaliero = 1 - errore del modello / errore di
  riferimento (riferimento: previsioni del Mango e "stesso giorno della settimana prima"), seguito nel tempo
  (media mobile su 7 giorni): se l'indice sale, il sistema impara. Da decidere con l'utente.
- Dati prima del 12/09/2026 (07/11/2026, utente: impianto e batteria c'erano gia', recupero da esportazione FusionSolar).
  Da verificare con l'utente: se il portale FusionSolar mostra ancora la curva del giorno (es. un giorno di agosto) e
  con quale passo (5 minuti, ora, giorno) esporta. Dati che servono per giorno: ora, potenza FV, consumo della casa,
  contatore (prelievo/immissione); utili batteria e SOC. Poi (su richiesta) importazione nello storico e rigioco.
  Risposta dell'utente (07/11/2026): prima del 12/09/2026 l'impianto NON era sul monitoraggio: nessun dato. La
  simulazione dei dati pregressi e' possibile solo dal 12/09/2026.
  Risposta dell'utente (07/11/2026): rigioco dal 12/09 al 16/10 con la condizione 2 usando le previsioni che il sistema
  avrebbe avuto (meteo previsto, come nella realta').

## Revisione R08 (07/11/2026) - realizzata su richiesta ("crea documentazione completa e gli ultimi files")
Scelte dell'utente: 11a (rigioco col meteo previsto), 14b (R08 completa con le opzioni consigliate per i punti aperti:
consumi delle ore dei giorni prima nella fuzzy, carichi ripetitivi non inseriti, indice di bravura con grafico),
15a (manuale PDF nello zip).
Prove fatte qui (copia del repository al 07/11/2026):
- addestramento con verifica col meteo previsto (7 giorni, 672 quarti d'ora tutti con meteo previsto): Mango 740 W,
  modello completo 765 W (non accettato), coefficienti 724 W, fuzzy 641 W (accettata: usata per le decisioni).
  L'automiglioramento NON ha scelto i consumi delle ore dei giorni prima (non fanno sbagliare meno).
- carichi ripetitivi (ultimi 30 giorni, quarti sopra 2 kW): ora piu' frequente le 19 nel 53 % dei giorni; nessuno
  quasi certo.
- rigioco 18/09-16/10 (27 giorni; 18 e 19/09 saltati per pochi dati prima): qui l'archivio delle previsioni Open-Meteo
  non era raggiungibile, quindi la prova e' stata fatta col meteo misurato; su GitHub va verificato al primo giro.
  Somme dei 27 giorni (netto = acquisti - cessioni + usura + cambi; piu' basso e' meglio): senza batteria 5,46 EUR,
  automatico simulato 0,53 EUR, condizione 2 -0,75 EUR (condizione 2 meglio dell'automatico in 11 giorni su 27),
  reale senza usura -2,93 EUR (non confrontabile: senza usura della batteria).
- Ambiente di prova dell'installazione completa ricreato (07/11/2026, richiesta dell'utente): mock_servizi.py,
  mock_github.py, prova_unico.sh (zip Ambiente_prova_EMS_R08.zip). Prova della R08: installazione da zero riuscita
  (storico finto di 20 giorni importato, "INSTALLAZIONE RIUSCITA"), aggiornamento riuscito, tutti i 18 passi di
  ems.yml con esito 0 in entrambi i giri, rigioco della condizione 2 fatto con l'archivio delle previsioni (finto) in
  104 s per 15 giorni, versione.json R08 nel repository.

## Revisione R10 (annotata come R09 fino al 09/11/2026) - annotazioni; APPLICATA il 12/11/2026 (vedi in fondo)
- Peso della potenza di scarica (07/11/2026, proposta dell'utente, immagine della cessione: scarica 17:00-17:30 a
  piena potenza). Si accettano anche scariche a potenza non piena, con preferenza per la scarica piu' lenta:
  potenza di scarica dal 20 all'80 % della massima peso 1; dall'80 al 90 % peso 0,98; dal 90 al 100 % peso 0,97.
  Stato attuale (verificato nel codice R05-R08, cessione): la potenza e' gia' modulabile (Third-party: valore per ora;
  TOU: potenza massima scelta 2-10 kW; sotto 2 kW = 20 % la scarica non parte), ma nella scelta del piano conta solo
  il ricavo, quindi a parita' di prezzo non c'e' preferenza per la scarica lenta. Da chiarire con l'utente: a cosa si
  applica il peso, a quali impianti, se vale solo per scegliere il piano o anche nei conti in euro.
  Risposte dell'utente (07/11/2026): 16a - il peso si applica al ricavo dell'energia SCARICATA dalla batteria in quel
  quarto d'ora (es. scarica al 95 % della potenza massima: quell'energia vale 0,97 del prezzo); 17b - vale per la
  cessione totale E per Cismondi (scarica forzata 2-5 kW: 2 kW = 40 %, 4 kW = 80 %, 5 kW = 100 %); 18a - solo per
  scegliere il piano: i conti in euro restano quelli veri.
  Nota (verificata in config.lua): a Cismondi i livelli di scarica sono 2, 3, 4, 5 kW = 40, 60, 80, 100 % di 5 kW:
  con i pesi proposti 2-4 kW peso 1 (4 kW = 80 %, confine: da decidere se 0,98 o 1) e 5 kW peso 0,97.
  Confini (07/11/2026, utente 19a): dal 20 all'80 % compreso peso 1; oltre l'80 fino al 90 % peso 0,98; oltre il 90 %
  peso 0,97. Cismondi: 2, 3, 4 kW peso 1; 5 kW peso 0,97.
- Discontinuita' del 08/11 nella cessione (09/11/2026, immagine dell'utente: in rete 18:15-18:30, pausa, 19:00-20:00).
  Verificato sui dati del repository: e' il grafico dell'OTTIMO TEORICO (cessione/giorni/2026-11-08.json): scarica
  2,26 kWh alle 18:15, niente 18:30-18:45, poi 10 kW 19:00-20:00. Prezzi NORD: ore 18 = 0,3161, ore 19 = 0,3163 EUR/kWh
  (differenza 0,0002): l'ottimo teorico e' una programmazione lineare senza costo dei cambi, quindi fra soluzioni di
  ricavo quasi uguale ne sceglie una qualunque (stesso problema del 24/10). La regola "comandi costanti per ora" e il
  costo dei cambi (R05) valgono solo per la simulazione ogni 2 ore, non per l'ottimo teorico.
  Rimedi possibili (da decidere): peso per la continuita' (costo per ogni avvio/arresto della scarica) anche
  nell'ottimo teorico; i pesi della potenza di scarica della R09 (scarica piu' lenta preferita) allungherebbero la
  scarica su 18:00-20:00.
- PROBLEMA trovato il 09/11/2026 (cessione, simulazione ogni 2 ore): l'esecuzione e' ferma al 07/11 09:45 (indice
  live "eseguito fino a 07/11 09:45"; le decisioni continuano con lo stato di allora). Causa verificata nei dati:
  il dataset di Cismondi del 07/11 inizia alle 09:55 (con l'installazione R08 le colonne del dataset sono cambiate e
  registro.lua ha messo da parte il file del giorno iniziato e ne ha aperto uno nuovo); il quarto d'ora 09:45-10:00
  ha una sola lettura e cessione_live.py esegue i quarti solo in ordine e senza buchi, quindi resta fermo per sempre.
  Da correggere (su richiesta): superare un buco quando ci sono letture successive (es. dopo 1 ora), e leggere anche
  i file del giorno messi da parte.
- Continuita' della scarica (09/11/2026, utente 21a): peso minimo per la continuita': 0,001 EUR per ogni avvio o
  arresto della scarica, anche nell'ottimo teorico (solo per scegliere fra soluzioni quasi uguali). -> R10.
- Blocco della simulazione ogni 2 ore della cessione: CORRETTO nella R09 (09/11/2026, utente 22a), vedi REVISIONI.txt.
  La numerazione: R09 = sola correzione; le annotazioni prima chiamate R09 (pesi della potenza di scarica) e la
  continuita' passano alla R10.
- Cessione a potenza ridotta su tutto l'intervallo (11/11/2026, utente, immagine dell'ottimo teorico del 09/11:
  scarica a piena potenza 16:00-17:45 e 19:15-20:00): la cessione poteva essere distribuita su 17-18 e 19-20 con una
  potenza inferiore al 100 % per tutto l'intervallo. -> R10 (pesi della potenza + continuita', anche nell'ottimo teorico).
- Rendimento di scarica (e carica?) dipendente dalla potenza (11/11/2026, utente: valore non noto). Verifica sui dati
  veri di Cismondi (dati/ dal 17/10 al 10/11, tratti continui a potenza stabile, energia misurata contro variazione
  del SOC su 15 kWh nominali; SOC a passi dell'1 % = 0,15 kWh):
  - scarica: sotto 1 kW rapporto 0,85 (4 tratti); 1-2 kW 0,90 (5 tratti); oltre 2 kW nessun dato (l'automatismo
    attuale scarica solo sul consumo della casa);
  - carica: 1-2 kW 0,935 (6 tratti); 2-3 kW 0,963 (4 tratti); oltre 3 kW nessun dato.
  Quindi i dati mostrano solo che a bassa potenza il rendimento e' piu' basso (gia' nel modello della cessione:
  PERDITA_BASSA_POT); l'andamento fra 20 e 100 % non e' misurabile con i dati attuali. Da decidere con l'utente.
  Risposta dell'utente (11/11/2026, 24a): si usano i pesi gia' decisi (1 / 0,98 / 0,97) come parametro; il programma
  MISURA il rendimento vero per fascia di potenza quando ci saranno scariche e cariche a potenze piu' alte (fase 2 o
  giorni in cui capita) e lo mostra; i pesi restano quelli decisi finche' l'utente non decide altrimenti. -> R10.
  Risposta dell'utente (11/11/2026, 26a): quando la misura e' disponibile i pesi si AGGIORNANO DA SOLI con il
  rendimento misurato; nuova pagina html dedicata ai rendimenti della batteria. Dati: impianto di Cismondi (unica
  batteria vera: LUNA2000 15 kWh; dataset a 5 minuti con potenza della batteria e SOC). Da chiarire: se la cessione
  (batterie ipotetiche) usa i rendimenti misurati a Cismondi.
  Risposte dell'utente (11/11/2026): 27 si -> la cessione usa i rendimenti misurati a Cismondi (stesso tipo di
  batteria, LUNA2000). "28 si" (inteso come domanda 25, da confermare): anche la carica preferisce stare fra il 20 e
  l'80 % della potenza massima, con gli stessi pesi; precisazione dell'utente: l'energia ceduta direttamente in rete
  (quella che non entra in batteria) ha il prezzo orario e subisce solo le perdite di conversione (inverter), non le
  perdite di carica/scarica della batteria.
  Confermato (11/11/2026): la risposta "28 si" era la 25: anche la CARICA preferisce stare fra il 20 e l'80 % della
  potenza massima, con gli stessi pesi della scarica (1 / 0,98 / 0,97, poi rendimento misurato).
- Grafico del SOC insieme al grafico delle potenze (11/11/2026, utente). Stato attuale: nella pagina di Cismondi SOC e
  potenze sono due pannelli separati; nella pagina della cessione l'energia in batteria (kWh e %) e' gia' nel grafico
  del giorno. Da chiarire: pagina e curve di SOC (reale, simulati). -> R10.
- Idem per il grafico della potenza della batteria (11/11/2026, utente): anche la potenza della batteria nel grafico
  delle potenze. Stato attuale: nella pagina di Cismondi il grafico delle potenze ha gia' la potenza reale della
  batteria; il pannello "Potenza batteria" separato ha reale, automatico simulato e condizione 2. Da chiarire con la 30.
  Risposte dell'utente (11/11/2026): 30a - nel grafico delle potenze di Cismondi SOC REALE (scala % propria) e potenza
  reale della batteria; i pannelli separati "SOC batteria" e "Potenza batteria" si tolgono. 29a - nella cessione si
  aggiungono le perdite di conversione dell'inverter sull'energia ceduta, con il rendimento dell'inverter misurato a
  Cismondi per fascia di potenza (colonne eta_inv_500, eta_inv_1000, eta_inv_2000, eta_inv_oltre del dataset). -> R10.
  Risposta dell'utente (11/11/2026, 31c): anche le curve SIMULATE di SOC e potenza della batteria (automatico
  simulato e condizione 2) entrano nel grafico delle potenze, NASCOSTE all'inizio (si accendono dalla legenda). -> R10.
- Ottimo teorico della cessione (11/11/2026, utente): NON calcolarlo piu', per semplificare. -> R10.
  Cosa dipende oggi dall'ottimo teorico (cessione_totale.py main): grafico "Giorno - ottimo teorico", barre e colonne
  "ottimo teorico" (euro, beneficio, energia, mese per mese), totali del mese, cessione/giornaliero.csv, mensile.csv,
  giorni/*.json; per i giorni prima dell'avvio della simulazione ogni 2 ore (23/10/2026) anche il "senza batteria".
  Le funzioni comuni di cessione_totale.py (impianto, radiazione, prezzi) restano: le usa la simulazione ogni 2 ore.
  Il punto R10 "continuita' anche nell'ottimo teorico" decade. Da chiarire: giorni prima del 23/10 e file gia' salvati.
  Risposte dell'utente (11/11/2026): 33a - la pagina della cessione parte dal 23/10/2026 (avvio della simulazione ogni
  2 ore): i giorni prima si tolgono. 34a - i file dell'ottimo teorico gia' salvati nel repository si CANCELLANO
  (cessione/giornaliero.csv, cessione/mensile.csv, cessione/giorni/, cessione/indice.json dell'ottimo; da verificare
  al momento del codice quali altri file usa ancora la simulazione ogni 2 ore, es. cessione/prezzi e cessione/meteo).
- PROBLEMA trovato l'11/11/2026 (Cismondi, condizione 2), dal grafico "Piano calcolato" dell'11/11 mandato dall'utente:
  la condizione 2 e' ferma su "SCARICA_5000" (scarica forzata 5 kW) dal 30/10, con il SOC simulato fisso al 21 %
  (dataset: 288 quarti su 288 ogni giorno dal 30/10 al 10/11). Verificato nel codice e con l'ottimizzatore:
  - in scarica forzata la batteria non scende sotto SOC_MIN_VENDITA = 20 % e sotto 2 kW si ferma: al 21 % non scarica;
  - in scarica forzata l'esubero FV va in rete e la batteria NON si carica;
  - quindi la batteria simulata resta ferma (come senza batteria), ma il comando resta "scarica";
  - l'ottimizzatore non torna in AUTO perche' ogni cambio costa 0,10 EUR e in novembre (poco esubero FV, batteria
    vuota) il vantaggio stimato di AUTO e' piu' piccolo (prova con il piano dell'11/11: AUTO meglio di circa 0,01 EUR).
  Conseguenza: dal 30/10 i risultati della condizione 2 sono di fatto "batteria ferma" (es. 08/11: condizione 2 0,10 EUR
  peggio del reale). Rimedi da decidere con l'utente.
  CORREZIONE della diagnosi (11/11/2026, dopo la domanda dell'utente sul 10/11): con i prezzi VERI la batteria ferma
  della condizione 2 e' stata la scelta piu' conveniente. Dati del 10/11: prezzo NORD di vendita circa 0,36 EUR/kWh,
  acquisto a prezzo fisso 0,2415 EUR/kWh. Reale (automatico, batteria caricata dal 6 al 48 %): prelievo 14,8 kWh,
  immissione 0,06 kWh, netto 3,68 EUR. Condizione 2 (batteria ferma, esubero venduto): prelievo 21,1 kWh, immissione
  7,4 kWh venduti a circa 0,35, netto 2,50 EUR -> 1,19 EUR meglio del reale. Quando il prezzo di vendita supera
  quello di acquisto conviene vendere l'esubero e non caricare la batteria. La prova di prima (AUTO meglio di 0,01
  EUR) era fatta con prezzi inventati: non valida. Resta da sistemare: il nome dell'azione ("scarica forzata 5 kW"
  mentre la batteria e' ferma) e il caso in cui la batteria resta a lungo al 20-21 % senza poter essere usata.

## Revisione del progetto Cismondi (11/11/2026, richiesta dell'utente) - NIENTE CODICE finche' non richiesto
Richiesta: rivedere progetto e logiche per un sistema funzionante che MINIMIZZI L'ACQUISTO e di conseguenza
massimizzi la cessione ("che vale di meno"), usando la batteria in tutti i modi di funzionamento conosciuti;
per ora niente carica da rete.
Fatti verificati (repository all'11/11/2026):
- obiettivo attuale dell'ottimizzatore: minimo costo netto in euro = acquisti - cessioni + usura + 0,10 EUR per cambio;
- prezzi: acquisto fisso 0,2415 EUR/kWh; NORD dal 17/10 al 10/11: medie giornaliere 0,225-0,321, massimi fino a 0,427;
  in 384 ore su 601 (64 %) il NORD e' stato SOPRA il prezzo di acquisto -> in quelle ore vendere rende piu' che
  evitare un acquisto, e il minimo costo in euro porta a NON caricare la batteria (es. 10/11). In questo periodo la
  premessa "la cessione vale di meno" non e' vera;
- azioni simulate: AUTO (massimo autoconsumo), RITARDATA (carica limitata a 200 W), CARICA_FV (carica dall'esubero,
  niente scarica), SCARICA 2/3/4/5 kW (scarica forzata, anche verso la rete, fino al 20 %); "batteria ferma" non
  esiste come azione (oggi si ottiene di fatto con una scarica forzata impossibile);
- vincoli: 14 periodi forzati al giorno, 1 ciclo di scarica forzata al giorno, SOC 6-95 %, vendita fino al 20 %.
Da decidere con l'utente: obiettivo (kWh acquistati o euro), azioni da aggiungere, forma del lavoro di revisione.
Risposta dell'utente (11/11/2026): obiettivo = MINIMIZZARE GLI EURO, visto GIORNALMENTE, comprendendo gli acquisti
per i consumi di Cismondi, che devono essere GARANTITI. Possibile anche comprare quando costa poco e vendere quando
rende tanto, agendo sui modi di funzionamento della batteria (carica da rete esclusa per ora).
Fatti per la decisione: l'acquisto e' a prezzo fisso F0 (0,2415 EUR/kWh uguale a ogni ora): non ci sono ore di
acquisto a basso prezzo. Senza carica da rete lo scambio possibile e' indiretto: la batteria (caricata dal FV) vende
in rete nelle ore a prezzo NORD alto mentre la casa compra a 0,2415 (scarica forzata verso la rete: gia' simulata).
Da chiarire: significato di "garantire l'esigenza energetica" (riserva di batteria o solo consumi sempre coperti).
Precisazione dell'utente (11/11/2026): "compro quando costa poco" e' una semplificazione: la simulazione deve
funzionare con un PREZZO DI ACQUISTO ORARIO in generale (prezzo fisso = caso particolare). Cismondi oggi compra a
prezzo fisso; per l'impianto da 20 kW si vedra': predisporre tutto. Nel grafico va mostrato il prezzo di acquisto con
le sue componenti (energia, perdite, dispacciamento, trasporto, oneri, accise, IVA).
Nota: nella R07 sono state tolte le simulazioni PARALLELE con prezzi diversi dal fisso (decisione dell'utente); qui si
tratta di un'unica simulazione con prezzo di acquisto configurabile (fisso oppure orario). Da chiarire la formula del
prezzo orario.
Risposta dell'utente (11/11/2026, 39a): "garantire l'esigenza energetica" = i consumi della casa sono sempre coperti
(dalla rete se serve); la batteria si puo' svuotare quando conviene (nessuna riserva aggiuntiva oltre ai limiti
della batteria).
Regola di valore dell'utente (11/11/2026): caricare la batteria dai pannelli costa quanto la mancata vendita (prezzo
NORD dell'ora di carica); quando scarica, l'energia vale il mancato acquisto (prezzo di acquisto) finche' copre i
consumi della casa (scambio con la rete a zero); oltre, l'energia va in rete e vale il prezzo orario di vendita.
Verificato nel codice: il simulatore calcola i flussi quarto per quarto (FV->casa, FV->batteria, FV->rete,
batteria->casa, batteria->rete, rete->casa) e l'ottimizzatore valuta prelievo x prezzo di acquisto e immissione x
prezzo di vendita: e' la stessa regola, piu' le perdite di carica/scarica e l'usura (0,02 EUR/kWh scaricato).
Risposta dell'utente (11/11/2026, 41): limite di SOC per vendere in rete = 5 %. Nota: oggi il minimo della batteria
in config.lua e' SOC_MIN = 6 % ("Fine scarica SOC" dell'inverter): da chiarire se anche il minimo generale passa al 5 %.
Risposta dell'utente (11/11/2026): minimo generale della batteria = 5 % (SOC_MIN e SOC_MIN_VENDITA a 5 %); l'utente
deve impostare anche il "Fine scarica SOC" dell'inverter al 5 % perche' la simulazione corrisponda all'impianto.
Risposta dell'utente (11/11/2026): la parte "energia" del prezzo di acquisto orario la indichera' piu' avanti: per ora
si predispone solo la STRUTTURA (prezzo di acquisto per ora/quarto d'ora configurabile; Cismondi resta a prezzo fisso).

## Revisione delle logiche e delle annotazioni - riepilogo (11/11/2026, NIENTE CODICE)
Obiettivo (deciso): minimo costo in euro della giornata, consumi di Cismondi sempre coperti; valore dell'energia:
carica dal FV = mancata vendita, scarica = mancato acquisto fino a scambio zero, oltre = prezzo di vendita
(gia' cosi' nel simulatore). Niente carica da rete.
Azioni di Cismondi oggi (simulatore.lua): AUTO, RITARDATA (200 W), CARICA_FV (carica piena dall'esubero, niente
scarica), SCARICA 2/3/4/5 kW. Proposte della revisione:
- nuova azione BATTERIA FERMA (niente carica, niente scarica; esubero in rete, consumi dalla rete): oggi manca e la si
  ottiene con una scarica impossibile (nome fuorviante "scarica 5 kW" dal 30/10);
- carica dall'esubero a potenze graduate (es. 1-5 kW), per i pesi della potenza (fino all'80 % peso 1, 80-90 % 0,98,
  oltre 0,97): oggi la carica dall'esubero e' solo a piena potenza;
- nomi chiari delle azioni in grafici e tabelle;
- corrispondenza con i comandi Huawei (fase 2, documento 26.2.0): AUTO = maximumSelfConsumption; CARICA dall'esubero
  = finestra TOU di carica con allowedAcChargePower 0 e potenza massima di carica (5.2.5); SCARICA P = finestra TOU di
  scarica con maximumDischargePower P, oppure thirdPartyDispatch -P; BATTERIA FERMA = thirdPartyDispatch 0 W
  (5.2.9: "0 fermo"). Da verificare sull'impianto prima della fase 2.
Incoerenza trovata: costo per cambio di comando a Cismondi 0,10 EUR (PENALITA_CAMBIO_EUR) contro il peso minimo di
continuita' 0,001 EUR deciso per la cessione: il costo di 0,10 EUR blocca cambi che renderebbero meno di 0,10 EUR.
Da decidere con l'utente. Altri vincoli da confermare: 14 periodi forzati al giorno, 1 ciclo di scarica forzata al
giorno, 0,01 EUR per ora sopra il 90 % di SOC.
Gia' deciso per la R10: SOC minimo 5 % (casa e vendita; Fine scarica SOC dell'inverter al 5 %), prezzo di acquisto
orario (struttura) con componenti nel grafico, pesi della potenza e rendimenti misurati (pagina nuova), perdite di
conversione nella cessione, SOC e potenza batteria nel grafico delle potenze, ottimo teorico della cessione tolto
(pagina dal 23/10, file cancellati), peso di continuita' 0,001 EUR nella cessione.
Altro trovato: il pannello "Piano calcolato" mostra sempre l'ultimo piano, non quello del giorno scelto.
Decisione 1 (11/11/2026): costo per cambio di comando a Cismondi = 0,001 EUR (come la continuita' della cessione).
Decisione 2 (11/11/2026): restano entrambi i limiti a Cismondi: 14 periodi forzati al giorno e 1 ciclo di scarica
forzata al giorno (motivo: in futuro l'utente abilitera' la carica da rete; per ora no).
Decisione 3 (11/11/2026): resta il costo di 0,01 EUR per ogni ora con SOC sopra il 90 % (Cismondi).
Decisione 4 (11/11/2026): a Cismondi si aggiungono (a) l'azione BATTERIA FERMA (niente carica e niente scarica;
comando Huawei: potenza 0 W) e la CARICA DALL'ESUBERO A POTENZE GRADUATE 1, 2, 3, 4, 5 kW (pesi: 1-4 kW peso 1,
5 kW peso 0,97).
Decisione 5 (11/11/2026): il pannello "Piano calcolato" mostra il piano del GIORNO SCELTO (quello calcolato la sera
prima per quel giorno: dati/AAAA-MM-GG/piano_sera.csv, presente nei giorni simulati); per domani resta l'ultimo piano.
Precisazione dell'utente sull'obiettivo (11/11/2026): non solo la giornata: va valutata anche la giornata SUCCESSIVA,
considerando l'energia rimasta in batteria per ridurre il costo del giorno dopo.
Stato attuale (verificato in ems_sim.lua): l'orizzonte dell'ottimizzatore arriva alla fine dei prezzi noti (oggi; dopo
le 13:30 circa anche domani, quando il GME pubblica i prezzi); all'energia rimasta a fine orizzonte si da' il valore
del costo medio di acquisto per i kWh che serviranno nella notte successiva (previsione, al massimo 14 ore).
Da decidere con l'utente come estendere (vedi cessione: orizzonte sempre fino a fine domani con prezzi previsti).
Risposta dell'utente (11/11/2026): dalle 13:30 (prezzi di domani noti) si valuta anche il giorno dopo (in particolare
la scarica nelle prime ore notturne); tanto il tutto si rivaluta ogni n ore. -> resta l'orizzonte attuale (fino
all'ultimo prezzo noto), che gia' fa questo. Stato attuale della rivalutazione a Cismondi: piano ricalcolato a ogni
quarto d'ora quando il programma gira (su GitHub i giri sono ogni 30 minuti, a volte saltati). Da chiarire "n".
Risposta dell'utente (11/11/2026): i piani si ricalcolano DOPO il recupero delle informazioni da Huawei. Verificato in
ems_sim.lua (ciclo): prima la lettura Huawei (su GitHub: le letture a 5 minuti dallo storico Huawei arrivate dal giro
precedente), poi la decisione del quarto d'ora con il piano ricalcolato: e' gia' cosi'. Nessun cambiamento.
- Frequenza dei giri (11/11/2026, domanda dell'utente). Verificato: ems.yml e' programmato ogni 30 minuti (minuti 7 e
  37), ma dal 03/11 all'11/11 GitHub ha fatto 33 giri: da 3 a 6 al giorno, intervallo medio 5,7 ore (minimo 0,4,
  massimo 11 ore). A ogni giro il programma (modalita' GitHub di ems_sim.lua) rigioca UNA PER UNA tutte le letture a
  5 minuti arrivate dal giro precedente, con l'ora simulata, e ricalcola il piano a ogni quarto d'ora simulato, come
  farebbe il Mango (che girera' ogni 5 minuti). Da verificare: quale previsione meteo usano le decisioni rigiocate
  (quella scaricata al momento del giro, piu' recente di quella che il Mango avrebbe avuto).
  Decisione dell'utente (11/11/2026, 1b): si ANTICIPA l'avvio dei giri da parte del Mango: il Mango avvia il workflow
  ems.yml ogni 30 minuti (API GitHub workflow_dispatch, come fa gia' INSTALLA_EMS). Serve: Mango collegato a Internet
  (router), curl, un token GitHub con permesso "workflow" salvato sul Mango, una riga di cron. Da chiarire lo stato
  del Mango.
  Mango reale (11/11/2026, dati dall'utente via SSH): GL.iNet GL-MT300N-V2, OpenWrt 22.03.4 (ramips/mt76x8, mipsel_24kc),
  RAM ~119 MB (disponibili ~68 MB), flash /overlay 1,6 MB (836 kB liberi), /tmp 59 MB in RAM, Lua 5.1.5 (double int32),
  curl e wget presenti, crontab vuoto.
  Benchmark (benchmark_mango.lua, config con PROFILI = {"C2"}): Mango totale 45,955 s (batteria 0,180 / ottimizzatore
  39,393 / json 6,381), real 55,75 s; GitHub 0,258 s (0,001 / 0,217 / 0,040). FATTORE_MANGO misurato ~178 (non ancora
  scritto in config.lua). Non verificato: che il piano calcolato sul Mango sia identico a quello di GitHub.
  La parte Python (ml/) non e' installabile sul Mango (flash 1,6 MB; numpy+pandas+scipy ~180 MB).
  Passaggi dell'ottimizzatore nei giorni reali (11/11/2026): rigioco C2 sui dati Cismondi 20/09-16/10/2026 (27 giorni,
  648 piani, uno all'ora, meteo previsto dall'archivio Open-Meteo gia' salvato in rigioco/meteo), conteggio fatto su una
  copia del programma: 1 passaggio 626 piani (96,6 %), 3 -> 5, 4 -> 3, 6 -> 2, 7 -> 1, 8 -> 11 (1,7 %); media 1,17.
  Stima sul Mango (~39 s per passaggio su 136 quarti): di solito <= 40 s, nei casi peggiori fino a ~5 minuti.
  Dettaglio dei piani con piu' passaggi (12/11/2026): 22 piani su 648, concentrati in 3 giorni (20/09 13-22,
  11/10 13 e 12/10 00, 13/10 13-22). Causa sempre il limite di 1 ciclo forzato al giorno (15 kWh): nei passaggi
  successivi il costo per kWh (lambda_e) viene abbassato per tentativi e il piano salta a 15,5-20,4 kWh di scarica
  forzata (oltre il limite) e viene scartato. Il limite di 14 finestre non e' mai stato superato (0 casi).
  Non verificato: se i passaggi dal 2 in poi cambiano il piano scelto rispetto al primo.
  Effetto dei passaggi in piu' (12/11/2026, stessi 22 piani): in 16 piani il piano finale e' identico al primo
  passaggio (passaggi 2-8 senza effetto); in 4 il primo passaggio superava il limite di ciclo (passaggi necessari);
  in 2 (20/09 14:00 +0,32 EUR, 20/09 22:00 +0,26 EUR di valore piano) i passaggi successivi hanno trovato un piano
  migliore entro il limite. In tutti i 22 l'azione del primo quarto d'ora e' identica; le differenze iniziano
  dopo 26-89 quarti d'ora (6,5-22 ore), quindi nel rigioco orario nessuna azione eseguita e' cambiata.
  Perche' solo 22 piani: dopo un primo passaggio entro i limiti la ricerca continua solo se il costo di ciclo
  ereditato dal piano precedente (lambda_e) e' > 0,01 EUR/kWh (e al massimo fino al passaggio 3), oppure se c'e'
  una violazione; negli altri 626 piani nessuna delle due condizioni.
  Conferma (12/11/2026): GitHub resta per calcoli, memoria, pagine ed email. Il Mango NON calcola: avvia soltanto il
  workflow ems.yml ogni 30 minuti (1 riga di cron + curl, ~1 s). Motivo: il Mango e' l'unico dispositivo acceso e
  collegato 24 ore su 24 (il PC no con certezza); scartato il servizio cron esterno (token presso terzi).
  Sul Mango servono: token GitHub con permesso di avviare i workflow (solo repository ems-dati) salvato in un file
  leggibile solo da root, servizio cron di OpenWrt abilitato, riga di crontab. Nessun programma Lua da copiare.
  Verifica (12/11/2026): ems.yml ha gia' workflow_dispatch e concurrency (group ems, cancel-in-progress false: un giro
  alla volta, al massimo uno in attesa). Durata dei giri dalla pagina Actions (#135-#142): da 1 min 2 s a 4 min 55 s,
  quindi molto sotto i 30 minuti. Intervalli tra giri programmati ancora di ore (es. 11/11 23:39 -> 12/11 04:46).
  Giro #139 (11/11 17:05, 4 min 55 s) FALLITO: causa da verificare.
  Decisione token (12/11/2026): sul Mango si usa lo STESSO token classico del PC (permessi repo e workflow su tutti
  i repository), salvato in un file leggibile solo da root. Rischio accettato dall'utente: chi accedesse al Mango
  avrebbe accesso completo ai repository. Non va mai scritto in file del repository ne' nei documenti.
  Richiesta (12/11/2026): SIMULATORE PER PC, file .exe per Windows 11, con tutte e tre le funzioni:
  a) prove "cosa succede se" (giorno reale o inventato, prezzi/consumi/FV/batteria/regole modificabili -> piano, SOC, euro);
  b) giri al posto di GitHub; c) confronto programmazione dinamica vs algoritmo genetico (euro e tempi).
  Nota tecnica certa: l'.exe Windows (es. PyInstaller) si costruisce su Windows, non dal contenitore Linux; si puo'
  costruire con un workflow GitHub su runner windows-latest. Da chiarire: punto b (il PC non e' acceso 24 h con
  certezza; le pagine sono su GitHub Pages), algoritmo genetico (dell'utente o da scrivere).
  Chiarimento (12/11/2026): il simulatore per PC deve SOLO far vedere graficamente cosa fa il sistema; nessuna modifica
  a quanto gia' fatto (GitHub, Mango, repository, workflow restano invariati; il simulatore non scrive su GitHub).
  Dati del simulatore PC (12/11/2026, c): copia locale sul PC, aggiornata in sola lettura dal repository pubblico quando c'e' Internet (nessun token).
  Viste del simulatore PC (12/11/2026, tutto): vista a filmato quarto per quarto (dati usati, piano, azione, flussi, SOC, euro; play/pausa/avanti/indietro) + vista a grafici del giorno + modifiche 'cosa succede se' + confronto programmazione dinamica / algoritmo genetico.
  Precisazione (12/11/2026): il simulatore per PC e' per l'impianto CESSIONE TOTALE 20 kW (non Cismondi). L'utente
  chiede che scriva e compili tutto io, senza azioni da parte sua. Nota: la cessione usa GIA' un algoritmo evolutivo
  (cessione_ottimizza.py: fasce di 2 ore, modi Fully/TOU/Third-party, 3 scenari di produzione, semi da LP e fuzzy).
  Nota tecnica: dal contenitore il sito python.org e' bloccato (403), quindi non posso impacchettare Python per
  Windows; possibile invece un .exe unico compilato in Go (incrociato per Windows) con pagina grafica nel browser.
  Ordine deciso (12/11/2026, a): PRIMA la revisione R10, POI il simulatore per PC della cessione (che copia la logica R10).

## R10 - elenco unico (12/11/2026, NIENTE CODICE finche' non richiesto)
DECISO - Cismondi:
 D1 SOC_MIN e SOC_MIN_VENDITA = 5 % (l'utente imposta "Fine scarica SOC" dell'inverter al 5 %).
 D2 Costo per cambio di comando 0,001 EUR. Restano: 14 periodi forzati/giorno, 1 ciclo forzato/giorno, 0,01 EUR/ora SOC > 90 %.
 D3 Nuove azioni: BATTERIA FERMA (0 W) e CARICA DALL'ESUBERO a 1-5 kW. Nomi chiari delle azioni in grafici e tabelle.
 D4 Pesi della potenza (solo per scegliere il piano): scarica e carica, fino all'80 % peso 1, 80-90 % 0,98, oltre 0,97
    (Cismondi: 1-4 kW peso 1, 5 kW 0,97); rendimento misurato per fascia di potenza; nuova pagina html dei rendimenti.
 D5 Prezzo di acquisto orario: solo struttura (Cismondi resta a prezzo fisso); componenti del prezzo nel grafico.
 D6 Grafico delle potenze: SOC reale (scala %) e potenza reale della batteria; curve simulate nascoste all'inizio;
    tolti i pannelli separati "SOC batteria" e "Potenza batteria".
 D7 "Piano calcolato" = piano del giorno scelto (dati/<g>/piano_sera.csv); per domani l'ultimo piano.
 D8 Il Mango avvia ems.yml ogni 30 minuti (curl + cron, token classico del PC in file leggibile solo da root).
 Invariati (verificati): orizzonte fino all'ultimo prezzo noto (dalle 13:30 anche domani); piano ricalcolato dopo le letture Huawei.
DECISO - Cessione totale:
 D9  Pesi della potenza di scarica e carica (come D4) e rendimenti batteria misurati a Cismondi.
 D10 Perdite di conversione dell'inverter sull'energia ceduta (eta_inv per fascia, misurato a Cismondi).
 D11 Continuita': 0,001 EUR per ogni avvio o arresto della scarica.
 D12 Ottimo teorico tolto: pagina dal 23/10/2026, file dell'ottimo cancellati (si tengono quelli usati dalla simulazione ogni 2 ore).
APERTO:
 A1 Come il rendimento misurato diventa peso ("i pesi si aggiornano da soli"): formula non definita.
 A2 Prezzo di acquisto orario: formula delle componenti con la parte "energia" variabile.
 A3 Installazione sul Mango: da qui non raggiungo il Mango (rete di casa); serve un passo fatto dall'utente o dal PC.
 A4 Caso "batteria a lungo al 20-21 % senza poter essere usata" (11/11): da confermare se risolto da D1 + D3.
 A5 Da verificare (non codice): previsione meteo usata dalle decisioni rigiocate su GitHub; servizio cron del Mango abilitato.
 Non indagato per scelta dell'utente: giro #139 fallito.
 A1 deciso (12/11/2026, a): peso fascia = rendimento misurato della fascia / miglior rendimento misurato (la migliore = 1); senza misure resta il peso fisso (1 / 0,98 / 0,97). Da chiudere: quante misure servono per considerare valida una fascia.
 A1-bis deciso (12/11/2026, b): una fascia e' valida con almeno 10 tratti, ciascuno di almeno 1,5 kWh (10 % di SOC).
 A2 deciso (12/11/2026, a): prezzo orario = stessa formula di oggi con 'energia' oraria (fonte indicata piu' avanti); perdite, dispacciamento, trasporto, oneri, accise e IVA restano fissi.
 A3 prova c (12/11/2026): dal computer collegato alla sessione la rete locale non e' raggiungibile (connessione diretta: 'Network is unreachable'; HTTP via proxy: 403). Strada c esclusa.
 A3 riprova (12/11/2026, Mango a 192.168.1.1 con VPN attiva): dal computer collegato il proxy di rete della sessione rifiuta la connessione (CONNECT 192.168.1.1:22 Forbidden). Strada c esclusa: dipende dalle impostazioni di rete dell'organizzazione.

## R10 APPLICATA (12/11/2026, "crea codice" dell'utente): D1-D12 e A1, A2, A3 (strada a: INSTALLA_EMS.bat via SSH).
Restano aperti: A4 (batteria a lungo al 20-21 %: con SOC minimo 5 % e BATTERIA FERMA dovrebbe sparire, da verificare
sui giorni dopo l'installazione), A5 (meteo usato dalle decisioni rigiocate; servizio cron del Mango: lo verifica il
passo Mango di INSTALLA_EMS). Dopo: simulatore per PC della cessione totale (.exe Windows, solo visualizzazione).
