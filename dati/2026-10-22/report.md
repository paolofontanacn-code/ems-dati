# Report EMS Cismondi - 22/10/2026 (feriale)

**SOLO SIMULAZIONE**: nessun comando inviato all'inverter.

## Scenari

Prezzo d'acquisto fisso F0: 0.12 EUR/kWh di energia, 0.2228 EUR/kWh con i costi aggiuntivi (perdite 10 % su energia e spread, dispacciamento NON NOTO (per ora 0), trasporto 0.0147, oneri di sistema 0.0332, accise 0.0227 EUR/kWh, IVA 10 %).

| Scenario | Descrizione |
|---|---|
| **Senza batteria** | Solo autoconsumo istantaneo del FV: il resto si compra, l'eccedenza si cede. |
| **Automatico** | Batteria in massimo autoconsumo, senza ottimizzatore (come oggi). |
| **F0** - senza carica da rete | Batteria gestita dall'ottimizzatore, senza carica dalla rete. |
| **F0R** - con carica da rete | Batteria gestita dall'ottimizzatore, con carica dalla rete fino a 1000 W di giorno. |

Cessioni (RID): prezzo zonale NORD del quarto d'ora. Usura batteria: 0.020 EUR per kWh scaricato. Ogni scenario ha la sua batteria simulata e l'ottimizzatore sceglie ogni 15 minuti tra autoconsumo, carica ritardata, carica forzata e scarica forzata a potenze graduate, con al massimo 14 periodi forzati e 1 ciclo di scarica forzata al giorno. Ogni cambiamento di funzionamento costa 0.10 EUR: si cambia solo se conviene anche pagandolo.

> Il dispacciamento non e' ancora noto ed e' calcolato a 0: i costi d'acquisto sono sottostimati della stessa quantita' per kWh. I kWh sono registrati nel dataset, quindi i costi si possono ricalcolare quando il valore sara' noto.

Letture: 288, ore integrate: 24.00. FV 27.45 kWh, consumi casa 24.46 kWh.
Reale: prelievo 6.32 kWh, immissione 7.50 kWh.  Solo autoconsumo simulato: prelievo 5.14 kWh, immissione 6.81 kWh.
Senza batteria: prelievo 17.63 kWh (3.93 EUR), immissione 20.63 kWh (4.38 EUR).

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio su automatico EUR | Beneficio con SOC EUR | Beneficio su senza batteria EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F0 | 17.63 | 20.63 | 3.93 | 4.38 | 0.00 | 0 (0.00) | 12.49 (2.78) | 13.82 (2.95) | 0.42 | -0.11 | 0.00 | 0.23 | 1 |
| F0R | 17.63 | 20.63 | 3.93 | 4.38 | 0.00 | 0 (0.00) | 12.49 (2.78) | 13.82 (2.95) | 0.42 | -0.11 | 0.00 | 0.23 | 1 |

Beneficio = costo netto dello scenario solo autoconsumo - costo netto del profilo (stessi prezzi) - costo dei cambiamenti. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 569.05 W, modello 560.34 W.  FV: sera prima 257.34 W, modello 168.90 W.
Rendimenti usati: carica 0.974, scarica 0.878. Ore con SOC reale >= 90 %: 4.67.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.118 s, massimo 0.732 s (qui). Calcolo del piano: massimo 0.510 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 11495.68 kB. Scritture nella memoria interna 1136.22 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 29, GitHub 28; dati ricevuti circa 1292.32 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| F0 | 00:00 | 00:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -4.93 EUR fino a fine prezzi; vantaggio su AUTO 0.158 EUR |
| F0R | 00:00 | 00:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -4.93 EUR fino a fine prezzi; vantaggio su AUTO 0.158 EUR |

## Segnalazioni
- Dispacciamento non noto (calcolato a 0): inserirlo in config.lua quando disponibile.
