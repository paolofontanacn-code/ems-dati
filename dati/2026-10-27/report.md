# Report EMS Cismondi - 27/10/2026 (feriale)

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

Letture: 288, ore integrate: 24.00. FV 24.42 kWh, consumi casa 24.41 kWh.
Reale: prelievo 5.05 kWh, immissione 4.73 kWh.  Solo autoconsumo simulato: prelievo 4.58 kWh, immissione 4.29 kWh.
Condizione 0 (senza batteria): prelievo 18.06 kWh (4.03 EUR), immissione 18.07 kWh (4.01 EUR), netto 0.02 EUR.
Condizione 1 (reale): acquisti 1.13 EUR, cessioni 1.10 EUR, usura batteria (13.20 kWh scaricati) inclusa: netto 0.29 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 18.06 | 18.07 | 4.03 | 4.01 | 0.00 | 0 (0.00) | 13.48 (3.00) | 13.78 (3.00) | 0.27 | 0.27 | 0.09 | 0.00 | 0.23 | 1 |
| C2a | 19.73 | 18.07 | 4.40 | 4.01 | 0.00 | 1 (0.10) | 15.15 (3.38) | 13.78 (3.00) | -0.20 | -0.20 | -0.10 | -0.47 | 0.42 | 2 |
| C2b | 18.06 | 18.07 | 4.03 | 4.01 | 0.00 | 0 (0.00) | 13.48 (3.00) | 13.78 (3.00) | 0.27 | 0.27 | 0.09 | 0.00 | 0.23 | 1 |
| C2c | 18.06 | 18.07 | 4.03 | 4.01 | 0.00 | 0 (0.00) | 13.48 (3.00) | 13.78 (3.00) | 0.27 | 0.27 | 0.09 | 0.00 | 0.23 | 1 |
| C2d | 19.73 | 18.07 | 4.40 | 4.01 | 0.00 | 1 (0.10) | 15.15 (3.38) | 13.78 (3.00) | -0.20 | -0.20 | -0.10 | -0.47 | 0.42 | 2 |
| C2e | 19.73 | 18.07 | 4.40 | 4.01 | 0.00 | 1 (0.10) | 15.15 (3.38) | 13.78 (3.00) | -0.20 | -0.20 | -0.10 | -0.47 | 0.42 | 2 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 581.79 W, modello 582.68 W.  FV: sera prima 194.24 W, modello 222.17 W.
Rendimenti usati: carica 0.971, scarica 0.883. Ore con SOC reale >= 90 %: 3.33.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.290 s, massimo 1.391 s (qui). Calcolo del piano: massimo 1.291 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 46662.39 kB. Scritture nella memoria interna 1450.82 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 28, GitHub 26; dati ricevuti circa 1282.14 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2a | 00:00 | 22:15 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -4.41 EUR fino a fine prezzi; vantaggio su AUTO 0.026 EUR |
| C2d | 00:00 | 22:15 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -4.41 EUR fino a fine prezzi; vantaggio su AUTO 0.026 EUR |
| C2e | 00:00 | 22:15 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -4.41 EUR fino a fine prezzi; vantaggio su AUTO 0.026 EUR |
| C2 | 00:00 | 00:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -4.41 EUR fino a fine prezzi; vantaggio su AUTO 0.026 EUR |
| C2a | 22:15 | 00:00 | CARICA_RETE_1000 | 20.00 -> 30.79 | carica 1.67, scarica 0.00 | piano -3.56 EUR fino a fine prezzi; vantaggio su AUTO 0.117 EUR |
| C2b | 00:00 | 00:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -4.41 EUR fino a fine prezzi; vantaggio su AUTO 0.026 EUR |
| C2c | 00:00 | 00:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -4.41 EUR fino a fine prezzi; vantaggio su AUTO 0.026 EUR |
| C2d | 22:15 | 00:00 | CARICA_RETE_1000 | 20.00 -> 30.79 | carica 1.67, scarica 0.00 | piano -3.56 EUR fino a fine prezzi; vantaggio su AUTO 0.117 EUR (stesso piano di C2a) |
| C2e | 22:15 | 00:00 | CARICA_RETE_1000 | 20.00 -> 30.79 | carica 1.67, scarica 0.00 | piano -3.56 EUR fino a fine prezzi; vantaggio su AUTO 0.117 EUR (stesso piano di C2a) |

## Segnalazioni
- Dispacciamento non noto (calcolato a 0): inserirlo in config.lua quando disponibile.
