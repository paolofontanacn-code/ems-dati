# EMS Cismondi - simulazione su GitHub

Revisione R03 - 23/10/2026 (elenco delle revisioni: REVISIONI.txt)

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

## Cessione totale 20 kW (dal 23/10/2026, pagina `cessione.html`) - revisione R03

Simulazione a parte, solo calcolo: impianto ipotetico da 20 kW in cessione totale (prodotto = ceduto), venduto in RID
al prezzo orario zonale NORD (PO NORD).
- **Impianto**: 20 kW di pannelli a Ovest, inclinazione 2 gradi; 2 x SUN2000-10KTL-M1 e 2 batterie da 15 kWh, calcolati
  come un inverter da 20 kW con una batteria da 30 kWh (carica e scarica max 10 kW, perdita 5 %); verso la rete max
  17 kW; nessun prelievo dalla rete, nessuna carica da AC.
- **Produzione**: Cismondi (11 kW, Sud, 2 gradi; i dati piu' freschi) x 20 / 11 x rapporto irraggiamento Ovest / Sud
  (radiazione diretta e diffusa Open-Meteo, modello isotropo).
- **Simulazione ogni 2 ore, da oggi in avanti** (`ml/cessione_live.py`, risultati in `cessione/live/`): a ogni fascia
  di 2 ore rivaluta tutto (previsione della produzione con piu' modelli meteo - il migliore per orizzonte secondo
  l'errore misurato - correzione imparata per ora del giorno, correzione con le ultime letture; prezzi noti;
  energia in batteria) e sceglie la modalita' Huawei con il ricavo atteso piu' alto: Fully fed to grid, TOU (max 14
  fasce al giorno), Third-party dispatch. Poi i quarti d'ora vengono "vissuti" con la produzione vera. Impara anche
  lo scarto atteso/ottenuto di ogni modalita' (provata in parallelo anche quando non e' scelta).
- **Ottimo teorico dei giorni passati** (`ml/cessione_totale.py`): produzione e prezzi noti in anticipo (limite
  massimo); senza batteria e con batteria.
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
- **Regola di lavoro (23/10/2026)**: il codice si scrive solo su richiesta esplicita; le indicazioni si annotano e si
  chiariscono prima con domande.
- **Simulazione su richiesta (22/10/2026)**: dalla pagina si impostano i parametri di una simulazione e la si avvia
  subito (avvio di un giro dedicato su GitHub con il token salvato nel browser); risultati mostrati nella pagina a
  parte, senza toccare le simulazioni normali ne' i comandi all'inverter. Parametri e periodo: da definire.
