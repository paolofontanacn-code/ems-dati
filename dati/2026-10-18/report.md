# Report EMS Cismondi - 18/10/2026 (domenica)

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

Letture: 288, ore integrate: 24.00. FV 13.69 kWh, consumi casa 20.89 kWh.
Reale: prelievo 1.42 kWh, immissione 0.22 kWh.  Solo autoconsumo simulato: prelievo 0.51 kWh, immissione 0.00 kWh.
Senza batteria: prelievo 6.55 kWh (1.46 EUR), immissione 0.02 kWh (0.00 EUR).

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio su automatico EUR | Beneficio con SOC EUR | Beneficio su senza batteria EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F0 | 6.46 | 0.00 | 1.44 | 0.00 | 0.00 | 1 (0.10) | 5.95 (1.33) | 0.00 (0.00) | -1.31 | -0.18 | -0.09 | -0.11 | 1 |
| F0R | 6.46 | 0.00 | 1.44 | 0.00 | 0.00 | 1 (0.10) | 5.95 (1.33) | 0.00 (0.00) | -1.31 | -0.18 | -0.09 | -0.11 | 1 |

Beneficio = costo netto dello scenario solo autoconsumo - costo netto del profilo (stessi prezzi) - costo dei cambiamenti. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 540.99 W, modello 534.81 W.  FV: sera prima 200.53 W, modello 263.82 W.
Rendimenti usati: carica 0.980, scarica 0.870. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.142 s, massimo 0.775 s (qui). Calcolo del piano: massimo 0.674 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 16178.32 kB. Scritture nella memoria interna 1741.96 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 9, meteo 28, GitHub 22; dati ricevuti circa 1326.40 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| F0 | 16:30 | 00:00 | CARICA_FV | 48.47 -> 48.47 | carica 0.00, scarica 0.00 | piano -2.92 EUR fino a fine prezzi; vantaggio su AUTO 0.002 EUR |
| F0R | 16:30 | 00:00 | CARICA_FV | 48.47 -> 48.47 | carica 0.00, scarica 0.00 | piano -2.92 EUR fino a fine prezzi; vantaggio su AUTO 0.002 EUR |

## Segnalazioni
- Dispacciamento non noto (calcolato a 0): inserirlo in config.lua quando disponibile.
