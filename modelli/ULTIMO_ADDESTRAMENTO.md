# Ultimo addestramento - 27/11/2026 10:02

Dati: 6876 quarti d'ora su 75 giorni (2026-09-12 - 2026-11-26).

Verifica con il meteo PREVISTO la sera prima (richieste del Mango) in 672 quarti d'ora su 672; negli altri il meteo del dataset (quello usato dal Mango in quel momento).

| Verifica sugli ultimi giorni | Errore medio consumi W | Errore medio FV W | Esito |
|---|---|---|---|
| Previsioni del Mango (registrate) | 680 | 148 | riferimento |
| Modello completo (GitHub) | 661 | 127 | non accettato |
| Coefficienti formato Mango | 673 | - | non accettati |
| Logica fuzzy (inerzia casa 48 h, oblio 0.98, ore dei giorni prima) | 658 | - | ACCETTATA |

Consumi per le decisioni: logica fuzzy.
Pompa di calore (W per grado sotto 18 C, quadrato/10, x vento/10, x sole/1000, sopra 24 C): 42.6, 0.0, 7.1, -0.0, 316.5
