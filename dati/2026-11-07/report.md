# Report EMS Cismondi - 07/11/2026 (sabato)

**SOLO SIMULAZIONE**: nessun comando inviato all'inverter.

## Scenari

Prezzo d'acquisto fisso F0: 0.12 EUR/kWh di energia, 0.2415 EUR/kWh con i costi aggiuntivi (perdite 10 % su energia e spread, dispacciamento 0.0170, trasporto 0.0147, oneri di sistema 0.0332, accise 0.0227 EUR/kWh, IVA 10 %).

| Condizione | Descrizione |
|---|---|
| **0** | Impianto senza batteria: solo autoconsumo istantaneo del FV, il resto si compra, l'eccedenza si cede. |
| **1** | Impianto con batteria senza ottimizzazione (come oggi): dati REALI misurati da Huawei. |
| **2 (senza carica AC)** | Batteria con ottimizzazione di carica e scarica, senza carica AC dalla rete. |
| controllo | Automatico simulato: la condizione 1 rifatta dal simulatore, per misurarne la precisione. |

Cessioni (RID): prezzo zonale NORD del quarto d'ora. Usura batteria: 0.020 EUR per kWh scaricato. Ogni scenario ha la sua batteria simulata e l'ottimizzatore sceglie ogni 15 minuti tra autoconsumo, carica ritardata, carica forzata e scarica forzata a potenze graduate, con al massimo 14 periodi forzati e 1 ciclo di scarica forzata al giorno. Ogni cambiamento di funzionamento costa 0.10 EUR: si cambia solo se conviene anche pagandolo.

Letture: 288, ore integrate: 24.00. FV 13.51 kWh, consumi casa 30.50 kWh.
Reale: prelievo 17.85 kWh, immissione 0.24 kWh.  Solo autoconsumo simulato: prelievo 17.63 kWh, immissione 0.00 kWh.
Condizione 0 (senza batteria): prelievo 21.55 kWh (5.04 EUR), immissione 4.56 kWh (1.06 EUR), netto 3.98 EUR.
Condizione 1 (reale): acquisti 4.14 EUR, cessioni 0.06 EUR, usura batteria (3.85 kWh scaricati) inclusa: netto 4.16 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 21.55 | 4.56 | 5.04 | 1.06 | 0.00 | 0 (0.00) | 3.92 (0.95) | 4.56 (1.06) | 0.18 | 0.19 | 0.62 | 0.00 | -0.16 | 1 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 785.79 W, modello 784.26 W.  FV: sera prima 201.79 W, modello 209.65 W.
Rendimenti usati: carica 0.975, scarica 0.881. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.152 s, massimo 2.834 s (qui). Calcolo del piano: massimo 0.883 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 34705.53 kB. Scritture nella memoria interna 1370.79 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 30, GitHub 26; dati ricevuti circa 1299.93 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2 | 00:00 | 00:00 | SCARICA_5000 | 20.83 -> 20.83 | carica 0.00, scarica 0.00 | piano -3.92 EUR fino a fine prezzi; vantaggio su AUTO 0.130 EUR |
