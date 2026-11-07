# Report EMS Cismondi - 06/11/2026 (feriale)

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

Letture: 288, ore integrate: 24.00. FV 10.22 kWh, consumi casa 29.40 kWh.
Reale: prelievo 19.30 kWh, immissione 0.06 kWh.  Solo autoconsumo simulato: prelievo 19.48 kWh, immissione 0.00 kWh.
Condizione 0 (senza batteria): prelievo 21.23 kWh (4.73 EUR), immissione 2.05 kWh (0.51 EUR), netto 4.22 EUR.
Condizione 1 (reale): acquisti 4.30 EUR, cessioni 0.02 EUR, usura batteria (2.07 kWh scaricati) inclusa: netto 4.33 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 21.23 | 2.05 | 4.73 | 0.51 | 0.00 | 0 (0.00) | 1.75 (0.39) | 2.05 (0.51) | 0.10 | 0.15 | 0.55 | 0.00 | -0.01 | 1 |
| C2a | 21.23 | 2.05 | 4.73 | 0.51 | 0.00 | 0 (0.00) | 1.75 (0.39) | 2.05 (0.51) | 0.10 | 0.15 | 0.53 | 0.00 | 0.71 | 1 |
| C2b | 21.23 | 2.05 | 4.73 | 0.51 | 0.00 | 0 (0.00) | 1.75 (0.39) | 2.05 (0.51) | 0.10 | 0.15 | 0.53 | 0.00 | 0.71 | 1 |
| C2c | 30.79 | 9.99 | 6.86 | 3.39 | 0.20 | 2 (0.20) | 11.32 (2.52) | 9.99 (3.39) | 0.46 | 0.50 | 0.88 | 0.35 | 0.36 | 3 |
| C2d | 31.18 | 10.38 | 6.95 | 3.48 | 0.20 | 2 (0.20) | 11.71 (2.61) | 10.38 (3.48) | 0.46 | 0.51 | 0.88 | 0.36 | 0.35 | 3 |
| C2e | 31.18 | 10.38 | 6.95 | 3.48 | 0.20 | 2 (0.20) | 11.71 (2.61) | 10.38 (3.48) | 0.46 | 0.51 | 0.88 | 0.36 | 0.35 | 3 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 664.87 W, modello 671.42 W.  FV: sera prima 240.85 W, modello 134.99 W.
Rendimenti usati: carica 0.975, scarica 0.881. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.256 s, massimo 1.784 s (qui). Calcolo del piano: massimo 1.404 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 47155.51 kB. Scritture nella memoria interna 1571.75 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 28, GitHub 26; dati ricevuti circa 1277.27 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2c | 00:00 | 12:30 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -5.53 EUR fino a fine prezzi; vantaggio su AUTO 0.162 EUR |
| C2d | 00:00 | 13:30 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -5.53 EUR fino a fine prezzi; vantaggio su AUTO 0.162 EUR |
| C2e | 00:00 | 13:30 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -5.53 EUR fino a fine prezzi; vantaggio su AUTO 0.162 EUR |
| C2c | 12:30 | 16:30 | CARICA_RETE_3000 | 20.00 -> 95.00 | carica 11.54, scarica 0.00 | piano -3.84 EUR fino a fine prezzi; vantaggio su AUTO 0.112 EUR |
| C2d | 13:30 | 16:30 | CARICA_RETE_4000 | 20.00 -> 95.00 | carica 11.54, scarica 0.00 | piano -11.64 EUR fino a fine prezzi; vantaggio su AUTO 0.103 EUR |
| C2e | 13:30 | 16:30 | CARICA_RETE_4000 | 20.00 -> 95.00 | carica 11.54, scarica 0.00 | piano -11.64 EUR fino a fine prezzi; vantaggio su AUTO 0.104 EUR |
| C2 | 00:00 | 00:00 | SCARICA_5000 | 20.83 -> 20.83 | carica 0.00, scarica 0.00 | piano -3.92 EUR fino a fine prezzi; vantaggio su AUTO 0.130 EUR |
| C2a | 00:00 | 00:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -5.53 EUR fino a fine prezzi; vantaggio su AUTO 0.162 EUR |
| C2b | 00:00 | 00:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -5.53 EUR fino a fine prezzi; vantaggio su AUTO 0.162 EUR |
| C2c | 16:30 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.91 | piano -8.48 EUR fino a fine prezzi; vantaggio su AUTO 0.156 EUR |
| C2d | 16:30 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.91 | piano -8.48 EUR fino a fine prezzi; vantaggio su AUTO 0.156 EUR |
| C2e | 16:30 | 00:00 | SCARICA_5000 | 95.00 -> 20.00 | carica 0.00, scarica 9.91 | piano -8.48 EUR fino a fine prezzi; vantaggio su AUTO 0.156 EUR |

## Segnalazioni
- Dispacciamento non noto (calcolato a 0): inserirlo in config.lua quando disponibile.
