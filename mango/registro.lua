-- registro.lua - file CSV (dataset per l'IA, periodi, riepilogo) e report giornaliero
-- Le righe si accumulano in RAM e ogni ora vengono aggiunte ai file nella memoria interna.
local F = require "lib_file"
local PA = require "prezzi_acquisto"
local M = {}

local FLUSSI = { "fv_carichi", "fv_batt", "rete_batt", "batt_carichi", "batt_rete", "fv_rete", "rete_carichi" }
M.FLUSSI = FLUSSI

-- ------------------------------------------------------------------ colonne del dataset (una riga ogni 5 minuti)
local function colonne_dataset(profili)
  local c = {
    "ts", "data_ora", "giorno", "ora", "minuto", "quarto_gme", "ora_gme", "settimana", "tipo_giorno", "fascia", "mese",
    "dt_s", "integrato", "qualita",
    -- misure Huawei
    "fv_w", "carico_w", "inverter_w", "batteria_w", "soc", "contatore_w", "prelievo_w", "immissione_w",
    "modo_reale_cod", "modo_reale", "stato_batteria_cod", "stato_batteria", "chiamate_huawei",
    -- prezzi (EUR/kWh)
    "nord", "pun", "nord_15", "pun_15", "costo_acquisto", "valore_cessione", "usura",
    -- meteo
    "temp_c", "temp_lag3h_c", "umidita", "nuvole", "ghi_wm2", "vento", "pioggia", "ghi_disp", "temp_disp", "n_modelli_meteo",
    -- previsioni
    "prev_carico_w", "prev_fv_w", "prev_carico_corr_w", "prev_fv_corr_w", "prev_carico_sera_w", "prev_fv_sera_w",
    "err_carico_w", "err_fv_w", "fonte_prev", "pdc_stima_w", "comportamento_w", "coef_fv", "cielo",
    "sigma_carico_w", "sigma_fv_rel",
    -- rendimenti
    "eta_carica", "eta_scarica", "eta_inv_500", "eta_inv_1000", "eta_inv_2000", "eta_inv_oltre", "fonte_rendimenti",
    -- energia reale nell'intervallo
    "reale_prel_kwh", "reale_imm_kwh", "reale_ricavo_eur",
    -- scenario 0: senza batteria
    "zero_prel_kwh", "zero_imm_kwh", "zero_costo_eur", "zero_ricavo_eur",
    -- scenario solo autoconsumo (simulato)
    "auto_soc", "auto_batteria_w",
  }
  for _, f in ipairs(FLUSSI) do c[#c + 1] = "auto_" .. f .. "_w" end
  for _, x in ipairs({ "auto_tagliato_w", "auto_sforamento_w", "auto_prel_kwh", "auto_imm_kwh", "auto_scarica_kwh" }) do c[#c + 1] = x end
  for _, p in ipairs(profili) do
    for _, x in ipairs({ "azione", "categoria", "soc", "batteria_w" }) do c[#c + 1] = p .. "_" .. x end
    for _, f in ipairs(FLUSSI) do c[#c + 1] = p .. "_" .. f .. "_w" end
    for _, x in ipairs({ "tagliato_w", "sforamento_w", "prel_kwh", "imm_kwh", "scarica_kwh", "costo_eur", "ricavo_eur",
      "usura_eur", "auto_costo_eur", "auto_ricavo_eur", "auto_usura_eur", "reale_costo_eur", "beneficio_eur",
      "costo_interventi_eur", "finestre_oggi", "comandi_oggi", "decisione", "motivo", "vantaggio_eur", "valore_piano_eur", "ore_soc_alto" }) do
      c[#c + 1] = p .. "_" .. x
    end
  end
  c[#c + 1] = "ore_soc_alto_reale"
  return c
end

M.COL_CARICO = { "ts", "data_ora", "cpu_s", "memoria_kb", "scritti_byte", "piano_s", "huawei_reali", "huawei_equivalenti",
  "gme", "meteo", "github_reali", "github_equivalenti", "byte_ricevuti", "secondi_rete" }

local COL_PERIODI = { "profilo", "inizio", "fine", "durata_min", "azione", "categoria", "motivo", "soc_inizio", "soc_fine",
  "carica_fv_kwh", "carica_rete_kwh", "scarica_kwh", "prelievo_kwh", "immissione_kwh", "nord_medio", "costo_medio", "euro_netto" }

local function colonne_riepilogo(profili)
  local c = { "giorno", "tipo_giorno", "letture", "ore_integrate", "fv_kwh", "carico_kwh", "reale_prel_kwh", "reale_imm_kwh",
    "auto_prel_kwh", "auto_imm_kwh", "auto_soc_fine", "mae_carico_sera_w", "mae_fv_sera_w", "mae_carico_modello_w",
    "mae_fv_modello_w", "eta_carica", "eta_scarica", "ore_soc_alto_reale", "chiamate_huawei", "dispacciamento_eur_kwh",
    "cicli", "cpu_medio_s", "cpu_max_s", "piano_max_s", "memoria_max_kb", "scritti_kb", "huawei_chiamate_mango",
    "gme_chiamate", "meteo_chiamate", "github_chiamate_mango", "rete_kb", "rete_s", "fattore_mango",
    "zero_prel_kwh", "zero_imm_kwh", "zero_costo_eur", "zero_ricavo_eur" }
  for _, p in ipairs(profili) do
    for _, x in ipairs({ "prel_kwh", "imm_kwh", "costo_eur", "ricavo_eur", "usura_eur", "auto_costo_eur", "auto_ricavo_eur",
      "auto_usura_eur", "maggiore_acquisto_kwh", "maggiore_acquisto_eur", "maggiore_cessione_kwh", "maggiore_cessione_eur",
      "costo_interventi_eur", "beneficio_eur", "beneficio_con_soc_eur", "soc_fine", "finestre", "comandi", "ottimo_eur", "ottenuto_eur",
      "rimpianto_eur", "reale_costo_eur", "reale_ricavo_eur", "sforamenti_kwh", "ore_soc_alto",
      "beneficio_vs_zero_eur", "auto_vs_zero_eur", "scarica_forzata_kwh" }) do
      c[#c + 1] = p .. "_" .. x
    end
  end
  return c
end

function M.nuovo(c, cartella_ram, cartella_dati)
  local self = { ram = cartella_ram, dati = cartella_dati }
  self.col_dataset = colonne_dataset(c.PROFILI)
  self.col_riepilogo = colonne_riepilogo(c.PROFILI)
  self.col_periodi = COL_PERIODI

  local function buffer(nome) return self.ram .. "/buffer_" .. nome end

  function self.riga_dataset(giorno, valori)
    F.accoda(buffer("dataset_" .. giorno .. ".csv"), F.riga_csv(self.col_dataset, valori))
  end

  function self.riga_periodo(giorno, valori)
    F.accoda(buffer("periodi_" .. giorno .. ".csv"), F.riga_csv(COL_PERIODI, valori))
  end

  -- sposta le righe accumulate in RAM nei file della memoria interna
  function self.svuota()
    for _, nome in ipairs(F.elenco(self.ram, "^buffer_.*%.csv$")) do
      local dest = self.dati .. "/" .. nome:gsub("^buffer_", "")
      local testo = F.leggi(self.ram .. "/" .. nome)
      if testo and #testo > 0 then
        local col = nome:match("^buffer_dataset_") and self.col_dataset or
          (nome:match("^buffer_carico_") and M.COL_CARICO or COL_PERIODI)
        -- file iniziato con colonne diverse (aggiornamento del programma): si mette da parte e se ne inizia uno nuovo
        local intest = F.esiste(dest) and (F.leggi(dest) or ""):match("^([^\n]*)") or nil
        if intest and intest ~= F.intestazione_csv(col):gsub("\n$", "") then
          os.rename(dest, (dest:gsub("%.csv$", "")) .. "_v" .. os.time() .. ".csv")
        end
        if not F.esiste(dest) then
          local col = nome:match("^buffer_dataset_") and self.col_dataset or
            (nome:match("^buffer_carico_") and M.COL_CARICO or COL_PERIODI)
          F.accoda(dest, F.intestazione_csv(col))
        end
        F.accoda(dest, testo)
      end
      os.remove(self.ram .. "/" .. nome)
    end
  end

  -- una riga per giorno: se il giorno e' gia' presente (es. ripristino da backup) la riga viene sostituita
  function self.riga_riepilogo(valori)
    local dest = self.dati .. "/riepilogo.csv"
    local testo = F.leggi(dest)
    if not testo or testo == "" then
      F.scrivi(dest, F.intestazione_csv(self.col_riepilogo) .. F.riga_csv(self.col_riepilogo, valori))
      return
    end
    if testo:match("^([^\n]*)") ~= F.intestazione_csv(self.col_riepilogo):gsub("\n$", "") then
      -- colonne cambiate (aggiornamento del programma): il vecchio riepilogo resta in riepilogo_v1.csv
      os.rename(dest, self.dati .. "/riepilogo_v1.csv")
      F.scrivi(dest, F.intestazione_csv(self.col_riepilogo) .. F.riga_csv(self.col_riepilogo, valori))
      return
    end
    local righe, chiave = {}, tostring(valori.giorno) .. ","
    for riga in testo:gmatch("[^\n]+") do
      if riga:sub(1, #chiave) ~= chiave then righe[#righe + 1] = riga end
    end
    righe[#righe + 1] = (F.riga_csv(self.col_riepilogo, valori):gsub("\n$", ""))
    local intest = table.remove(righe, 1)
    table.sort(righe)
    F.scrivi(dest, intest .. "\n" .. table.concat(righe, "\n") .. "\n")
  end

  return self
end

-- ------------------------------------------------------------------ report giornaliero (Markdown per GitHub)
local function e2(v) return v and string.format("%.2f", v) or "-" end
local function e3(v) return v and string.format("%.3f", v) or "-" end

function M.report(c, r, periodi, note)
  local L = {}
  local g = r.giorno
  L[#L + 1] = string.format("# Report EMS Cismondi - %s/%s/%s (%s)", g:sub(7, 8), g:sub(5, 6), g:sub(1, 4), r.tipo_giorno or "")
  L[#L + 1] = ""
  L[#L + 1] = "**SOLO SIMULAZIONE**: nessun comando inviato all'inverter."
  L[#L + 1] = ""
  L[#L + 1] = "## Scenari"
  L[#L + 1] = ""
  local agg = string.format("perdite %.0f %% su energia e spread, dispacciamento %s, trasporto %.4f, oneri di sistema %.4f, accise %.4f EUR/kWh, IVA %.0f %%",
    c.PERDITE * 100, ((c.DISPACCIAMENTO or 0) > 0) and string.format("%.4f", c.DISPACCIAMENTO) or "NON NOTO (per ora 0)",
    c.TRASPORTO, c.ONERI, c.ACCISE, c.IVA * 100)
  L[#L + 1] = string.format("Prezzo d'acquisto fisso F0: %.2f EUR/kWh di energia, %.4f EUR/kWh con i costi aggiuntivi (%s).",
    c.PREZZO_FISSO_A, PA.costo_da_energia(c, c.PREZZO_FISSO_A), agg)
  L[#L + 1] = ""
  L[#L + 1] = "| Scenario | Descrizione |"
  L[#L + 1] = "|---|---|"
  L[#L + 1] = "| **Senza batteria** | Solo autoconsumo istantaneo del FV: il resto si compra, l'eccedenza si cede. |"
  L[#L + 1] = "| **Automatico** | Batteria in massimo autoconsumo, senza ottimizzatore (come oggi). |"
  for _, p in ipairs(c.PROFILI) do
    L[#L + 1] = string.format("| **%s** - %s | Batteria gestita dall'ottimizzatore%s. |", p, (c.PROFILI_NOME or {})[p] or p,
      ((c.PROFILI_CARICA_RETE or {})[p]) and string.format(", con carica dalla rete fino a %d W di giorno", c.P_MAX_CARICA_RETE_W)
        or ", senza carica dalla rete")
  end
  L[#L + 1] = ""
  L[#L + 1] = string.format("Cessioni (RID): prezzo zonale %s%s%s. ", c.ZONA, c.PREZZI_QUARTO_ORA and " del quarto d'ora" or " orario",
      (c.IMPOSTA_CESSIONI or 0) > 0 and string.format(" meno l'imposta del %.0f %%", c.IMPOSTA_CESSIONI * 100) or "") ..
    string.format("Usura batteria: %.3f EUR per kWh scaricato. ", c.USURA_EUR_KWH or 0) ..
    "Ogni scenario ha la sua batteria simulata e l'ottimizzatore sceglie ogni 15 minuti tra autoconsumo, carica ritardata, " ..
    "carica forzata e scarica forzata a potenze graduate, con al massimo " .. c.MAX_FINESTRE_GIORNO .. " periodi forzati e " ..
    tostring(c.MAX_CICLI_FORZATI_GIORNO or 1) .. " ciclo di scarica forzata al giorno. " ..
    string.format("Ogni cambiamento di funzionamento costa %.2f EUR: si cambia solo se conviene anche pagandolo.", c.PENALITA_CAMBIO_EUR)
  L[#L + 1] = ""
  if (c.DISPACCIAMENTO or 0) == 0 then
    L[#L + 1] = "> Il dispacciamento non e' ancora noto ed e' calcolato a 0: i costi d'acquisto sono sottostimati " ..
      "della stessa quantita' per kWh. I kWh sono registrati nel dataset, quindi i costi si possono ricalcolare quando il valore sara' noto."
    L[#L + 1] = ""
  end
  L[#L + 1] = string.format("Letture: %s, ore integrate: %s. FV %s kWh, consumi casa %s kWh.", tostring(r.letture),
    e2(r.ore_integrate), e2(r.fv_kwh), e2(r.carico_kwh))
  L[#L + 1] = string.format("Reale: prelievo %s kWh, immissione %s kWh.  Solo autoconsumo simulato: prelievo %s kWh, immissione %s kWh.",
    e2(r.reale_prel_kwh), e2(r.reale_imm_kwh), e2(r.auto_prel_kwh), e2(r.auto_imm_kwh))
  L[#L + 1] = string.format("Senza batteria: prelievo %s kWh (%s EUR), immissione %s kWh (%s EUR).",
    e2(r.zero_prel_kwh), e2(r.zero_costo_eur), e2(r.zero_imm_kwh), e2(r.zero_ricavo_eur))
  L[#L + 1] = ""
  L[#L + 1] = "| Profilo | Prelievo kWh | Immissione kWh | Costo EUR | Ricavo EUR | Usura EUR | Cambiamenti (EUR) | Maggiore acquisto kWh (EUR) | Maggiore cessione kWh (EUR) | Beneficio su automatico EUR | Beneficio con SOC EUR | Beneficio su senza batteria EUR | Rimpianto EUR | Finestre |"
  L[#L + 1] = "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
  for _, p in ipairs(c.PROFILI) do
    L[#L + 1] = string.format("| %s | %s | %s | %s | %s | %s | %s (%s) | %s (%s) | %s (%s) | %s | %s | %s | %s | %s |", p,
      e2(r[p .. "_prel_kwh"]), e2(r[p .. "_imm_kwh"]), e2(r[p .. "_costo_eur"]), e2(r[p .. "_ricavo_eur"]), e2(r[p .. "_usura_eur"]),
      tostring(r[p .. "_comandi"] or 0), e2(r[p .. "_costo_interventi_eur"]),
      e2(r[p .. "_maggiore_acquisto_kwh"]), e2(r[p .. "_maggiore_acquisto_eur"]), e2(r[p .. "_maggiore_cessione_kwh"]),
      e2(r[p .. "_maggiore_cessione_eur"]), e2(r[p .. "_beneficio_eur"]), e2(r[p .. "_beneficio_con_soc_eur"]),
      e2(r[p .. "_beneficio_vs_zero_eur"]), e2(r[p .. "_rimpianto_eur"]), tostring(r[p .. "_finestre"] or 0))
  end
  L[#L + 1] = ""
  L[#L + 1] = "Beneficio = costo netto dello scenario solo autoconsumo - costo netto del profilo (stessi prezzi) - costo dei cambiamenti. " ..
    "Con SOC: tiene conto del valore dell'energia rimasta in batteria a fine giornata. " ..
    "Rimpianto = distanza dall'ottimo calcolato a posteriori con i dati veri del giorno."
  L[#L + 1] = ""
  L[#L + 1] = "## Previsioni"
  L[#L + 1] = string.format("Errore medio consumi: sera prima %s W, modello %s W.  FV: sera prima %s W, modello %s W.",
    e2(r.mae_carico_sera_w), e2(r.mae_carico_modello_w), e2(r.mae_fv_sera_w), e2(r.mae_fv_modello_w))
  L[#L + 1] = string.format("Rendimenti usati: carica %s, scarica %s. Ore con SOC reale >= %d %%: %s.", e3(r.eta_carica),
    e3(r.eta_scarica), c.ORE_SOC_ALTO, e2(r.ore_soc_alto_reale))
  L[#L + 1] = ""
  if r.cicli then
    L[#L + 1] = "## Carico di lavoro del Mango"
    local f = c.FATTORE_MANGO
    local function m(x) return f and string.format("%.2f s", x * f) or "da tarare" end
    L[#L + 1] = string.format("Cicli: %s. CPU per ciclo: media %s s, massimo %s s (qui). Calcolo del piano: massimo %s s (qui).",
      tostring(r.cicli), e3(r.cpu_medio_s), e3(r.cpu_max_s), e3(r.piano_max_s))
    L[#L + 1] = string.format("Stima sul Mango: media %s, massimo %s, piano %s%s.", m(r.cpu_medio_s or 0), m(r.cpu_max_s or 0),
      m(r.piano_max_s or 0), f and string.format(" (fattore %.1f misurato con benchmark_mango.lua)", f) or
      " (lanciare benchmark_mango.lua sul Mango e scrivere FATTORE_MANGO in config.lua)")
    L[#L + 1] = string.format("Memoria Lua massima %s kB. Scritture nella memoria interna %s kB al giorno.", e2(r.memoria_max_kb), e2(r.scritti_kb))
    L[#L + 1] = string.format("Chiamate che il Mango farebbe in un giorno: Huawei %s (limite %d), GME %s, meteo %s, GitHub %s; dati ricevuti circa %s kB.",
      tostring(r.huawei_chiamate_mango), c.LIMITE_CHIAMATE_GIORNO, tostring(r.gme_chiamate), tostring(r.meteo_chiamate),
      tostring(r.github_chiamate_mango), e2(r.rete_kb))
    L[#L + 1] = ""
  end
  L[#L + 1] = "## Periodi di carica e scarica forzata (profili)"
  local n = 0
  for _, x in ipairs(periodi or {}) do
    if x.categoria ~= "auto" or x.azione == "RITARDATA" then
      if n == 0 then
        L[#L + 1] = "| Profilo | Inizio | Fine | Azione | SOC | Energia kWh | Motivo |"
        L[#L + 1] = "|---|---|---|---|---|---|---|"
      end
      n = n + 1
      L[#L + 1] = string.format("| %s | %s | %s | %s | %s -> %s | carica %s, scarica %s | %s |", x.profilo, x.inizio:sub(12, 16),
        x.fine:sub(12, 16), x.azione, e2(x.soc_inizio), e2(x.soc_fine), e2((x.carica_fv_kwh or 0) + (x.carica_rete_kwh or 0)),
        e2(x.scarica_kwh), (x.motivo or ""):gsub("|", "/"))
    end
  end
  if n == 0 then L[#L + 1] = "Nessun periodo forzato: tutti i profili sono rimasti in autoconsumo." end
  if note and #note > 0 then
    L[#L + 1] = ""
    L[#L + 1] = "## Segnalazioni"
    for _, x in ipairs(note) do L[#L + 1] = "- " .. x end
  end
  return table.concat(L, "\n") .. "\n"
end

return M
