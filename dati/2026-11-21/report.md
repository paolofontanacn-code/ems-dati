# Report EMS Cismondi - 21/11/2026 (sabato)

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

Letture: 288, ore integrate: 24.00. FV 17.35 kWh, consumi casa 26.19 kWh.
Reale: prelievo 8.80 kWh, immissione 0.17 kWh.  Solo autoconsumo simulato: prelievo 9.48 kWh, immissione 0.00 kWh.
Condizione 0 (senza batteria): prelievo 19.37 kWh (4.68 EUR), immissione 10.53 kWh (1.82 EUR), netto 2.86 EUR.
Condizione 1 (reale): acquisti 2.13 EUR, cessioni 0.03 EUR, usura batteria (10.72 kWh scaricati) inclusa: netto 2.31 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 18.83 | 4.79 | 4.55 | 1.15 | 0.08 | 5 (0.01) | 9.35 (2.26) | 4.79 (1.15) | -1.17 | -1.00 | 0.30 | -0.62 | 0.09 | 5 |
| C3 | 15.89 | 5.64 | 3.84 | 1.45 | 0.18 | 3 (0.00) | 6.40 (1.55) | 5.64 (1.45) | -0.26 | -0.08 | -0.18 | 0.29 | 0.02 | 2 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 763.62 W, modello 763.62 W.  FV: sera prima 216.20 W, modello 126.46 W.
Rendimenti usati: carica 0.978, scarica 0.887. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.161 s, massimo 1.190 s (qui). Calcolo del piano: massimo 0.887 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 19994.65 kB. Scritture nella memoria interna 1396.43 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 29, GitHub 26; dati ricevuti circa 1278.73 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2 | 00:00 | 10:00 | CARICA_FV_1000 | 22.69 -> 27.97 | carica 0.81, scarica 0.00 | piano -9.38 EUR fino a fine prezzi; vantaggio su AUTO 0.003 EUR |
| C3 | 17:15 | 20:00 | CARICA_FV_2000 | 60.11 -> 60.11 | carica 0.00, scarica 0.00 | piano -10.76 EUR fino a fine prezzi; vantaggio su AUTO 0.008 EUR |
| C2 | 10:00 | 20:15 | CARICA_FV_2000 | 27.97 -> 82.66 | carica 8.39, scarica 0.00 | piano -2.15 EUR fino a fine prezzi; vantaggio su AUTO 0.001 EUR |
| C2 | 20:15 | 20:45 | SCARICA_4000 | 82.66 -> 67.62 | carica 0.00, scarica 2.00 | piano -8.46 EUR fino a fine prezzi; vantaggio su AUTO 0.007 EUR |
| C2 | 20:45 | 21:00 | CARICA_FV_1000 | 67.62 -> 67.62 | carica 0.00, scarica 0.00 | piano -8.39 EUR fino a fine prezzi; vantaggio su AUTO 0.001 EUR |
| C2 | 21:00 | 21:30 | SCARICA_4000 | 67.62 -> 52.59 | carica 0.00, scarica 2.00 | piano -8.28 EUR fino a fine prezzi; vantaggio su AUTO 0.023 EUR |
| C3 | 20:00 | 21:45 | SCARICA_4000 | 60.11 -> 7.48 | carica 0.00, scarica 7.00 | piano -9.63 EUR fino a fine prezzi; vantaggio su AUTO 0.029 EUR |
| C2 | 21:30 | 00:00 | CARICA_FV_1000 | 52.59 -> 52.59 | carica 0.00, scarica 0.00 | piano -8.58 EUR fino a fine prezzi; vantaggio su AUTO 0.001 EUR |
