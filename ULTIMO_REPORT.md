# Report EMS Cismondi - 23/10/2026 (feriale)

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

Letture: 288, ore integrate: 24.00. FV 16.31 kWh, consumi casa 24.06 kWh.
Reale: prelievo 5.21 kWh, immissione 0.19 kWh.  Solo autoconsumo simulato: prelievo 5.05 kWh, immissione 0.01 kWh.
Condizione 0 (senza batteria): prelievo 17.99 kWh (4.01 EUR), immissione 10.24 kWh (2.33 EUR), netto 1.68 EUR.
Condizione 1 (reale): acquisti 1.16 EUR, cessioni 0.04 EUR, usura batteria (11.46 kWh scaricati) inclusa: netto 1.34 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 13.56 | 10.05 | 3.02 | 2.28 | 0.06 | 1 (0.10) | 8.51 (1.90) | 10.04 (2.28) | 0.44 | 0.45 | 0.41 | 0.78 | -0.22 | 1 |
| C2a | 13.56 | 10.05 | 3.02 | 2.28 | 0.06 | 1 (0.10) | 8.51 (1.90) | 10.04 (2.28) | 0.44 | 0.45 | 0.41 | 0.78 | -0.22 | 1 |
| C2b | 13.56 | 10.05 | 3.02 | 2.28 | 0.06 | 1 (0.10) | 8.51 (1.90) | 10.04 (2.28) | 0.44 | 0.45 | 0.41 | 0.78 | -0.22 | 1 |
| C2c | 13.56 | 10.05 | 3.02 | 2.28 | 0.06 | 1 (0.10) | 8.51 (1.90) | 10.04 (2.28) | 0.44 | 0.45 | 0.41 | 0.78 | -0.22 | 1 |
| C2d | 13.56 | 10.05 | 3.02 | 2.28 | 0.06 | 1 (0.10) | 8.51 (1.90) | 10.04 (2.28) | 0.44 | 0.45 | 0.41 | 0.78 | -0.22 | 1 |
| C2e | 13.56 | 10.05 | 3.02 | 2.28 | 0.06 | 1 (0.10) | 8.51 (1.90) | 10.04 (2.28) | 0.44 | 0.45 | 0.41 | 0.78 | -0.22 | 1 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 519.63 W, modello 581.85 W.  FV: sera prima 289.08 W, modello 281.09 W.
Rendimenti usati: carica 0.977, scarica 0.879. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.307 s, massimo 1.509 s (qui). Calcolo del piano: massimo 1.403 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 45052.67 kB. Scritture nella memoria interna 1762.46 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 6, meteo 28, GitHub 26; dati ricevuti circa 1301.55 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2 | 10:00 | 00:00 | SCARICA_1000 | 7.17 -> 7.17 | carica 0.00, scarica 0.00 | piano -2.34 EUR fino a fine prezzi; vantaggio su AUTO 0.000 EUR |
| C2a | 10:00 | 00:00 | SCARICA_1000 | 7.17 -> 7.17 | carica 0.00, scarica 0.00 | piano -2.34 EUR fino a fine prezzi; vantaggio su AUTO 0.000 EUR |
| C2b | 10:00 | 00:00 | SCARICA_1000 | 7.17 -> 7.17 | carica 0.00, scarica 0.00 | piano -2.34 EUR fino a fine prezzi; vantaggio su AUTO 0.000 EUR |
| C2c | 10:00 | 00:00 | SCARICA_1000 | 7.17 -> 7.17 | carica 0.00, scarica 0.00 | piano -2.34 EUR fino a fine prezzi; vantaggio su AUTO 0.000 EUR |
| C2d | 10:00 | 00:00 | SCARICA_1000 | 7.17 -> 7.17 | carica 0.00, scarica 0.00 | piano -2.34 EUR fino a fine prezzi; vantaggio su AUTO 0.000 EUR |
| C2e | 10:00 | 00:00 | SCARICA_1000 | 7.17 -> 7.17 | carica 0.00, scarica 0.00 | piano -2.34 EUR fino a fine prezzi; vantaggio su AUTO 0.000 EUR |

## Segnalazioni
- Dispacciamento non noto (calcolato a 0): inserirlo in config.lua quando disponibile.
