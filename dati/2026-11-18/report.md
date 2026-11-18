# Report EMS Cismondi - 18/11/2026 (feriale)

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

Letture: 288, ore integrate: 24.00. FV 19.01 kWh, consumi casa 27.77 kWh.
Reale: prelievo 10.61 kWh, immissione 0.14 kWh.  Solo autoconsumo simulato: prelievo 10.29 kWh, immissione 0.00 kWh.
Condizione 0 (senza batteria): prelievo 20.10 kWh (4.86 EUR), immissione 11.34 kWh (2.42 EUR), netto 2.44 EUR.
Condizione 1 (reale): acquisti 2.56 EUR, cessioni 0.03 EUR, usura batteria (9.76 kWh scaricati) inclusa: netto 2.73 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 19.64 | 7.11 | 4.74 | 1.68 | 0.04 | 4 (0.00) | 9.35 (2.26) | 7.11 (1.68) | -0.38 | -0.43 | 0.24 | -0.67 | 0.08 | 5 |
| C3 | 19.64 | 10.70 | 4.74 | 2.41 | 0.04 | 4 (0.00) | 9.35 (2.26) | 10.70 (2.41) | 0.35 | 0.30 | 0.30 | 0.06 | -0.00 | 4 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 665.78 W, modello 665.78 W.  FV: sera prima 142.89 W, modello 124.30 W.
Rendimenti usati: carica 0.976, scarica 0.886. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.187 s, massimo 1.079 s (qui). Calcolo del piano: massimo 0.989 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 20027.04 kB. Scritture nella memoria interna 1283.48 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 61, GitHub 22; dati ricevuti circa 1428.75 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2 | 00:00 | 11:00 | SCARICA_5000 | 5.00 -> 5.00 | carica 0.00, scarica 0.00 | piano -10.85 EUR fino a fine prezzi; vantaggio su AUTO 0.032 EUR |
| C3 | 00:00 | 12:30 | BATTERIA_FERMA | 5.67 -> 5.67 | carica 0.00, scarica 0.00 | piano -7.45 EUR fino a fine prezzi; vantaggio su AUTO 0.001 EUR |
| C2 | 11:00 | 14:30 | CARICA_FV_2000 | 5.00 -> 42.59 | carica 5.78, scarica 0.00 | piano -2.20 EUR fino a fine prezzi; vantaggio su AUTO 0.000 EUR |
| C2 | 14:30 | 16:45 | BATTERIA_FERMA | 42.59 -> 42.59 | carica 0.00, scarica 0.00 | piano -8.21 EUR fino a fine prezzi; vantaggio su AUTO 0.001 EUR |
| C3 | 13:15 | 16:45 | BATTERIA_FERMA | 19.01 -> 19.01 | carica 0.00, scarica 0.00 | piano -2.28 EUR fino a fine prezzi; vantaggio su AUTO 0.005 EUR |
| C2 | 16:45 | 17:15 | SCARICA_4000 | 42.59 -> 27.57 | carica 0.00, scarica 2.00 | piano -7.98 EUR fino a fine prezzi; vantaggio su AUTO 0.012 EUR |
| C3 | 16:45 | 17:15 | SCARICA_4000 | 19.01 -> 5.00 | carica 0.00, scarica 1.86 | piano -8.76 EUR fino a fine prezzi; vantaggio su AUTO 0.016 EUR |
| C2 | 17:15 | 00:00 | CARICA_FV_1000 | 27.57 -> 27.57 | carica 0.00, scarica 0.00 | piano -8.24 EUR fino a fine prezzi; vantaggio su AUTO 0.008 EUR |
| C3 | 17:15 | 00:00 | BATTERIA_FERMA | 5.00 -> 5.00 | carica 0.00, scarica 0.00 | piano -8.99 EUR fino a fine prezzi; vantaggio su AUTO 0.001 EUR |
