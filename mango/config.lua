-- config.lua - CONFIGURAZIONE della simulazione EMS sul Mango (impianto Cismondi)
-- SOLO SIMULAZIONE: il programma legge l'impianto ma non invia alcun comando all'inverter.
-- Modificare solo i valori, lasciando virgole e virgolette.
return {
  -- ================================================================ PREZZI E COSTI
  -- costo di un kWh prelevato = [energia x (1 + PERDITE) + DISPACCIAMENTO + TRASPORTO + ONERI + ACCISE] x (1 + IVA)
  --   profilo A: energia = PREZZO_FISSO_A
  --   profilo B: energia = PUN medio mensile della fascia (F1/F2/F3) + SPREAD_B
  --   profilo C: energia = PUN orario + SPREAD_C
  PREZZO_FISSO_A = 0.12,               -- EUR/kWh
  SPREAD_B = 0.02,                      -- EUR/kWh
  SPREAD_C = 0.02,                      -- EUR/kWh
  PERDITE = 0.10,                       -- 10 % bassa tensione (ARERA 117/2022/R/eel, TIS tab. 4), su energia e spread
  DISPACCIAMENTO = 0.0,                 -- EUR/kWh  >>> VALORE NON NOTO: inserirlo appena disponibile (bolletta) <<<
  TRASPORTO = 0.014730,                 -- EUR/kWh quota variabile, domestico non residente, IV trim. 2026
  ONERI = 0.033153,                     -- EUR/kWh quota variabile oneri di sistema, IV trim. 2026
  ACCISE = 0.0227,                      -- EUR/kWh, domestico non residente
  IVA = 0.10,                           -- uso domestico
  -- cessioni (RID): valore = prezzo zonale orario NORD x (1 - IMPOSTA_CESSIONI)
  IMPOSTA_CESSIONI = 0.40,              -- reddito diverso tassato al 40 % (indicazione dell'utente)
  ZONA = "NORD",
  PROFILI = { "A", "B", "C" },

  -- ================================================================ BATTERIA (LUNA2000 15 kWh)
  CAPACITA_KWH = 15.0,
  P_MAX_CARICA_W = 5000,
  P_MAX_SCARICA_W = 5000,
  SOC_MAX = 95,                         -- "Fine carica SOC"
  SOC_MIN = 6,                          -- "Fine scarica SOC" (riserva minima)
  SOC_MIN_VENDITA = 20,                 -- la scarica verso la rete non scende sotto questo SOC
  LIVELLI_SCARICA_W = { 1000, 2000, 3000, 5000 },   -- potenze graduate della scarica forzata
  P_CARICA_RITARDATA_W = 200,           -- potenza di carica minima impostabile via API (carica ritardata)
  -- rendimenti iniziali (IPOTESI): vengono sostituiti da quelli misurati appena ci sono dati sufficienti
  RENDIMENTO_CARICA = 0.95,             -- energia immagazzinata / energia entrante
  RENDIMENTO_SCARICA = 0.97,            -- energia DC in uscita / energia tolta (batteria)
  RENDIMENTO_INVERTER = 0.97,           -- energia AC / energia DC in scarica
  -- usura (VALORI INDICATIVI): EUR per kWh scaricato = COSTO_BATTERIA_EUR / (CICLI_VITA x CAPACITA_KWH)
  COSTO_BATTERIA_EUR = 6000,
  CICLI_VITA = 6000,

  -- ================================================================ IMPIANTO E RETE
  P_NOMINALE_FV_W = 11000,              -- 11 kWp, sud, inclinazione 5 gradi
  P_MAX_AC_INVERTER_W = 10000,          -- SUN2000 10 kW
  P_MAX_PRELIEVO_W = 7000,              -- prelievo massimo imposto (contratto 6 kW)
  P_MAX_IMMISSIONE_W = 8000,            -- potenza in immissione del contratto di connessione
  CARICA_DA_RETE_AMMESSA = true,        -- SOLO SIMULAZIONE: rete -> batteria di giorno
  P_MAX_CARICA_RETE_W = 1000,
  FV_MIN_GIORNO_W = 100,                -- "di giorno" = FV previsto/misurato almeno di questa potenza
  P_MAX_POMPA_CALORE_W = 3000,          -- potenza elettrica indicativa della pompa di calore
  LATITUDINE = nil, LONGITUDINE = nil,  -- nil = dalle informazioni dell'impianto su FusionSolar

  -- ================================================================ OTTIMIZZATORE
  PASSO_SOC_KWH = 0.1,                  -- griglia del SOC (piu' piccola = piu' precisa ma piu' lenta)
  MAX_FINESTRE_GIORNO = 14,             -- periodi forzati al giorno (limite TOU Huawei)
  MAX_COMANDI_GIORNO = 100,             -- comandi di controllo OAuth al giorno
  -- costo attribuito a ogni cambiamento di funzionamento (compreso il ritorno all'autoconsumo): l'ottimizzatore
  -- cambia solo se conviene anche pagando questo costo, che viene sottratto dal beneficio nei riepiloghi
  PENALITA_CAMBIO_EUR = 0.10,           -- EUR per cambiamento
  PENALITA_FINESTRA_EUR = 0.0,          -- costo aggiuntivo per periodo forzato: cresce da solo oltre le 14 finestre
  MARGINE_Z = 0.5,                      -- margine di sicurezza: deviazioni standard dell'errore di previsione
  ORE_SOC_ALTO = 90,                    -- soglia per registrare le ore a SOC alto (invecchiamento)

  -- ================================================================ SERVIZI
  URL_OAUTH = "https://oauth2.fusionsolar.huawei.com",
  URL_API_HUAWEI = "https://eu5.fusionsolar.huawei.com",
  CLIENT_ID = "765569051",
  CLIENT_SECRET = os.getenv("HUAWEI_CLIENT_SECRET"),   -- RISERVATO: segreto di GitHub o config_locale.lua sul Mango
  REDIRECT_URI = "https://paolofontanacn-code.github.io/fusionsolar-callback/",
  NOME_IMPIANTO = "Cismondi",
  LIMITE_CHIAMATE_GIORNO = 950,         -- Huawei: 1000 al giorno per proprietario
  URL_API_GME = "https://api.mercatoelettrico.org/request/api/v1",
  ORA_PREZZI = 13.5,                    -- 13:30 primo tentativo prezzi del giorno dopo (poi ogni 30 min)
  URL_METEO = "https://api.open-meteo.com/v1/forecast",
  URL_METEO_STORICO = "https://archive-api.open-meteo.com/v1/archive",
  MODELLI_METEO = "icon_seamless,ecmwf_ifs025,gfs_seamless",
  URL_GITHUB = "https://api.github.com",
  GITHUB_OWNER = "paolofontanacn-code",
  GITHUB_REPO = "ems-dati",
  GITHUB_BRANCH = "main",
  ORA_LIMITE_PREVISIONI_GITHUB = 21,    -- se le previsioni di GitHub non arrivano entro le 21 usa le proprie

  -- ================================================================ FUNZIONAMENTO
  INTERVALLO_MIN = 5,
  BUCO_MAX_MIN = 20,                    -- intervalli piu' lunghi non vengono integrati (dato mancante)
  DURATA_PROVA_GIORNI = 5,
  STORICO_GIORNI_MAX = 450,             -- giorno 0: giorni di storico FusionSolar da importare
  CARTELLA_RAM = os.getenv("EMS_RAM") or "/tmp/ems_sim",
  CARTELLA_DATI = os.getenv("EMS_DATI"), -- nil = cartella "dati" accanto ai programmi (memoria interna)
  -- modalita' GitHub: ritardo con cui si rigiocano le letture (lo storico Huawei arriva con qualche minuto di ritardo)
  RITARDO_STORICO_MIN = 20,
  FATTORE_MANGO = nil,                  -- tempo Mango / tempo GitHub: si misura con benchmark_mango.lua (nil = non tarato)
}
