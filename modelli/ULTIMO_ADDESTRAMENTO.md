# Ultimo addestramento - 09/11/2026 21:40

Dati: 5148 quarti d'ora su 57 giorni (2026-09-12 - 2026-11-08).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 633 quarti d'ora su 633; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 710 | 159 | riferimento |
| Modello completo (GitHub) | 668 | 167 | ACCETTATO |
| Coefficienti formato Mango | 674 | - | ACCETTATI |
| Logica fuzzy (inerzia casa 48 h, oblio 0.98) | 630 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 41.5, 4.8, 0.0, -0.0, 345.4
Previsioni per 20261110: accettate (consumi: logica fuzzy (migliore delle previsioni del Mango)).
