# Ultimo addestramento - 18/11/2026 17:33

Dati: 6012 quarti d'ora su 66 giorni (2026-09-12 - 2026-11-17).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 672 quarti d'ora su 672; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 631 | 181 | riferimento |
| Modello completo (GitHub) | 697 | 192 | non accettato |
| Coefficienti formato Mango | 617 | - | non accettati |
| Logica fuzzy (inerzia casa 3 h, oblio 0.995) | 613 | - | non accettata |

Consumi per le decisioni: previsioni del Mango.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 41.2, 0.0, 10.1, -0.0, 332.2
Previsioni per 20261119: non accettate (non migliore del Mango).
