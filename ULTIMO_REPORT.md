# Report EMS Cismondi - 02/11/2026 (feriale)

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

Letture: 288, ore integrate: 24.00. FV 22.47 kWh, consumi casa 26.71 kWh.
Reale: prelievo 8.36 kWh, immissione 0.09 kWh.  Solo autoconsumo simulato: prelievo 8.24 kWh, immissione 0.00 kWh.
Condizione 0 (senza batteria): prelievo 18.06 kWh (4.02 EUR), immissione 13.82 kWh (4.06 EUR), netto -0.03 EUR.
Condizione 1 (reale): acquisti 1.86 EUR, cessioni 0.03 EUR, usura batteria (9.77 kWh scaricati) inclusa: netto 2.03 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 18.06 | 13.82 | 4.02 | 4.06 | 0.00 | 0 (0.00) | 9.82 (2.19) | 13.82 (4.06) | 2.06 | 2.07 | 2.05 | 0.00 | -0.00 | 1 |
| C2a | 27.19 | 23.21 | 6.06 | 7.15 | 0.20 | 1 (0.10) | 18.95 (4.22) | 23.21 (7.15) | 2.83 | 2.83 | 2.80 | 0.76 | 0.08 | 2 |
| C2b | 28.79 | 22.89 | 6.42 | 7.05 | 0.20 | 2 (0.20) | 20.55 (4.58) | 22.89 (7.05) | 2.27 | 2.27 | 2.24 | 0.21 | 0.27 | 3 |
| C2c | 28.53 | 22.64 | 6.36 | 6.98 | 0.20 | 2 (0.20) | 20.29 (4.52) | 22.64 (6.98) | 2.25 | 2.25 | 2.22 | 0.19 | 0.29 | 3 |
| C2d | 28.35 | 22.45 | 6.32 | 6.93 | 0.20 | 2 (0.20) | 20.11 (4.48) | 22.45 (6.93) | 2.24 | 2.24 | 2.21 | 0.18 | 0.30 | 3 |
| C2e | 28.35 | 22.45 | 6.32 | 6.93 | 0.20 | 2 (0.20) | 20.11 (4.48) | 22.45 (6.93) | 2.24 | 2.24 | 2.21 | 0.18 | 0.30 | 3 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 903.95 W, modello 843.36 W.  FV: sera prima 126.12 W, modello 119.44 W.
Rendimenti usati: carica 0.973, scarica 0.881. Ore con SOC reale >= 90 %: 2.50.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.273 s, massimo 2.019 s (qui). Calcolo del piano: massimo 1.394 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 46343.82 kB. Scritture nella memoria interna 1571.05 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 28, GitHub 26; dati ricevuti circa 1278.63 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2b | 00:00 | 04:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -3.58 EUR fino a fine prezzi; vantaggio su AUTO 0.160 EUR |
| C2c | 00:00 | 06:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -3.58 EUR fino a fine prezzi; vantaggio su AUTO 0.160 EUR |
| C2d | 00:00 | 07:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -3.58 EUR fino a fine prezzi; vantaggio su AUTO 0.160 EUR |
| C2e | 00:00 | 07:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -3.58 EUR fino a fine prezzi; vantaggio su AUTO 0.160 EUR |
| C2a | 00:00 | 14:30 | CARICA_RETE_1000 | 32.43 -> 95.00 | carica 9.65, scarica 0.00 | piano -5.98 EUR fino a fine prezzi; vantaggio su AUTO 0.138 EUR |
| C2b | 04:00 | 14:30 | CARICA_RETE_2000 | 20.00 -> 95.00 | carica 11.56, scarica 0.00 | piano -3.05 EUR fino a fine prezzi; vantaggio su AUTO 0.131 EUR |
| C2c | 06:00 | 14:30 | CARICA_RETE_3000 | 20.00 -> 95.00 | carica 11.56, scarica 0.00 | piano -2.13 EUR fino a fine prezzi; vantaggio su AUTO 0.131 EUR |
| C2d | 07:00 | 14:30 | CARICA_RETE_4000 | 20.00 -> 95.00 | carica 11.56, scarica 0.00 | piano -1.21 EUR fino a fine prezzi; vantaggio su AUTO 0.144 EUR |
| C2e | 07:00 | 14:30 | CARICA_RETE_4000 | 20.00 -> 95.00 | carica 11.56, scarica 0.00 | piano -1.21 EUR fino a fine prezzi; vantaggio su AUTO 0.130 EUR |
| C2 | 00:00 | 00:00 | SCARICA_5000 | 20.83 -> 20.83 | carica 0.00, scarica 0.00 | piano -3.92 EUR fino a fine prezzi; vantaggio su AUTO 0.130 EUR |
| C2a | 14:30 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.91 | piano -5.53 EUR fino a fine prezzi; vantaggio su AUTO 0.162 EUR |
| C2b | 14:30 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.91 | piano -5.53 EUR fino a fine prezzi; vantaggio su AUTO 0.162 EUR |
| C2c | 14:30 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.91 | piano -5.53 EUR fino a fine prezzi; vantaggio su AUTO 0.162 EUR |
| C2d | 14:30 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.91 | piano -5.53 EUR fino a fine prezzi; vantaggio su AUTO 0.162 EUR |
| C2e | 14:30 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.91 | piano -5.53 EUR fino a fine prezzi; vantaggio su AUTO 0.162 EUR |

## Segnalazioni
- Dispacciamento non noto (calcolato a 0): inserirlo in config.lua quando disponibile.
