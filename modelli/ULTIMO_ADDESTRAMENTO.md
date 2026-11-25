# Ultimo addestramento - 25/11/2026 05:07

Dati: 6684 quarti d'ora su 73 giorni (2026-09-12 - 2026-11-24).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 672 quarti d'ora su 672; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 653 | 135 | riferimento |
| Modello completo (GitHub) | 624 | 135 | ACCETTATO |
| Coefficienti formato Mango | 625 | - | ACCETTATI |
| Logica fuzzy (inerzia casa 12 h, oblio 0.98) | 612 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 42.2, 0.0, 6.4, -0.0, 298.6
