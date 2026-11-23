# Report EMS Cismondi - 22/11/2026 (domenica)

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

Letture: 288, ore integrate: 24.00. FV 3.03 kWh, consumi casa 31.25 kWh.
Reale: prelievo 27.90 kWh, immissione 0.01 kWh.  Solo autoconsumo simulato: prelievo 27.78 kWh, immissione 0.00 kWh.
Condizione 0 (senza batteria): prelievo 28.44 kWh (6.87 EUR), immissione 0.22 kWh (0.05 EUR), netto 6.82 EUR.
Condizione 1 (reale): acquisti 6.74 EUR, cessioni 0.00 EUR, usura batteria (0.57 kWh scaricati) inclusa: netto 6.75 EUR.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio sulla condizione 1 EUR | Beneficio su automatico simulato EUR | Beneficio con SOC EUR | Beneficio su condizione 0 EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 | 28.44 | 0.00 | 6.87 | 0.00 | 0.00 | 1 (0.00) | 0.66 (0.16) | 0.00 (0.00) | -0.12 | -0.15 | 1.29 | -0.05 | 0.11 | 2 |
| C3 | 28.25 | 0.00 | 6.82 | 0.00 | 0.00 | 0 (0.00) | 0.47 (0.11) | 0.00 (0.00) | -0.08 | -0.10 | -0.10 | -0.01 | 0.01 | 0 |

Costo netto = acquisto (prezzo fisso F0) - vendita (prezzo NORD al quarto d'ora) + usura batteria (0,02 EUR/kWh scaricato). Beneficio sulla condizione 1 = costo netto della condizione 1 (dati reali) - costo netto della condizione. Beneficio su automatico simulato = stesso confronto con l'automatico rifatto dal simulatore (controllo del simulatore). Beneficio su condizione 0 = confronto con l'impianto senza batteria. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 749.73 W, modello 749.73 W.  FV: sera prima 106.15 W, modello 65.55 W.
Rendimenti usati: carica 0.978, scarica 0.887. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.175 s, massimo 0.973 s (qui). Calcolo del piano: massimo 0.881 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 20173.38 kB. Scritture nella memoria interna 1389.82 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 28, GitHub 26; dati ricevuti circa 1277.97 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| C2 | 00:00 | 15:45 | CARICA_FV_1000 | 52.59 -> 54.03 | carica 0.22, scarica 0.00 | piano -8.58 EUR fino a fine prezzi; vantaggio su AUTO 0.001 EUR |
| C2 | 15:45 | 00:00 | BATTERIA_FERMA | 54.03 -> 54.03 | carica 0.00, scarica 0.00 | piano -8.07 EUR fino a fine prezzi; vantaggio su AUTO 0.020 EUR |
