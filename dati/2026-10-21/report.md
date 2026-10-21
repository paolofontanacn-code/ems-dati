# Report EMS Cismondi - 21/10/2026 (feriale)

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

Letture: 288, ore integrate: 24.00. FV 20.44 kWh, consumi casa 20.28 kWh.
Reale: prelievo 6.82 kWh, immissione 0.31 kWh.  Solo autoconsumo simulato: prelievo 6.72 kWh, immissione 0.00 kWh.
Senza batteria: prelievo 12.59 kWh (2.80 EUR), immissione 12.75 kWh (3.47 EUR).

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio su automatico EUR | Beneficio con SOC EUR | Beneficio su senza batteria EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F0 | 12.59 | 12.75 | 2.80 | 3.47 | 0.00 | 0 (0.00) | 5.87 (1.31) | 12.75 (3.47) | 2.28 | 1.59 | 0.00 | -0.00 | 1 |
| F0R | 12.59 | 12.75 | 2.80 | 3.47 | 0.00 | 0 (0.00) | 5.87 (1.31) | 12.75 (3.47) | 2.28 | 1.59 | 0.00 | -0.00 | 1 |

Beneficio = costo netto dello scenario solo autoconsumo - costo netto del profilo (stessi prezzi) - costo dei cambiamenti. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 522.31 W, modello 559.43 W.  FV: sera prima 382.42 W, modello 363.96 W.
Rendimenti usati: carica 0.966, scarica 0.890. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.125 s, massimo 0.724 s (qui). Calcolo del piano: massimo 0.512 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 12015.77 kB. Scritture nella memoria interna 1111.63 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 27, GitHub 26; dati ricevuti circa 1274.42 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| F0 | 00:00 | 00:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -4.93 EUR fino a fine prezzi; vantaggio su AUTO 0.158 EUR |
| F0R | 00:00 | 00:00 | SCARICA_5000 | 20.00 -> 20.00 | carica 0.00, scarica 0.00 | piano -4.93 EUR fino a fine prezzi; vantaggio su AUTO 0.158 EUR |

## Segnalazioni
- Dispacciamento non noto (calcolato a 0): inserirlo in config.lua quando disponibile.
