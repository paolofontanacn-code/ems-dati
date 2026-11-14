# Report EMS Cismondi - 14/11/2026 (sabato)

**SOLO SIMULAZIONE**: nessun comando inviato all'inverter.

## Scenari

Prezzo d'acquisto fisso F0: 0.12 EUR/kWh di energia, 0.2415 EUR/kWh con i costi aggiuntivi (perdite 10 % su energia e spread, dispacciamento 0.0170, trasporto 0.0147, oneri di sistema 0.0332, accise 0.0227 EUR/kWh, IVA 10 %).

| Condizione | Descrizione |
|---|---|
| **0** | Impianto senza batteria: solo autoconsumo istantaneo del FV, il resto si compra, l'eccedenza si cede. |
| **1** | Impianto con batteria senza ottimizzazione (come oggi): dati REALI misurati da Huawei. |
| **2 (programmazione dinamica)** | Batteria con ottimizzazione di carica e scarica, senza carica AC dalla rete. |
| **3 (algoritmo evolutivo)** | Batteria con ottimizzazione di carica e scarica, senza carica AC dalla rete. |
| controllo | Automatico simulato: la condizione 1 rifatta dal simulatore, per misurarne la precisione. |

Cessioni (RID): prezzo zonale NORD del quarto d'ora. Usura batteria: 0.020 EUR per kWh scaricato. Ogni scenario ha la sua batteria simulata e l'ottimizzatore sceglie ogni 15 minuti tra autoconsumo, carica ritardata, carica forzata e scarica forzata a potenze graduate, con al massimo 14 periodi forzati e 1 ciclo di scarica forzata al giorno. Ogni cambiamento di funzionamento costa 0.001 EUR: si cambia solo se conviene anche pagandolo.

Letture: 286, ore integrate: 24.00. FV 2.51 kWh, consumi casa 31.93 kWh.
Reale: prelievo 29.32 kWh, immissione 0.00 kWh.  Solo autoconsumo simulato: prelievo 29.13 kWh, immissione 0.00 kWh.
Condizione 0 (senza batteria): prelievo 29.42 kWh (7.11 EUR), immissione 0.00 kWh (0.00 EUR), netto 7.11 EUR.
Condizione 1 (reale): acquisti 7.08 EUR, cessioni 0.00 EUR, usura batteria (0.10 kWh scaricati) inclusa: netto 7.08 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 29.27 | 1.10 | 7.07 | 0.33 | 0.02 | 1 (0.00) | 0.15 (0.04) | 1.10 (0.33) | 0.32 | 0.28 | 0.28 | 0.34 | 0.00 | 2 |
| C3 | 29.42 | 0.00 | 7.11 | 0.00 | 0.00 | 0 (0.00) | 0.29 (0.07) | 0.00 (0.00) | -0.02 | -0.07 | -0.07 | 0.00 | -0.00 | 0 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 718.92 W, modello 718.92 W.  FV: sera prima 79.59 W, modello 73.30 W.
Rendimenti usati: carica 0.975, scarica 0.886. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.185 s, massimo 1.087 s (qui). Calcolo del piano: massimo 0.987 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 20378.12 kB. Scritture nella memoria interna 1223.97 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 49, GitHub 22; dati ricevuti circa 1438.20 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2 | 00:00 | 15:45 | BATTERIA_FERMA | 14.34 -> 14.34 | carica 0.00, scarica 0.00 | piano -3.04 EUR fino a fine prezzi; vantaggio su AUTO 0.002 EUR |
| C2 | 15:45 | 00:00 | SCARICA_5000 | 14.34 -> 5.00 | carica 0.00, scarica 1.24 | piano -10.85 EUR fino a fine prezzi; vantaggio su AUTO 0.032 EUR |
