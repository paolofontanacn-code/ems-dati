# Ultimo addestramento - 21/11/2026 07:59

Dati: 6300 quarti d'ora su 69 giorni (2026-09-12 - 2026-11-20).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 672 quarti d'ora su 672; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 648 | 157 | riferimento |
| Modello completo (GitHub) | 663 | 167 | non accettato |
| Coefficienti formato Mango | 634 | - | non accettati |
| Logica fuzzy (inerzia casa 48 h, oblio 0.98) | 624 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 42.1, 0.0, 8.5, -0.0, 321.9
