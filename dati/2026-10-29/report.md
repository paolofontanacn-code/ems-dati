# Report EMS Cismondi - 29/10/2026 (feriale)

**SOLO SIMULAZIONE**: nessun comando inviato all'inverter.

## Scenari

Prezzo d'acquisto fisso F0: 0.12 EUR/kWh di energia, 0.2228 EUR/kWh con i costi aggiuntivi (perdite 10 % su energia e spread, dispacciamento NON NOTO (per ora 0), trasporto 0.0147, oneri di sistema 0.0332, accise 0.0227 EUR/kWh, IVA 10 %).

| Condizione | Descrizione |
|---|---|
| **0** | Impianto senza batteria: solo autoconsumo istantaneo del FV, il resto si compra, l'eccedenza si cede. |
| **1** | Impianto con batteria senza ottimizzazione (come oggi): dati REALI misurati da Huawei. |
| **2 (senza carica AC)** | Batteria con ottimizzazione di carica e scarica, senza carica AC dalla rete. |
| **2a (carica AC 1 kW)** | Batteria con ottimizzazione di carica e scarica, carica AC dalla rete fino a 1 kW a qualsiasi ora. |
| **2b (carica AC 2 kW)** | Batteria con ottimizzazione di carica e scarica, carica AC dalla rete fino a 2 kW a qualsiasi ora. |
| **2c (carica AC 3 kW)** | Batteria con ottimizzazione di carica e scarica, carica AC dalla rete fino a 3 kW a qualsiasi ora. |
| **2d (carica AC 4 kW)** | Batteria con ottimizzazione di carica e scarica, carica AC dalla rete fino a 4 kW a qualsiasi ora. |
| **2e (carica AC 5 kW)** | Batteria con ottimizzazione di carica e scarica, carica AC dalla rete fino a 5 kW a qualsiasi ora. |
| controllo | Automatico simulato: la condizione 1 rifatta dal simulatore, per misurarne la precisione. |

Cessioni (RID): prezzo zonale NORD del quarto d'ora. Usura batteria: 0.020 EUR per kWh scaricato. Ogni scenario ha la sua batteria simulata e l'ottimizzatore sceglie ogni 15 minuti tra autoconsumo, carica ritardata, carica forzata e scarica forzata a potenze graduate, con al massimo 14 periodi forzati e 1 ciclo di scarica forzata al giorno. Ogni cambiamento di funzionamento costa 0.10 EUR: si cambia solo se conviene anche pagandolo.

> Il dispacciamento non e' ancora noto ed e' calcolato a 0: i costi d'acquisto sono sottostimati della stessa quantita' per kWh. I kWh sono registrati nel dataset, quindi i costi si possono ricalcolare quando il valore sara' noto.

Letture: 288, ore integrate: 24.00. FV 22.88 kWh, consumi casa 24.06 kWh.
Reale: prelievo 1.05 kWh, immissione 2.01 kWh.  Solo autoconsumo simulato: prelievo 0.02 kWh, immissione 1.96 kWh.
Condizione 0 (senza batteria): prelievo 16.53 kWh (3.68 EUR), immissione 15.35 kWh (3.74 EUR), netto -0.05 EUR.
Condizione 1 (reale): acquisti 0.23 EUR, cessioni 0.55 EUR, usura batteria (15.71 kWh scaricati) inclusa: netto -0.00 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 15.51 | 12.69 | 3.46 | 4.21 | 0.17 | 2 (0.20) | 15.49 (3.45) | 10.72 (3.69) | 0.37 | 0.19 | 0.59 | 0.32 | 0.26 | 3 |
| C2a | 18.31 | 15.42 | 4.08 | 5.03 | 0.20 | 2 (0.20) | 18.29 (4.08) | 13.46 (4.51) | 0.55 | 0.37 | 0.74 | 0.50 | 0.10 | 3 |
| C2b | 19.85 | 16.96 | 4.42 | 5.39 | 0.20 | 2 (0.20) | 19.83 (4.42) | 15.00 (4.87) | 0.57 | 0.39 | 0.76 | 0.52 | 0.08 | 3 |
| C2c | 20.04 | 17.15 | 4.47 | 5.44 | 0.20 | 2 (0.20) | 20.02 (4.46) | 15.19 (4.92) | 0.57 | 0.39 | 0.76 | 0.52 | 0.08 | 3 |
| C2d | 20.04 | 17.15 | 4.47 | 5.44 | 0.20 | 2 (0.20) | 20.02 (4.46) | 15.19 (4.92) | 0.57 | 0.39 | 0.76 | 0.52 | 0.08 | 3 |
| C2e | 20.04 | 17.15 | 4.47 | 5.44 | 0.20 | 2 (0.20) | 20.02 (4.46) | 15.19 (4.92) | 0.57 | 0.39 | 0.76 | 0.52 | 0.08 | 3 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 582.94 W, modello 551.06 W.  FV: sera prima 136.04 W, modello 138.71 W.
Rendimenti usati: carica 0.973, scarica 0.877. Ore con SOC reale >= 90 %: 3.33.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.521 s, massimo 7.406 s (qui). Calcolo del piano: massimo 5.621 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 45040.68 kB. Scritture nella memoria interna 1508.97 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 27, GitHub 26; dati ricevuti circa 1269.69 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2 | 00:00 | 11:15 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -4.41 EUR fino a fine prezzi; vantaggio su AUTO 0.026 EUR |
| C2a | 00:00 | 11:15 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -2.66 EUR fino a fine prezzi; vantaggio su AUTO 0.134 EUR |
| C2b | 00:00 | 12:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -2.63 EUR fino a fine prezzi; vantaggio su AUTO 0.134 EUR |
| C2c | 00:00 | 12:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -2.62 EUR fino a fine prezzi; vantaggio su AUTO 0.134 EUR |
| C2d | 00:00 | 12:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -2.62 EUR fino a fine prezzi; vantaggio su AUTO 0.134 EUR |
| C2e | 00:00 | 12:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -2.62 EUR fino a fine prezzi; vantaggio su AUTO 0.134 EUR |
| C2 | 11:15 | 16:15 | CARICA_FV | 20.00 -> 87.33 | carica 10.39, scarica 0.00 | piano -1.14 EUR fino a fine prezzi; vantaggio su AUTO 0.072 EUR |
| C2a | 11:15 | 16:15 | CARICA_RETE_1000 | 20.00 -> 95.00 | carica 11.57, scarica 0.00 | piano -0.98 EUR fino a fine prezzi; vantaggio su AUTO 0.102 EUR |
| C2b | 12:00 | 16:15 | CARICA_RETE_2000 | 20.00 -> 95.00 | carica 11.57, scarica 0.00 | piano -0.79 EUR fino a fine prezzi; vantaggio su AUTO 0.091 EUR |
| C2c | 12:00 | 16:15 | CARICA_RETE_3000 | 20.00 -> 95.00 | carica 11.57, scarica 0.00 | piano -0.76 EUR fino a fine prezzi; vantaggio su AUTO 0.108 EUR |
| C2d | 12:00 | 16:15 | CARICA_RETE_4000 | 20.00 -> 95.00 | carica 11.57, scarica 0.00 | piano -0.76 EUR fino a fine prezzi; vantaggio su AUTO 0.098 EUR |
| C2e | 12:00 | 16:15 | CARICA_RETE_4000 | 20.00 -> 95.00 | carica 11.57, scarica 0.00 | piano -0.76 EUR fino a fine prezzi; vantaggio su AUTO 0.098 EUR |
| C2 | 16:15 | 00:00 | SCARICA_5000 | 87.33 -> 20.83 | carica 0.00, scarica 8.75 | piano -3.92 EUR fino a fine prezzi; vantaggio su AUTO 0.130 EUR |
| C2a | 16:15 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.87 | piano -3.58 EUR fino a fine prezzi; vantaggio su AUTO 0.160 EUR |
| C2b | 16:15 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.87 | piano -3.58 EUR fino a fine prezzi; vantaggio su AUTO 0.160 EUR |
| C2c | 16:15 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.87 | piano -3.58 EUR fino a fine prezzi; vantaggio su AUTO 0.160 EUR |
| C2d | 16:15 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.87 | piano -3.58 EUR fino a fine prezzi; vantaggio su AUTO 0.160 EUR |
| C2e | 16:15 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.87 | piano -3.58 EUR fino a fine prezzi; vantaggio su AUTO 0.160 EUR |

## Segnalazioni
- Dispacciamento non noto (calcolato a 0): inserirlo in config.lua quando disponibile.
