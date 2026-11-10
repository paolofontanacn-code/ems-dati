# Report EMS Cismondi - 09/11/2026 (feriale)

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

Letture: 288, ore integrate: 24.00. FV 7.32 kWh, consumi casa 24.11 kWh.
Reale: prelievo 17.10 kWh, immissione 0.04 kWh.  Solo autoconsumo simulato: prelievo 17.18 kWh, immissione 0.00 kWh.
Condizione 0 (senza batteria): prelievo 19.64 kWh (4.74 EUR), immissione 2.86 kWh (0.91 EUR), netto 3.83 EUR.
Condizione 1 (reale): acquisti 4.13 EUR, cessioni 0.01 EUR, usura batteria (2.56 kWh scaricati) inclusa: netto 4.17 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 19.64 | 2.86 | 4.74 | 0.91 | 0.00 | 0 (0.00) | 2.46 (0.60) | 2.86 (0.91) | 0.34 | 0.37 | 0.80 | 0.00 | -0.01 | 1 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 680.01 W, modello 680.01 W.  FV: sera prima 169.87 W, modello 130.27 W.
Rendimenti usati: carica 0.977, scarica 0.884. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.083 s, massimo 0.637 s (qui). Calcolo del piano: massimo 0.350 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 11539.06 kB. Scritture nella memoria interna 1233.76 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 27, GitHub 26; dati ricevuti circa 1270.19 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2 | 00:00 | 00:00 | SCARICA_5000 | 20.83 -> 20.83 | carica 0.00, scarica 0.00 | piano -3.92 EUR fino a fine prezzi; vantaggio su AUTO 0.130 EUR |
