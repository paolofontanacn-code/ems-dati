# Ultimo addestramento - 07/11/2026 21:12

Dati: 4995 quarti d'ora su 55 giorni (2026-09-12 - 2026-11-06).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 672 quarti d'ora su 672; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 740 | 137 | riferimento |
| Modello completo (GitHub) | 765 | 110 | non accettato |
| Coefficienti formato Mango | 724 | - | non accettati |
| Logica fuzzy (inerzia casa 48 h, oblio 0.98) | 641 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 41.7, 4.8, 0.0, -0.0, 348.3
