# Report EMS Cismondi - 26/10/2026 (feriale)

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

Letture: 288, ore integrate: 24.00. FV 22.28 kWh, consumi casa 22.50 kWh.
Reale: prelievo 9.02 kWh, immissione 2.35 kWh.  Solo autoconsumo simulato: prelievo 8.90 kWh, immissione 2.25 kWh.
Condizione 0 (senza batteria): prelievo 16.26 kWh (3.62 EUR), immissione 16.04 kWh (3.61 EUR), netto 0.02 EUR.
Condizione 1 (reale): acquisti 2.01 EUR, cessioni 0.58 EUR, usura batteria (7.29 kWh scaricati) inclusa: netto 1.58 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 14.82 | 10.94 | 3.30 | 3.21 | 0.20 | 2 (0.20) | 5.91 (1.32) | 8.69 (2.66) | 1.09 | 1.09 | 0.56 | -0.48 | 0.20 | 2 |
| C2a | 14.82 | 10.94 | 3.30 | 3.21 | 0.20 | 2 (0.20) | 5.91 (1.32) | 8.69 (2.66) | 1.09 | 1.09 | 0.56 | -0.48 | 0.20 | 2 |
| C2b | 14.82 | 10.94 | 3.30 | 3.21 | 0.20 | 2 (0.20) | 5.91 (1.32) | 8.69 (2.66) | 1.09 | 1.09 | 0.56 | -0.48 | 0.20 | 2 |
| C2c | 14.82 | 10.94 | 3.30 | 3.21 | 0.20 | 2 (0.20) | 5.91 (1.32) | 8.69 (2.66) | 1.09 | 1.09 | 0.56 | -0.48 | 0.20 | 2 |
| C2d | 14.82 | 10.94 | 3.30 | 3.21 | 0.20 | 2 (0.20) | 5.91 (1.32) | 8.69 (2.66) | 1.09 | 1.09 | 0.56 | -0.48 | 0.20 | 2 |
| C2e | 14.82 | 10.94 | 3.30 | 3.21 | 0.20 | 2 (0.20) | 5.91 (1.32) | 8.69 (2.66) | 1.09 | 1.09 | 0.56 | -0.48 | 0.20 | 2 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 540.37 W, modello 501.32 W.  FV: sera prima 330.15 W, modello 273.83 W.
Rendimenti usati: carica 0.969, scarica 0.885. Ore con SOC reale >= 90 %: 2.83.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.305 s, massimo 1.999 s (qui). Calcolo del piano: massimo 1.395 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 48569.64 kB. Scritture nella memoria interna 1486.91 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 28, GitHub 26; dati ricevuti circa 1278.67 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2 | 00:00 | 08:30 | SCARICA_1000 | 7.17 -> 7.17 | carica 0.00, scarica 0.00 | piano -2.34 EUR fino a fine prezzi; vantaggio su AUTO 0.000 EUR |
| C2a | 00:00 | 08:30 | SCARICA_1000 | 7.17 -> 7.17 | carica 0.00, scarica 0.00 | piano -2.34 EUR fino a fine prezzi; vantaggio su AUTO 0.000 EUR |
| C2b | 00:00 | 08:30 | SCARICA_1000 | 7.17 -> 7.17 | carica 0.00, scarica 0.00 | piano -2.34 EUR fino a fine prezzi; vantaggio su AUTO 0.000 EUR |
| C2c | 00:00 | 08:30 | SCARICA_1000 | 7.17 -> 7.17 | carica 0.00, scarica 0.00 | piano -2.34 EUR fino a fine prezzi; vantaggio su AUTO 0.000 EUR |
| C2d | 00:00 | 08:30 | SCARICA_1000 | 7.17 -> 7.17 | carica 0.00, scarica 0.00 | piano -2.34 EUR fino a fine prezzi; vantaggio su AUTO 0.000 EUR |
| C2e | 00:00 | 08:30 | SCARICA_1000 | 7.17 -> 7.17 | carica 0.00, scarica 0.00 | piano -2.34 EUR fino a fine prezzi; vantaggio su AUTO 0.000 EUR |
| C2 | 15:30 | 00:00 | SCARICA_5000 | 93.93 -> 20.00 | carica 0.00, scarica 9.81 | piano -4.41 EUR fino a fine prezzi; vantaggio su AUTO 0.026 EUR |
| C2a | 15:30 | 00:00 | SCARICA_5000 | 93.93 -> 20.00 | carica 0.00, scarica 9.81 | piano -4.41 EUR fino a fine prezzi; vantaggio su AUTO 0.026 EUR |
| C2b | 15:30 | 00:00 | SCARICA_5000 | 93.93 -> 20.00 | carica 0.00, scarica 9.81 | piano -4.41 EUR fino a fine prezzi; vantaggio su AUTO 0.026 EUR |
| C2c | 15:30 | 00:00 | SCARICA_5000 | 93.93 -> 20.00 | carica 0.00, scarica 9.81 | piano -4.41 EUR fino a fine prezzi; vantaggio su AUTO 0.026 EUR |
| C2d | 15:30 | 00:00 | SCARICA_5000 | 93.93 -> 20.00 | carica 0.00, scarica 9.81 | piano -4.41 EUR fino a fine prezzi; vantaggio su AUTO 0.026 EUR |
| C2e | 15:30 | 00:00 | SCARICA_5000 | 93.93 -> 20.00 | carica 0.00, scarica 9.81 | piano -4.41 EUR fino a fine prezzi; vantaggio su AUTO 0.026 EUR |

## Segnalazioni
- Dispacciamento non noto (calcolato a 0): inserirlo in config.lua quando disponibile.
