# Report EMS Cismondi - 19/11/2026 (feriale)

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

Letture: 288, ore integrate: 24.00. FV 13.94 kWh, consumi casa 25.69 kWh.
Reale: prelievo 13.12 kWh, immissione 0.07 kWh.  Solo autoconsumo simulato: prelievo 12.91 kWh, immissione 0.00 kWh.
Condizione 0 (senza batteria): prelievo 20.32 kWh (4.91 EUR), immissione 8.57 kWh (2.09 EUR), netto 2.82 EUR.
Condizione 1 (reale): acquisti 3.17 EUR, cessioni 0.02 EUR, usura batteria (7.37 kWh scaricati) inclusa: netto 3.30 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 20.00 | 11.11 | 4.83 | 2.77 | 0.06 | 3 (0.00) | 7.09 (1.71) | 11.11 (2.77) | 1.18 | 1.15 | 1.18 | 0.70 | 0.02 | 4 |
| C3 | 20.32 | 8.57 | 4.91 | 2.09 | 0.00 | 0 (0.00) | 7.41 (1.79) | 8.57 (2.09) | 0.48 | 0.45 | 0.45 | 0.00 | -0.00 | 1 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 748.01 W, modello 747.38 W.  FV: sera prima 158.82 W, modello 185.13 W.
Rendimenti usati: carica 0.976, scarica 0.886. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.185 s, massimo 0.987 s (qui). Calcolo del piano: massimo 0.955 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 19866.52 kB. Scritture nella memoria interna 1285.92 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 72, GitHub 22; dati ricevuti circa 1463.92 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2 | 00:00 | 10:00 | CARICA_FV_1000 | 27.57 -> 27.71 | carica 0.02, scarica 0.00 | piano -8.24 EUR fino a fine prezzi; vantaggio su AUTO 0.008 EUR |
| C2 | 10:00 | 10:15 | SCARICA_4000 | 27.71 -> 20.19 | carica 0.00, scarica 1.00 | piano -2.70 EUR fino a fine prezzi; vantaggio su AUTO 0.003 EUR |
| C2 | 10:15 | 11:00 | CARICA_FV_1000 | 20.19 -> 20.98 | carica 0.12, scarica 0.00 | piano -3.64 EUR fino a fine prezzi; vantaggio su AUTO 0.011 EUR |
| C2 | 11:00 | 00:00 | SCARICA_4000 | 20.98 -> 5.93 | carica 0.00, scarica 2.00 | piano -3.37 EUR fino a fine prezzi; vantaggio su AUTO 0.007 EUR |
| C3 | 00:00 | 00:00 | BATTERIA_FERMA | 5.00 -> 5.00 | carica 0.00, scarica 0.00 | piano -8.99 EUR fino a fine prezzi; vantaggio su AUTO 0.001 EUR |
