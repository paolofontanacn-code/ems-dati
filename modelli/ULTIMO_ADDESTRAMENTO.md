# Ultimo addestramento - 17/11/2026 20:04

Dati: 5916 quarti d'ora su 65 giorni (2026-09-12 - 2026-11-16).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 672 quarti d'ora su 672; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 652 | 170 | riferimento |
| Modello completo (GitHub) | 682 | 177 | non accettato |
| Coefficienti formato Mango | 608 | - | ACCETTATI |
| Logica fuzzy (inerzia casa 6 h, oblio 0.98) | 615 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 41.7, 0.0, 9.4, -0.0, 337.7
