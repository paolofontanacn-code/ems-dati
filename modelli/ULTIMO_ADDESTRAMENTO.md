# Ultimo addestramento - 10/11/2026 12:43

Dati: 5244 quarti d'ora su 58 giorni (2026-09-12 - 2026-11-09).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 633 quarti d'ora su 633; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 676 | 167 | riferimento |
| Modello completo (GitHub) | 656 | 180 | non accettato |
| Coefficienti formato Mango | 658 | - | non accettati |
| Logica fuzzy (inerzia casa 48 h, oblio 0.995) | 621 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 42.2, 0.0, 6.6, -0.0, 334.5
