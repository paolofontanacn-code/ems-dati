# Report EMS Cismondi - 20/11/2026 (feriale)

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

Letture: 288, ore integrate: 24.00. FV 18.19 kWh, consumi casa 23.49 kWh.
Reale: prelievo 8.79 kWh, immissione 0.48 kWh.  Solo autoconsumo simulato: prelievo 8.16 kWh, immissione 0.00 kWh.
Condizione 0 (senza batteria): prelievo 17.21 kWh (4.16 EUR), immissione 11.90 kWh (2.49 EUR), netto 1.66 EUR.
Condizione 1 (reale): acquisti 2.12 EUR, cessioni 0.11 EUR, usura batteria (8.87 kWh scaricati) inclusa: netto 2.19 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 17.15 | 9.26 | 4.14 | 1.98 | 0.00 | 3 (0.00) | 8.99 (2.17) | 9.26 (1.98) | 0.02 | -0.02 | 0.23 | -0.51 | 0.04 | 3 |
| C3 | 17.02 | 11.68 | 4.11 | 2.44 | 0.00 | 1 (0.00) | 8.86 (2.14) | 11.68 (2.44) | 0.52 | 0.48 | 0.21 | -0.01 | 0.02 | 1 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 647.97 W, modello 647.97 W.  FV: sera prima 113.04 W, modello 133.26 W.
Rendimenti usati: carica 0.978, scarica 0.886. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.192 s, massimo 1.426 s (qui). Calcolo del piano: massimo 0.766 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 19961.27 kB. Scritture nella memoria interna 1327.79 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 37, GitHub 26; dati ricevuti circa 1365.20 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2 | 00:00 | 12:00 | SCARICA_4000 | 5.93 -> 5.93 | carica 0.00, scarica 0.00 | piano -3.37 EUR fino a fine prezzi; vantaggio su AUTO 0.007 EUR |
| C3 | 00:00 | 15:00 | BATTERIA_FERMA | 5.00 -> 5.00 | carica 0.00, scarica 0.00 | piano -8.99 EUR fino a fine prezzi; vantaggio su AUTO 0.001 EUR |
| C2 | 13:15 | 18:45 | BATTERIA_FERMA | 22.69 -> 22.69 | carica 0.00, scarica 0.00 | piano -2.99 EUR fino a fine prezzi; vantaggio su AUTO 0.000 EUR |
| C2 | 18:45 | 00:00 | CARICA_FV_1000 | 22.69 -> 22.69 | carica 0.00, scarica 0.00 | piano -9.38 EUR fino a fine prezzi; vantaggio su AUTO 0.003 EUR |
