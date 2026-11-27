# Report EMS Cismondi - 26/11/2026 (feriale)

**SOLO SIMULAZIONE**: nessun comando inviato all'inverter.

## Scenari

Prezzo d'acquisto fisso F0: 0.12 EUR/kWh di energia, 0.2415 EUR/kWh con i costi aggiuntivi (perdite 10 % su energia e spread, dispacciamento 0.0170, trasporto 0.0147, oneri di sistema 0.0332, accise 0.0227 EUR/kWh, IVA 10 %).

| Condizione | Descrizione |
|---|---|
| **0** | Impianto senza batteria: solo autoconsumo istantaneo del FV, il resto si compra, l'eccedenza si cede. |
| **1** | Impianto con batteria senza ottimizzazione (come oggi): dati REALI misurati da Huawei. |
| **2 (programmazione dinamica)** | Batteria con ottimizzazione di carica e scarica, senza carica AC dalla rete. |
| **3 (algoritmo evolutivo)** | Batteria con ottimizzazione di carica e scarica, senza carica AC dalla rete. |
| controllo | Automatico simulato: la condizione 1 rifatta dal simulatore, per misurarne la precisione. |

Cessioni (RID): prezzo zonale NORD del quarto d'ora. Usura batteria: 0.020 EUR per kWh scaricato. Ogni scenario ha la sua batteria simulata e l'ottimizzatore sceglie ogni 15 minuti tra autoconsumo, carica ritardata, carica forzata e scarica forzata a potenze graduate, con al massimo 14 periodi forzati e 1 ciclo di scarica forzata al giorno. Ogni cambiamento di funzionamento costa 0.001 EUR: si cambia solo se conviene anche pagandolo.

Letture: 288, ore integrate: 24.00. FV 9.74 kWh, consumi casa 31.14 kWh.
Reale: prelievo 21.75 kWh, immissione 0.05 kWh.  Solo autoconsumo simulato: prelievo 21.97 kWh, immissione 0.00 kWh.
Condizione 0 (senza batteria): prelievo 25.64 kWh (6.19 EUR), immissione 4.23 kWh (1.32 EUR), netto 4.87 EUR.
Condizione 1 (reale): acquisti 5.25 EUR, cessioni 0.01 EUR, usura batteria (3.94 kWh scaricati) inclusa: netto 5.32 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 25.32 | 6.34 | 6.12 | 2.03 | 0.08 | 8 (0.01) | 3.35 (0.81) | 6.34 (2.03) | 1.15 | 1.21 | 1.72 | 0.70 | 0.32 | 9 |
| C3 | 25.64 | 4.12 | 6.19 | 1.28 | 0.01 | 3 (0.00) | 3.67 (0.89) | 4.12 (1.28) | 0.39 | 0.45 | 0.45 | -0.06 | 0.05 | 3 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 732.34 W, modello 732.34 W.  FV: sera prima 163.72 W, modello 163.72 W.
Rendimenti usati: carica 0.980, scarica 0.887. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.174 s, massimo 0.951 s (qui). Calcolo del piano: massimo 0.852 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 20356.60 kB. Scritture nella memoria interna 1470.67 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 28, GitHub 26; dati ricevuti circa 1283.78 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2 | 00:00 | 11:45 | CARICA_FV_1000 | 42.13 -> 45.46 | carica 0.51, scarica 0.00 | piano -12.20 EUR fino a fine prezzi; vantaggio su AUTO 0.007 EUR |
| C2 | 11:45 | 12:00 | SCARICA_2000 | 45.46 -> 41.70 | carica 0.00, scarica 0.50 | piano -2.75 EUR fino a fine prezzi; vantaggio su AUTO 0.005 EUR |
| C2 | 12:00 | 13:00 | CARICA_FV_1000 | 41.70 -> 48.23 | carica 1.00, scarica 0.00 | piano -2.89 EUR fino a fine prezzi; vantaggio su AUTO 0.012 EUR |
| C3 | 12:00 | 13:00 | BATTERIA_FERMA | 10.53 -> 10.53 | carica 0.00, scarica 0.00 | piano -4.11 EUR fino a fine prezzi; vantaggio su AUTO 0.046 EUR |
| C2 | 13:00 | 13:15 | SCARICA_3000 | 48.23 -> 42.58 | carica 0.00, scarica 0.75 | piano -2.29 EUR fino a fine prezzi; vantaggio su AUTO 0.007 EUR |
| C3 | 13:00 | 13:45 | SCARICA_3000 | 10.53 -> 5.00 | carica 0.00, scarica 0.74 | piano -3.78 EUR fino a fine prezzi; vantaggio su AUTO 0.018 EUR |
| C2 | 13:15 | 14:15 | BATTERIA_FERMA | 42.58 -> 42.58 | carica 0.00, scarica 0.00 | piano -2.48 EUR fino a fine prezzi; vantaggio su AUTO 0.003 EUR |
| C2 | 14:15 | 14:30 | SCARICA_3000 | 42.58 -> 36.94 | carica 0.00, scarica 0.75 | piano -12.11 EUR fino a fine prezzi; vantaggio su AUTO 0.013 EUR |
| C2 | 14:30 | 14:45 | CARICA_FV_1000 | 36.94 -> 37.35 | carica 0.06, scarica 0.00 | piano -12.27 EUR fino a fine prezzi; vantaggio su AUTO 0.012 EUR |
| C2 | 14:45 | 15:15 | SCARICA_4000 | 37.35 -> 22.31 | carica 0.00, scarica 2.00 | piano -12.17 EUR fino a fine prezzi; vantaggio su AUTO 0.016 EUR |
| C2 | 15:15 | 00:00 | CARICA_FV_1000 | 22.31 -> 22.31 | carica 0.00, scarica 0.00 | piano -13.02 EUR fino a fine prezzi; vantaggio su AUTO 0.037 EUR |
| C3 | 13:45 | 00:00 | BATTERIA_FERMA | 5.00 -> 5.00 | carica 0.00, scarica 0.00 | piano -13.59 EUR fino a fine prezzi; vantaggio su AUTO 0.001 EUR |
