# Ultimo addestramento - 19/11/2026 16:02

Dati: 6108 quarti d'ora su 67 giorni (2026-09-12 - 2026-11-18).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 672 quarti d'ora su 672; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 640 | 170 | riferimento |
| Modello completo (GitHub) | 690 | 186 | non accettato |
| Coefficienti formato Mango | 620 | - | ACCETTATI |
| Logica fuzzy (inerzia casa 48 h, oblio 0.98, ore dei giorni prima) | 617 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 37.8, 0.0, 18.6, -0.0, 298.9
