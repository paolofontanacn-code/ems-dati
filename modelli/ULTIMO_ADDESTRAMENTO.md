# Ultimo addestramento - 28/11/2026 11:17

Dati: 6972 quarti d'ora su 76 giorni (2026-09-12 - 2026-11-27).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 672 quarti d'ora su 672; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 698 | 149 | riferimento |
| Modello completo (GitHub) | 685 | 124 | non accettato |
| Coefficienti formato Mango | 690 | - | non accettati |
| Logica fuzzy (inerzia casa 48 h, oblio 0.98) | 683 | - | non accettata |

Consumi per le decisioni: previsioni del Mango.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 42.1, 0.6, 6.9, -0.0, 321.1
