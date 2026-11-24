# Report EMS Cismondi - 23/11/2026 (feriale)

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

Letture: 288, ore integrate: 24.00. FV 14.77 kWh, consumi casa 25.83 kWh.
Reale: prelievo 12.31 kWh, immissione 0.27 kWh.  Solo autoconsumo simulato: prelievo 12.44 kWh, immissione 0.00 kWh.
Condizione 0 (senza batteria): prelievo 21.32 kWh (5.15 EUR), immissione 10.26 kWh (2.29 EUR), netto 2.86 EUR.
Condizione 1 (reale): acquisti 2.97 EUR, cessioni 0.07 EUR, usura batteria (9.15 kWh scaricati) inclusa: netto 3.08 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 20.49 | 9.99 | 4.95 | 2.62 | 0.12 | 8 (0.01) | 8.05 (1.94) | 9.99 (2.62) | 0.63 | 0.73 | 1.89 | 0.41 | 0.21 | 9 |
| C3 | 19.75 | 8.02 | 4.77 | 1.99 | 0.09 | 8 (0.01) | 7.31 (1.77) | 8.02 (1.99) | 0.20 | 0.30 | 0.30 | -0.02 | 0.11 | 6 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 631.00 W, modello 631.00 W.  FV: sera prima 137.79 W, modello 137.79 W.
Rendimenti usati: carica 0.979, scarica 0.886. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.166 s, massimo 0.968 s (qui). Calcolo del piano: massimo 0.592 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 20161.12 kB. Scritture nella memoria interna 1463.99 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 27, GitHub 26; dati ricevuti circa 1269.43 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C3 | 09:45 | 10:00 | CARICA_FV_3000 | 5.34 -> 8.09 | carica 0.42, scarica 0.00 | piano -2.86 EUR fino a fine prezzi; vantaggio su AUTO 0.003 EUR |
| C3 | 10:00 | 10:45 | SCARICA_4000 | 8.09 -> 5.59 | carica 0.00, scarica 0.33 | piano -2.49 EUR fino a fine prezzi; vantaggio su AUTO 0.026 EUR |
| C2 | 00:00 | 11:30 | BATTERIA_FERMA | 54.03 -> 54.03 | carica 0.00, scarica 0.00 | piano -8.07 EUR fino a fine prezzi; vantaggio su AUTO 0.020 EUR |
| C3 | 10:45 | 12:30 | CARICA_FV_4000 | 5.59 -> 30.94 | carica 3.89, scarica 0.00 | piano -2.77 EUR fino a fine prezzi; vantaggio su AUTO 0.001 EUR |
| C3 | 12:30 | 13:00 | RITARDATA | 30.94 -> 31.59 | carica 0.10, scarica 0.00 | piano -2.15 EUR fino a fine prezzi; vantaggio su AUTO 0.005 EUR |
| C3 | 13:00 | 13:15 | CARICA_FV_4000 | 31.59 -> 35.21 | carica 0.56, scarica 0.00 | piano -2.22 EUR fino a fine prezzi; vantaggio su AUTO 0.001 EUR |
| C2 | 11:30 | 14:15 | CARICA_FV_2000 | 54.03 -> 89.45 | carica 5.43, scarica 0.00 | piano -1.32 EUR fino a fine prezzi; vantaggio su AUTO 0.001 EUR |
| C2 | 14:15 | 15:30 | BATTERIA_FERMA | 89.45 -> 89.45 | carica 0.00, scarica 0.00 | piano -9.58 EUR fino a fine prezzi; vantaggio su AUTO 0.009 EUR |
| C2 | 15:30 | 16:00 | SCARICA_4000 | 89.45 -> 74.41 | carica 0.00, scarica 2.00 | piano -9.41 EUR fino a fine prezzi; vantaggio su AUTO 0.003 EUR |
| C3 | 13:15 | 16:00 | BATTERIA_FERMA | 35.21 -> 35.21 | carica 0.00, scarica 0.00 | piano -2.03 EUR fino a fine prezzi; vantaggio su AUTO 0.012 EUR |
| C2 | 16:00 | 16:15 | CARICA_FV_1000 | 74.41 -> 74.42 | carica 0.00, scarica 0.00 | piano -9.96 EUR fino a fine prezzi; vantaggio su AUTO 0.008 EUR |
| C2 | 16:15 | 16:30 | SCARICA_4000 | 74.42 -> 66.90 | carica 0.00, scarica 1.00 | piano -9.82 EUR fino a fine prezzi; vantaggio su AUTO 0.016 EUR |
| C3 | 16:00 | 17:00 | SCARICA_4000 | 35.21 -> 5.14 | carica 0.00, scarica 4.00 | piano -11.35 EUR fino a fine prezzi; vantaggio su AUTO 0.157 EUR |
| C2 | 16:30 | 19:45 | CARICA_FV_1000 | 66.90 -> 66.90 | carica 0.00, scarica 0.00 | piano -10.61 EUR fino a fine prezzi; vantaggio su AUTO 0.017 EUR |
| C2 | 19:45 | 20:30 | SCARICA_4000 | 66.90 -> 44.35 | carica 0.00, scarica 3.00 | piano -8.73 EUR fino a fine prezzi; vantaggio su AUTO 0.016 EUR |
| C2 | 20:30 | 00:00 | CARICA_FV_1000 | 44.35 -> 44.35 | carica 0.00, scarica 0.00 | piano -9.13 EUR fino a fine prezzi; vantaggio su AUTO 0.011 EUR |
