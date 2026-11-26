# Ultimo addestramento - 26/11/2026 16:45

Dati: 6780 quarti d'ora su 74 giorni (2026-09-12 - 2026-11-25).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 672 quarti d'ora su 672; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 682 | 145 | riferimento |
| Modello completo (GitHub) | 656 | 135 | ACCETTATO |
| Coefficienti formato Mango | 661 | - | ACCETTATI |
| Logica fuzzy (inerzia casa 3 h, oblio 0.995) | 645 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 42.2, 0.0, 6.3, -0.0, 299.3
Previsioni per 20261127: accettate (consumi: logica fuzzy (migliore delle previsioni del Mango)).
