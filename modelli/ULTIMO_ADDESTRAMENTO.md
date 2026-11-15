# Ultimo addestramento - 15/11/2026 04:32

Dati: 5724 quarti d'ora su 63 giorni (2026-09-12 - 2026-11-14).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 672 quarti d'ora su 672; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 636 | 159 | riferimento |
| Modello completo (GitHub) | 680 | 213 | non accettato |
| Coefficienti formato Mango | 593 | - | ACCETTATI |
| Logica fuzzy (inerzia casa 3 h, oblio 0.995) | 601 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 41.8, 1.3, 6.8, -0.0, 353.0
