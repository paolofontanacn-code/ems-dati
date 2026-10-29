# Report EMS Cismondi - 28/10/2026 (feriale)

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

Letture: 288, ore integrate: 24.00. FV 22.42 kWh, consumi casa 19.18 kWh.
Reale: prelievo 2.53 kWh, immissione 1.76 kWh.  Solo autoconsumo simulato: prelievo 2.60 kWh, immissione 1.49 kWh.
Condizione 0 (senza batteria): prelievo 12.36 kWh (2.76 EUR), immissione 15.61 kWh (4.04 EUR), netto -1.29 EUR.
Condizione 1 (reale): acquisti 0.56 EUR, cessioni 0.51 EUR, usura batteria (10.00 kWh scaricati) inclusa: netto 0.26 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 12.36 | 15.61 | 2.76 | 4.04 | 0.00 | 0 (0.00) | 9.76 (2.18) | 14.12 (3.61) | 1.55 | 1.63 | 0.97 | 0.00 | 0.16 | 1 |
| C2a | 20.35 | 23.61 | 4.54 | 6.84 | 0.20 | 1 (0.10) | 17.75 (3.96) | 22.12 (6.40) | 2.26 | 2.35 | 1.69 | 0.72 | 0.11 | 2 |
| C2b | 21.76 | 23.36 | 4.85 | 6.76 | 0.20 | 2 (0.20) | 19.16 (4.27) | 21.86 (6.33) | 1.77 | 1.85 | 1.20 | 0.22 | 0.29 | 3 |
| C2c | 21.47 | 23.07 | 4.78 | 6.67 | 0.20 | 2 (0.20) | 18.87 (4.20) | 21.57 (6.24) | 1.75 | 1.83 | 1.18 | 0.20 | 0.31 | 3 |
| C2d | 20.35 | 23.61 | 4.54 | 6.84 | 0.20 | 1 (0.10) | 17.75 (3.96) | 22.12 (6.40) | 2.26 | 2.35 | 1.69 | 0.72 | 0.17 | 2 |
| C2e | 20.35 | 23.61 | 4.54 | 6.84 | 0.20 | 1 (0.10) | 17.75 (3.96) | 22.12 (6.40) | 2.26 | 2.35 | 1.69 | 0.72 | 0.17 | 2 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 630.46 W, modello 625.25 W.  FV: sera prima 154.24 W, modello 130.36 W.
Rendimenti usati: carica 0.972, scarica 0.883. Ore con SOC reale >= 90 %: 3.50.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 1.031 s, massimo 9.249 s (qui). Calcolo del piano: massimo 9.234 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 43493.20 kB. Scritture nella memoria interna 1513.75 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 29, GitHub 26; dati ricevuti circa 1288.24 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2b | 00:00 | 04:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -4.41 EUR fino a fine prezzi; vantaggio su AUTO 0.026 EUR |
| C2c | 00:00 | 06:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -4.41 EUR fino a fine prezzi; vantaggio su AUTO 0.026 EUR |
| C2a | 00:00 | 17:15 | CARICA_RETE_1000 | 30.79 -> 95.00 | carica 9.92, scarica 0.00 | piano -3.56 EUR fino a fine prezzi; vantaggio su AUTO 0.117 EUR |
| C2b | 04:00 | 17:15 | CARICA_RETE_2000 | 20.00 -> 95.00 | carica 11.59, scarica 0.00 | piano -2.18 EUR fino a fine prezzi; vantaggio su AUTO 0.132 EUR |
| C2c | 06:00 | 17:15 | CARICA_RETE_3000 | 20.00 -> 95.00 | carica 11.59, scarica 0.00 | piano -1.21 EUR fino a fine prezzi; vantaggio su AUTO 0.130 EUR |
| C2d | 00:00 | 17:15 | CARICA_RETE_1000 | 30.79 -> 95.00 | carica 9.92, scarica 0.00 | piano -3.56 EUR fino a fine prezzi; vantaggio su AUTO 0.117 EUR (stesso piano di C2a) |
| C2e | 00:00 | 17:15 | CARICA_RETE_1000 | 30.79 -> 95.00 | carica 9.92, scarica 0.00 | piano -3.56 EUR fino a fine prezzi; vantaggio su AUTO 0.117 EUR (stesso piano di C2a) |
| C2 | 00:00 | 00:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -4.41 EUR fino a fine prezzi; vantaggio su AUTO 0.026 EUR |
| C2a | 17:15 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.94 | piano -2.66 EUR fino a fine prezzi; vantaggio su AUTO 0.134 EUR |
| C2b | 17:15 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.94 | piano -2.63 EUR fino a fine prezzi; vantaggio su AUTO 0.134 EUR |
| C2c | 17:15 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.94 | piano -2.62 EUR fino a fine prezzi; vantaggio su AUTO 0.134 EUR |
| C2d | 17:15 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.94 | piano -2.62 EUR fino a fine prezzi; vantaggio su AUTO 0.134 EUR |
| C2e | 17:15 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.94 | piano -2.62 EUR fino a fine prezzi; vantaggio su AUTO 0.134 EUR |

## Segnalazioni
- Dispacciamento non noto (calcolato a 0): inserirlo in config.lua quando disponibile.
