# Ultimo addestramento - 13/11/2026 19:32

Dati: 5532 quarti d'ora su 61 giorni (2026-09-12 - 2026-11-12).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 633 quarti d'ora su 633; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 639 | 174 | riferimento |
| Modello completo (GitHub) | 641 | 201 | non accettato |
| Coefficienti formato Mango | 603 | - | ACCETTATI |
| Logica fuzzy (inerzia casa 6 h, oblio 0.98) | 596 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 40.2, 2.6, 4.4, -0.0, 327.9
