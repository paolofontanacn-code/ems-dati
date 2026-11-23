# Ultimo addestramento - 23/11/2026 13:26

Dati: 6492 quarti d'ora su 71 giorni (2026-09-12 - 2026-11-22).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 672 quarti d'ora su 672; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 649 | 159 | riferimento |
| Modello completo (GitHub) | 625 | 146 | ACCETTATO |
| Coefficienti formato Mango | 632 | - | non accettati |
| Logica fuzzy (inerzia casa 48 h, oblio 0.995, ore dei giorni prima) | 620 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 42.7, 0.0, 6.8, -0.0, 314.4
