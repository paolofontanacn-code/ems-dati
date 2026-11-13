# Report EMS Cismondi - 13/11/2026 (feriale)

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

Letture: 288, ore integrate: 24.00. FV 17.27 kWh, consumi casa 25.27 kWh.
Reale: prelievo 10.00 kWh, immissione 0.17 kWh.  Solo autoconsumo simulato: prelievo 9.84 kWh, immissione 0.00 kWh.
Condizione 0 (senza batteria): prelievo 19.32 kWh (4.67 EUR), immissione 11.32 kWh (2.59 EUR), netto 2.08 EUR.
Condizione 1 (reale): acquisti 2.41 EUR, cessioni 0.04 EUR, usura batteria (9.55 kWh scaricati) inclusa: netto 2.56 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 19.30 | 10.71 | 4.66 | 2.57 | 0.02 | 3 (0.00) | 9.46 (2.29) | 10.71 (2.57) | 0.45 | 0.45 | 0.66 | -0.04 | 0.13 | 4 |
| C3 | 4.49 | 4.78 | 1.09 | 1.37 | 0.12 | 2 (0.00) | -5.35 (1.09) | 4.78 (1.37) | 2.73 | 0.27 | 0.21 | 2.24 | -0.62 | 1 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 646.95 W, modello 646.95 W.  FV: sera prima 320.44 W, modello 274.74 W.
Rendimenti usati: carica 0.975, scarica 0.886. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.173 s, massimo 0.892 s (qui). Calcolo del piano: massimo 0.837 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 18976.59 kB. Scritture nella memoria interna 1435.38 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 34, GitHub 26; dati ricevuti circa 1318.79 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2 | 00:00 | 09:00 | CARICA_FV_1000 | 11.42 -> 11.42 | carica 0.00, scarica 0.00 | piano -10.91 EUR fino a fine prezzi; vantaggio su AUTO 0.033 EUR |
| C2 | 09:00 | 12:15 | SCARICA_4000 | 11.42 -> 5.00 | carica 0.00, scarica 0.85 | piano -3.26 EUR fino a fine prezzi; vantaggio su AUTO 0.034 EUR |
| C2 | 12:15 | 13:00 | CARICA_FV_2000 | 5.00 -> 14.34 | carica 1.44, scarica 0.00 | piano -3.25 EUR fino a fine prezzi; vantaggio su AUTO 0.000 EUR |
| C3 | 18:45 | 20:15 | SCARICA_4000 | 48.62 -> 6.00 | carica 0.00, scarica 5.67 | piano -9.82 EUR fino a fine prezzi; vantaggio su AUTO 0.023 EUR |
| C2 | 13:00 | 00:00 | BATTERIA_FERMA | 14.34 -> 14.34 | carica 0.00, scarica 0.00 | piano -3.04 EUR fino a fine prezzi; vantaggio su AUTO 0.002 EUR |
