# Report EMS Cismondi - 17/10/2026 (sabato)

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

Letture: 171, ore integrate: 14.25. FV 20.38 kWh, consumi casa 11.50 kWh.
Reale: prelievo 0.47 kWh, immissione 0.61 kWh.  Solo autoconsumo simulato: prelievo 0.11 kWh, immissione 0.00 kWh.

| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo netto EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio EUR | Beneficio con SOC EUR | Rimpianto EUR | Finestre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 0.11 | 0.00 | 0.00 | 0.00 | 0.33 | 0 (0.00) | 0.00 (0.00) | 0.00 (0.00) | 0.00 | 0.00 | - | 0 |
| B | 0.11 | 0.00 | 0.00 | 0.00 | 0.33 | 0 (0.00) | 0.00 (0.00) | 0.00 (0.00) | 0.00 | 0.00 | - | 0 |
| C | 0.11 | 0.00 | 0.00 | 0.00 | 0.33 | 0 (0.00) | 0.00 (0.00) | 0.00 (0.00) | 0.00 | 0.00 | - | 0 |

Beneficio = costo netto dello scenario solo autoconsumo - costo netto del profilo (stessi prezzi) - costo dei cambiamenti. Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno.

## Previsioni
Errore medio consumi: sera prima - W, modello 489.45 W.  FV: sera prima - W, modello 287.08 W.
Rendimenti usati: carica 0.974, scarica 0.970. Ore con SOC reale >= 90 %: 3.00.

## Carico di lavoro del Mango
Cicli: 172. CPU per ciclo: media 0.153 s, massimo 0.740 s (qui). Calcolo del piano: massimo 0.650 s (qui).
Stima sul Mango: media da tarare, massimo da tarare, piano da tarare (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua).
Memoria Lua massima 15327.88 kB. Scritture nella memoria interna 1349.94 kB al giorno.
Chiamate che il Mango farebbe in un giorno: Huawei 516 (limite 950), GME 18, meteo 17, GitHub 4; dati ricevuti circa 825.75 kB.

## Periodi di carica e scarica forzata (profili)
Nessun periodo forzato: tutti i profili sono rimasti in autoconsumo.

## Segnalazioni
- Ottimo a posteriori non calcolato: dati del giorno incompleti (letture mancanti in qualche quarto d'ora).
- Dispacciamento non noto (calcolato a 0): inserirlo in config.lua quando disponibile.
