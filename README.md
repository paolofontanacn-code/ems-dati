# EMS Cismondi - simulazione su GitHub

**SOLO SIMULAZIONE**: nessun comando viene inviato all'inverter Huawei.

Ogni 2 ore GitHub esegue **lo stesso programma che girerà sul Mango** (cartella `mango/`, in Lua) e misura il
carico di lavoro che il Mango avrebbe. I dati dell'impianto arrivano dallo **storico Huawei a 5 minuti**: le letture
vengono "rigiocate" una per una, come se il Mango le leggesse in tempo reale ogni 5 minuti. Il machine learning
gira in Python (cartella `ml/`).

## Scenari simulati

| Scenario | Prezzo dell'energia acquistata |
|---|---|
| **A** - prezzo fisso | 0,12 EUR/kWh |
| **B** - PUN per fascia | PUN medio mensile della fascia F1/F2/F3 + spread 0,02 EUR/kWh |
| **C** - PUN orario | PUN dell'ora + spread 0,02 EUR/kWh |
| Solo autoconsumo | riferimento: batteria in massimo autoconsumo, senza ottimizzatore |

A tutti si aggiungono: perdite 10 % (su energia e spread), dispacciamento (valore non ancora noto, per ora 0),
trasporto 0,014730, oneri di sistema 0,033153, accise 0,0227 EUR/kWh, IVA 10 %.
Le cessioni (RID) valgono il prezzo zonale orario NORD meno l'imposta del 40 %.
Ogni scenario ha la sua batteria simulata (SOC proprio). Ogni 15 minuti l'ottimizzatore sceglie tra autoconsumo,
carica ritardata, carica forzata (solo FV o FV + rete fino a 1 kW di giorno) e scarica forzata (1, 2, 3 o 5 kW),
con al massimo 14 periodi forzati al giorno. Ogni cambiamento di funzionamento ha un costo attribuito di 0,10 EUR.

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
2. **Ogni 2 ore** (`.github/workflows/ems.yml`): scarica lo storico Huawei delle ultime ore (3 chiamate per giorno
   coinvolto), rigioca le letture ogni 5 minuti con il programma del Mango, scarica prezzi GME (dalle 13:30) e meteo,
   ottimizza, registra, chiude i giorni finiti; poi il machine learning riaddestra i modelli e prepara le previsioni.
3. Le chiamate reali a Huawei sono circa 70-110 al giorno (il Mango ne farebbe circa 870 con le letture ogni 5 minuti).
4. Ogni giro dura indicativamente 2-4 minuti: circa 700-1.400 minuti al mese sui 2.000 gratuiti per i repository
   privati (da verificare nel tab Actions dopo i primi giorni).

Avvio manuale: tab **Actions** > **EMS simulazione** > **Run workflow**.

## Installazione

Si fa dal PC con `INSTALLA_EMS.bat` (pacchetto Installa_EMS): crea o prepara questo repository, carica i file,
imposta segreti e permessi, avvia il primo giro e ne controlla l'esito. Se si rilancia, riparte da zero
con una nuova autorizzazione Huawei.
