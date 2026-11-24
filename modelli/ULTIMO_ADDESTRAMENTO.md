# Ultimo addestramento - 24/11/2026 01:20

Dati: 6588 quarti d'ora su 72 giorni (2026-09-12 - 2026-11-23).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 672 quarti d'ora su 672; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 637 | 153 | riferimento |
| Modello completo (GitHub) | 620 | 139 | non accettato |
| Coefficienti formato Mango | 621 | - | non accettati |
| Logica fuzzy (inerzia casa 24 h, oblio 0.98) | 610 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 43.1, 0.0, 5.4, -0.0, 313.2
Previsioni per 20261124: accettate (consumi: logica fuzzy (migliore delle previsioni del Mango)).
