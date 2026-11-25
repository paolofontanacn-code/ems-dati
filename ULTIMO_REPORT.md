# Report EMS Cismondi - 24/11/2026 (feriale)

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

Letture: 288, ore integrate: 24.00. FV 3.24 kWh, consumi casa 28.55 kWh.
Reale: prelievo 25.54 kWh, immissione 0.00 kWh.  Solo autoconsumo simulato: prelievo 25.34 kWh, immissione 0.00 kWh.
Condizione 0 (senza batteria): prelievo 25.52 kWh (6.16 EUR), immissione 0.21 kWh (0.05 EUR), netto 6.12 EUR.
Condizione 1 (reale): acquisti 6.17 EUR, cessioni 0.00 EUR, usura batteria (0.00 kWh scaricati) inclusa: netto 6.17 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 25.21 | 1.69 | 6.09 | 0.50 | 0.04 | 4 (0.00) | -0.13 (-0.03) | 1.69 (0.50) | 0.53 | 0.49 | 1.24 | 0.48 | 0.17 | 5 |
| C3 | 25.34 | 0.00 | 6.12 | 0.00 | 0.00 | 0 (0.00) | 0.00 (0.00) | 0.00 (0.00) | 0.04 | 0.00 | 0.00 | -0.01 | 0.01 | 0 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 742.98 W, modello 716.22 W.  FV: sera prima 122.72 W, modello 62.37 W.
Rendimenti usati: carica 0.979, scarica 0.886. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.237 s, massimo 1.109 s (qui). Calcolo del piano: massimo 1.012 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 20217.29 kB. Scritture nella memoria interna 1436.96 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 27, GitHub 26; dati ricevuti circa 1263.16 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2 | 00:00 | 06:45 | CARICA_FV_1000 | 44.35 -> 44.35 | carica 0.00, scarica 0.00 | piano -9.13 EUR fino a fine prezzi; vantaggio su AUTO 0.011 EUR |
| C2 | 06:45 | 07:00 | SCARICA_4000 | 44.35 -> 36.83 | carica 0.00, scarica 1.00 | piano -5.31 EUR fino a fine prezzi; vantaggio su AUTO 0.013 EUR |
| C2 | 07:00 | 17:15 | CARICA_FV_1000 | 36.83 -> 38.19 | carica 0.21, scarica 0.00 | piano -5.36 EUR fino a fine prezzi; vantaggio su AUTO 0.016 EUR |
| C2 | 17:15 | 17:30 | SCARICA_4000 | 38.19 -> 30.67 | carica 0.00, scarica 1.00 | piano -12.02 EUR fino a fine prezzi; vantaggio su AUTO 0.010 EUR |
| C2 | 17:30 | 00:00 | CARICA_FV_1000 | 30.67 -> 30.67 | carica 0.00, scarica 0.00 | piano -12.20 EUR fino a fine prezzi; vantaggio su AUTO 0.007 EUR |
