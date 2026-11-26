# Report EMS Cismondi - 25/11/2026 (feriale)

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

Letture: 288, ore integrate: 24.00. FV 7.46 kWh, consumi casa 30.75 kWh.
Reale: prelievo 23.43 kWh, immissione 0.06 kWh.  Solo autoconsumo simulato: prelievo 23.56 kWh, immissione 0.00 kWh.
Condizione 0 (senza batteria): prelievo 25.35 kWh (6.12 EUR), immissione 2.07 kWh (0.57 EUR), netto 5.55 EUR.
Condizione 1 (reale): acquisti 5.66 EUR, cessioni 0.02 EUR, usura batteria (2.02 kWh scaricati) inclusa: netto 5.68 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 25.35 | 0.31 | 6.12 | 0.09 | 0.00 | 0 (0.00) | 1.79 (0.43) | 0.31 (0.09) | -0.35 | -0.31 | 0.78 | -0.48 | 0.34 | 1 |
| C3 | 24.93 | 1.44 | 6.02 | 0.40 | 0.03 | 4 (0.00) | 1.37 (0.33) | 1.44 (0.40) | 0.03 | 0.07 | 0.07 | -0.10 | 0.10 | 2 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 839.21 W, modello 834.58 W.  FV: sera prima 209.68 W, modello 186.10 W.
Rendimenti usati: carica 0.979, scarica 0.886. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.189 s, massimo 1.460 s (qui). Calcolo del piano: massimo 0.749 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 20136.59 kB. Scritture nella memoria interna 1447.96 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 26, GitHub 26; dati ricevuti circa 1255.70 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C3 | 12:00 | 12:15 | SCARICA_4000 | 8.78 -> 5.00 | carica 0.00, scarica 0.50 | piano -4.58 EUR fino a fine prezzi; vantaggio su AUTO 0.011 EUR |
| C3 | 12:45 | 13:00 | SCARICA_5000 | 8.97 -> 5.84 | carica 0.00, scarica 0.42 | piano -4.29 EUR fino a fine prezzi; vantaggio su AUTO 0.014 EUR |
| C2 | 00:00 | 00:00 | CARICA_FV_1000 | 30.67 -> 42.13 | carica 1.76, scarica 0.00 | piano -12.20 EUR fino a fine prezzi; vantaggio su AUTO 0.007 EUR |
