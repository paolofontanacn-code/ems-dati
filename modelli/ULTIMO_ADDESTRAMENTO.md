# Ultimo addestramento - 20/11/2026 02:02

Dati: 6204 quarti d'ora su 68 giorni (2026-09-12 - 2026-11-19).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 672 quarti d'ora su 672; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 647 | 182 | riferimento |
| Modello completo (GitHub) | 699 | 200 | non accettato |
| Coefficienti formato Mango | 630 | - | non accettati |
| Logica fuzzy (inerzia casa 6 h, oblio 0.98, ore dei giorni prima) | 626 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 38.0, 0.0, 18.1, -0.0, 300.3
