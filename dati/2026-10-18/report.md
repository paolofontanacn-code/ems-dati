# Report EMS Cismondi - 18/10/2026 (domenica)

**SOLO SIMULAZIONE**: nessun comando inviato all'inverter.

## Scenari

| Scenario | Prezzo dell'energia acquistata | Descrizione |
|---|---|---|
| **A** - prezzo fisso | 0.12 EUR/kWh (con i costi aggiuntivi: 0.223 EUR/kWh) | Batteria gestita dall'ottimizzatore con un prezzo d'acquisto uguale in tutte le ore. |
| **B** - PUN per fascia | PUN medio mensile della fascia F1/F2/F3 + spread 0.02 EUR/kWh | Come il contratto indicizzato a fasce. Durante il mese il PUN di fascia e' stimato con i giorni gia' pubblicati dal GME. |
| **C** - PUN orario | PUN dell'ora + spread 0.02 EUR/kWh | Prezzo d'acquisto diverso ogni ora: l'ottimizzatore puo' spostare l'uso della batteria verso le ore piu' care. |
| Solo autoconsumo | (valutato con i prezzi di ciascuno scenario) | Riferimento: la batteria lasciata in massimo autoconsumo, senza ottimizzatore. |

In tutti gli scenari: ai prezzi dell'energia si aggiungono gli stessi costi (perdite 10 % su energia e spread, dispacciamento NON NOTO (per ora 0), trasporto 0.0147, oneri di sistema 0.0332, accise 0.0227 EUR/kWh, IVA 10 %). Le cessioni (RID) valgono il prezzo zonale orario NORD meno l'imposta del 40 %. Ogni scenario ha la sua batteria simulata (SOC proprio) e l'ottimizzatore sceglie ogni 15 minuti tra autoconsumo, carica ritardata, carica forzata (solo FV o FV + rete fino a 1000 W di giorno) e scarica forzata a potenze graduate, con al massimo 14 periodi forzati al giorno. Ogni cambiamento di funzionamento (compreso il ritorno all'autoconsumo) ha un costo attribuito di 0.10 EUR: si cambia solo se conviene anche pagandolo, e il costo e' sottratto dal beneficio.

> Il dispacciamento non e' ancora noto ed e' calcolato a 0: i costi d'acquisto di A, B e C sono sottostimati della stessa quantita' per kWh. I kWh sono registrati nel dataset, quindi i costi si possono ricalcolare quando il valore sara' noto.

Letture: 288, ore integrate: 24.00. FV 13.69 kWh, consumi casa 20.89 kWh.
Reale: prelievo 1.42 kWh, immissione 0.22 kWh.  Solo autoconsumo simulato: prelievo 0.51 kWh, immissione 0.00 kWh.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo netto EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio EUR | Beneficio con SOC EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 0.51 | 0.00 | 0.11 | 0.00 | 0.88 | 0 (0.00) | 0.00 (0.00) | 0.00 (0.00) | 0.00 | 0.00 | -0.09 | 0 |
| B | 7.02 | 0.00 | 2.64 | 0.00 | 0.45 | 1 (0.10) | 6.51 (2.45) | 0.00 (0.00) | -2.12 | -0.12 | -0.07 | 1 |
| C | 12.66 | 0.00 | 4.90 | 0.00 | 0.07 | 1 (0.10) | 12.15 (4.71) | 0.00 (0.00) | -4.00 | -0.45 | 0.24 | 1 |

Beneficio = costo netto dello scenario solo autoconsumo - costo netto del profilo (stessi prezzi) - costo dei cambiamenti. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima 540.99 W, modello 534.81 W.  FV: sera prima 200.53 W, modello 263.82 W.
Rendimenti usati: carica 0.980, scarica 0.870. Ore con SOC reale >= 90 %: -.

## Carico di lavoro del Mango
Cicli: 288. CPU per ciclo: media 0.154 s, massimo 0.775 s (qui). Calcolo del piano: massimo 0.674 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 16178.32 kB. Scritture nella memoria interna 1133.47 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 864 (limite 950), GME 3, meteo 28, GitHub 22; dati ricevuti circa 1288.38 kB.

## Periodi di carica e scarica forzata (profili)
| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |
|---|---|---|---|---|---|---|
| B | 14:45 | 00:00 | CARICA_FV | 51.66 -> 55.41 | carica 0.57, scarica 0.00 | piano -10.97 EUR fino a fine prezzi; vantaggio su AUTO 0.003 EUR |
| C | 02:00 | 00:00 | CARICA_FV | 52.08 -> 94.56 | carica 6.51, scarica 0.00 | piano -3.96 EUR fino a fine prezzi; vantaggio su AUTO 0.001 EUR |

## Segnalazioni
- Dispacciamento non noto (calcolato a 0): inserirlo in config.lua quando disponibile.
