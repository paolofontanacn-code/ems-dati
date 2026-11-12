# Ultimo addestramento - 12/11/2026 13:35

Dati: 5436 quarti d'ora su 60 giorni (2026-09-12 - 2026-11-11).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 633 quarti d'ora su 633; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 645 | 188 | riferimento |
| Modello completo (GitHub) | 669 | 202 | non accettato |
| Coefficienti formato Mango | 620 | - | ACCETTATI |
| Logica fuzzy (inerzia casa 48 h, oblio 0.98) | 611 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 42.5, 2.2, 1.9, -0.0, 341.2
