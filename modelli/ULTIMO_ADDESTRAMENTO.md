# Ultimo addestramento - 22/11/2026 18:06

Dati: 6396 quarti d'ora su 70 giorni (2026-09-12 - 2026-11-21).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 672 quarti d'ora su 672; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 659 | 176 | riferimento |
| Modello completo (GitHub) | 631 | 150 | ACCETTATO |
| Coefficienti formato Mango | 642 | - | non accettati |
| Logica fuzzy (inerzia casa 24 h, oblio 0.995, ore dei giorni prima) | 633 | - | ACCETTATA |

Consumi per le decisioni: modello completo.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 42.7, 0.0, 6.8, -0.0, 311.6
Previsioni per 20261123: accettate (migliore delle previsioni del Mango).
