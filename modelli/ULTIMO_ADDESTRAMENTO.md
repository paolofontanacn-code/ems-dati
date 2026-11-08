# Ultimo addestramento - 08/11/2026 19:30

Dati: 5052 quarti d'ora su 56 giorni (2026-09-12 - 2026-11-07).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 633 quarti d'ora su 633; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 742 | 144 | riferimento |
| Modello completo (GitHub) | 744 | 133 | non accettato |
| Coefficienti formato Mango | 713 | - | ACCETTATI |
| Logica fuzzy (inerzia casa 48 h, oblio 0.98) | 643 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 41.7, 4.8, 0.0, -0.0, 348.3
