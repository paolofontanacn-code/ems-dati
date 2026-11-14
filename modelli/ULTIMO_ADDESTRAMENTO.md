# Ultimo addestramento - 14/11/2026 01:02

Dati: 5628 quarti d'ora su 62 giorni (2026-09-12 - 2026-11-13).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 633 quarti d'ora su 633; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 641 | 179 | riferimento |
| Modello completo (GitHub) | 636 | 191 | non accettato |
| Coefficienti formato Mango | 594 | - | ACCETTATI |
| Logica fuzzy (inerzia casa 3 h, oblio 0.995) | 593 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 41.9, 0.0, 7.8, -0.0, 313.9
