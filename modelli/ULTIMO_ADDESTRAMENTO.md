# Ultimo addestramento - 16/11/2026 20:33

Dati: 5820 quarti d'ora su 64 giorni (2026-09-12 - 2026-11-15).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 672 quarti d'ora su 672; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 648 | 169 | riferimento |
| Modello completo (GitHub) | 676 | 187 | non accettato |
| Coefficienti formato Mango | 611 | - | ACCETTATI |
| Logica fuzzy (inerzia casa 3 h, oblio 0.995) | 616 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 39.9, 0.0, 12.1, -0.0, 317.1
