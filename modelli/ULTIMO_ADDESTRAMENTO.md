# Ultimo addestramento - 11/11/2026 01:38

Dati: 5340 quarti d'ora su 59 giorni (2026-09-12 - 2026-11-10).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 633 quarti d'ora su 633; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 679 | 163 | riferimento |
| Modello completo (GitHub) | 694 | 187 | non accettato |
| Coefficienti formato Mango | 641 | - | ACCETTATI |
| Logica fuzzy (inerzia casa 6 h, oblio 0.98) | 616 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 42.4, 1.2, 4.1, -0.0, 338.9
