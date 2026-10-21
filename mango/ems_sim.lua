-- ems_sim.lua - SIMULAZIONE EMS Cismondi sul Mango (programma principale)
-- SOLO SIMULAZIONE: legge Huawei, GME e meteo, simula tre profili di ottimizzazione e registra tutto.
-- Non invia alcun comando all'inverter.
--
-- Uso:  lua ems_sim.lua ciclo        (ogni 5 minuti da cron)
--       lua ems_sim.lua autorizza    (una tantum, autorizzazione Huawei)
--       lua ems_sim.lua prova        (controllo: una lettura, prezzi, meteo, tempo dell'ottimizzatore)
--       lua ems_sim.lua stato        (riassunto)
--       lua ems_sim.lua invia        (invia subito su GitHub i file in coda)
local CARTELLA = (arg and arg[0] or ""):match("^(.*)/[^/]*$") or "."
package.path = CARTELLA .. "/?.lua;" .. package.path

local J = require "lib_json"
local F = require "lib_file"
local HT = require "lib_http"
local T = require "lib_tempo"
local HW = require "huawei"
local GME = require "gme"
local MET = require "meteo"
local PA = require "prezzi_acquisto"
local MOD = require "modelli"
local S = require "simulatore"
local O = require "ottimizzatore"
local REG = require "registro"
local GH = require "github"
local STO = require "storico"

local c = dofile(CARTELLA .. "/config.lua")
if F.esiste(CARTELLA .. "/config_locale.lua") then
  for k, v in pairs(dofile(CARTELLA .. "/config_locale.lua")) do c[k] = v end
end
local RAM = c.CARTELLA_RAM
local DATI = c.CARTELLA_DATI or (CARTELLA .. "/dati")
local PREZZI = DATI .. "/prezzi"
F.cartella(RAM); F.cartella(DATI); F.cartella(PREZZI)
F.prefisso_conteggio = DATI .. "/"        -- byte scritti nella memoria interna (usura della flash)

-- ------------------------------------------------------------------ registro testuale
local function log(msg)
  local riga = T.testo(nil) .. "  " .. msg
  print(riga)
  F.accoda(RAM .. "/ems_sim.log", riga .. "\n")
end

-- ------------------------------------------------------------------ stato e modelli (RAM, copia oraria in memoria interna)
local function carica_json(nome)
  local t = F.leggi(RAM .. "/" .. nome) or F.leggi(DATI .. "/" .. nome)
  if not t then return nil end
  local ok, d = pcall(J.decode, t)
  return ok and d or nil
end

local stato = carica_json("stato.json") or { versione = 1 }
local modelli = MOD.normalizza(carica_json("modelli.json") or MOD.nuovo())
stato.sim = stato.sim or {}
stato.meteo = stato.meteo or {}

-- RAM a ogni ciclo; memoria interna: stato ogni ora (senza il meteo, che si riscarica), modelli ogni 6 ore
-- (o quando forza_modelli), per limitare le scritture sulla flash del Mango
local function salva(anche_flash, forza_modelli)
  modelli._cache = nil
  local ts, tm = J.encode(stato), J.encode(modelli)
  F.scrivi(RAM .. "/stato.json", ts)
  F.scrivi(RAM .. "/modelli.json", tm)
  if anche_flash then
    local meteo = stato.meteo
    stato.meteo = nil
    F.scrivi(DATI .. "/stato.json", J.encode(stato))
    stato.meteo = meteo
    local trascorso = T.ora_forzata and (T.adesso() - (stato.flash_modelli_sim or 0)) or (os.time() - (stato.flash_modelli or 0))
    if forza_modelli or trascorso >= 6 * 3600 or trascorso < 0 then
      F.scrivi(DATI .. "/modelli.json", tm)
      stato.flash_modelli, stato.flash_modelli_sim = os.time(), T.adesso()
    end
    local logram = F.leggi(RAM .. "/ems_sim.log")
    if logram then
      F.accoda(DATI .. "/ems_sim.log", logram)
      os.remove(RAM .. "/ems_sim.log")
      local dim = #(F.leggi(DATI .. "/ems_sim.log") or "")
      if dim > 1000000 then os.rename(DATI .. "/ems_sim.log", DATI .. "/ems_sim.log.1") end
    end
  end
end

local hw = HW.nuovo(c, CARTELLA, stato, log)
local gh = GH.nuovo(c, CARTELLA, stato, log)
local reg = REG.nuovo(c, RAM, DATI)
local usura = c.USURA_EUR_KWH or (c.COSTO_BATTERIA_EUR / (c.CICLI_VITA * c.CAPACITA_KWH))

-- ------------------------------------------------------------------ prezzi
local cache_prezzi = {}
local function prezzi_giorno(g, scarica_se_manca)
  local d = GME.carica(PREZZI, g)
  if d or not scarica_se_manca then return d end
  stato.tentativi_prezzi = stato.tentativi_prezzi or {}
  local ult = stato.tentativi_prezzi[g] or 0
  if T.adesso() - ult < 1800 then return nil end
  stato.tentativi_prezzi[g] = T.adesso()
  local ok, r = pcall(GME.scarica, c, CARTELLA, PREZZI, g, log)
  if not ok then log("Prezzi GME del " .. g .. " non scaricati: " .. tostring(r)); return nil end
  PA.aggiungi_giorno(stato, r)
  cache_prezzi[g] = r
  return r
end

local function prezzo_ora(t)
  local cal = T.calendario(t)
  local d = cache_prezzi[cal.giorno]
  if d == nil then
    d = GME.carica(PREZZI, cal.giorno) or false
    if d then cache_prezzi[cal.giorno] = d end
  end
  if not d then return nil end
  local h = d.ore[cal.ora_gme]
  local qq = d.quarti and d.quarti[cal.quarto_gme]
  return h, qq
end

-- prezzo NORD usato per la cessione: quello del quarto d'ora se disponibile (MGP a 15 minuti), altrimenti orario
local function nord_cessione(h, qq)
  if c.PREZZI_QUARTO_ORA and qq and qq.nord then return qq.nord end
  return h and h.nord
end

-- scenario 0: impianto senza batteria (solo autoconsumo istantaneo), potenze medie in W
local function senza_batteria(fv, car)
  local fv_car = math.min(fv, car)
  local imm = math.max(0, math.min(fv - fv_car, c.P_MAX_IMMISSIONE_W, c.P_MAX_AC_INVERTER_W - fv_car))
  return car - fv_car, imm
end

-- accumulatore di un profilo (crea quelli mancanti, es. profili cambiati durante il giorno)
local function acc_profilo(a, p)
  a.prof[p] = a.prof[p] or { prel = 0, imm = 0, sca = 0, costo = 0, ricavo = 0, usura = 0, auto_costo = 0, auto_ricavo = 0,
                             auto_usura = 0, reale_costo = 0, reale_ricavo = 0, sfor = 0, euro = 0, ore_alto = 0 }
  return a.prof[p]
end

-- ------------------------------------------------------------------ meteo
local function serie_meteo() return MET.da_testo(stato.meteo.serie) end

local function aggiorna_meteo(forza)
  local imp = stato.impianto or {}
  local lat, lon = c.LATITUDINE or imp.lat, c.LONGITUDINE or imp.lon
  if not (lat and lon) then return end
  if not forza and stato.meteo.t and T.adesso() - stato.meteo.t < 3300 then return end
  local ok, s = pcall(MET.previsioni, c, lat, lon, log)
  if not ok then log("Meteo non aggiornato: " .. tostring(s)); return end
  -- conserva le ore passate gia' note (osservate) e aggiorna le future
  local vecchia = serie_meteo()
  for t, x in pairs(s) do vecchia[t] = x end
  vecchia = MET.ritaglia(vecchia, T.adesso() - 2 * 86400, T.adesso() + 4 * 86400)
  stato.meteo.serie = MET.a_testo(vecchia)
  stato.meteo.t = T.adesso()
end

-- ------------------------------------------------------------------ previsioni per un istante
local function tmed_giorno(serie, g)
  local m0 = T.mezzanotte(g)
  local s, n = 0, 0
  for h = 0, 23 do
    local x = serie[m0 + h * 3600]
    if x and x.temp then s, n = s + x.temp, n + 1 end
  end
  return (n > 0) and s / n or nil
end

local cache_giorno = {}
local function info_giorno(g, tipo, serie)
  if cache_giorno[g] then return cache_giorno[g] end
  local gh_prev = (modelli.github_prev or {})[g]
  local x = { simili = MOD.simili(modelli, tipo, tmed_giorno(serie, g), g), github = gh_prev }
  cache_giorno[g] = x
  return x
end

-- previsione base (senza correzione in giornata) per l'istante t
local function previsione(t, serie)
  local cal = T.calendario(t)
  cal.epoca = t
  local met = MET.istante(serie, t)
  local tlag = MET.temp_media(serie, t, 3)
  local car, fv, det = MOD.prevedi(modelli, c, cal, met, tlag, info_giorno(cal.giorno, cal.tipo, serie))
  return car, fv, det, cal, met, tlag
end

-- ------------------------------------------------------------------ orizzonte dell'ottimizzatore
local function costruisci_quarti(t0, serie, con_margine)
  local quarti = {}
  local giorno0 = T.giorno(t0)
  local ultimo = prezzi_giorno(T.giorno(t0, 1), false) and T.giorno(t0, 1) or giorno0
  local fine = T.mezzanotte(T.giorno(T.mezzanotte(ultimo) + 43200, 1))
  local carico_ultimo = (stato.lettura_prec or {}).carico_w or 800
  local t = T.inizio_quarto(t0)
  while t < fine do
    local tm = t + 450
    local h, qq = prezzo_ora(tm)
    if not h then break end
    local car, fv, _, cal = previsione(tm, serie)
    car = car or carico_ultimo
    fv = fv or 0
    car, fv = MOD.correggi(modelli, tm, car, fv)
    if con_margine then
      local sc, sf = MOD.sigma(modelli, cal.ora)
      local met = MET.istante(serie, tm) or {}
      local disp_meteo = (met.ghi_disp or 0) / 1000 * c.P_NOMINALE_FV_W * 0.8
      car = car + c.MARGINE_Z * sc
      fv = math.max(0, fv - c.MARGINE_Z * math.sqrt((sf * math.max(fv, 500)) ^ 2 + disp_meteo ^ 2))
    end
    local costi = PA.costi(c, stato, tm, h.pun)
    quarti[#quarti + 1] = { t = t, giorno = cal.giorno, fv = fv, carico = car, di_giorno = fv >= c.FV_MIN_GIORNO_W,
      mezzanotte = (t == T.mezzanotte(cal.giorno)), vend = PA.valore_cessione(c, nord_cessione(h, qq)), costo = costi }
    t = t + 900
  end
  return quarti
end

-- valore dell'energia a fine orizzonte: costo medio d'acquisto per i kWh che serviranno nella notte successiva
-- (dalla fine dell'orizzonte fino a quando il FV previsto torna a coprire i consumi, al massimo 14 ore)
local function valore_fine(quarti, serie)
  local v = {}
  local e_notte
  if serie and #quarti > 0 then
    local t = quarti[#quarti].t + 900
    e_notte = 0
    for _ = 1, 56 do
      local car, fv = previsione(t + 450, serie)
      car, fv = car or 800, fv or 0
      if fv >= car and fv > c.FV_MIN_GIORNO_W then break end
      e_notte = e_notte + math.max(0, car - fv) * 0.25 / 1000
      t = t + 900
    end
  end
  for _, p in ipairs(c.PROFILI) do
    local s, sv = 0, 0
    for _, q in ipairs(quarti) do s, sv = s + q.costo[p], sv + q.vend end
    local n = #quarti
    v[p] = { costo = (n > 0) and s / n or PA.costo_da_energia(c, c.PREZZO_FISSO_A),
             vend = (n > 0) and sv / n or 0, e_notte = e_notte }
  end
  return v
end

-- ------------------------------------------------------------------ accumulatori giornalieri
local function nuovo_accumulo(g)
  local a = { giorno = g, letture = 0, ore = 0, fv = 0, carico = 0, reale = { prel = 0, imm = 0 },
              zero = { prel = 0, imm = 0, costo = 0, ricavo = 0 },
              auto = { prel = 0, imm = 0, sca = 0 }, quarti = {}, comp = {}, err = { cs = 0, cn = 0, fs = 0, fn = 0, ms = 0, mn = 0, mfs = 0, mfn = 0 },
              soc_inizio = {}, prof = {}, chiamate = 0 }
  for _, p in ipairs(c.PROFILI) do
    a.prof[p] = { prel = 0, imm = 0, sca = 0, costo = 0, ricavo = 0, usura = 0, auto_costo = 0, auto_ricavo = 0,
                  auto_usura = 0, reale_costo = 0, reale_ricavo = 0, sfor = 0, euro = 0, ore_alto = 0 }
    a.soc_inizio[p] = (stato.sim[p] or {}).soc
  end
  a.soc_inizio.auto = (stato.sim.auto or {}).soc
  return a
end

-- chiusura di un periodo di un profilo (registro dei periodi)
local function chiudi_periodo(p, t_fine)
  local s = stato.sim[p]
  local per = s and s.periodo
  if not per then return end
  local durata = (t_fine - per.inizio) / 60
  if durata > 0 then
    local giorno = T.giorno(per.inizio)
    local x = { profilo = p, inizio = T.calendario(per.inizio).iso, fine = T.calendario(t_fine).iso, durata_min = durata,
      azione = per.azione, categoria = S.categoria(per.azione), motivo = per.motivo, soc_inizio = per.soc0, soc_fine = s.soc,
      carica_fv_kwh = per.cfv, carica_rete_kwh = per.crete, scarica_kwh = per.sca, prelievo_kwh = per.prel,
      immissione_kwh = per.imm, nord_medio = (per.n > 0) and per.nord / per.n or nil,
      costo_medio = (per.n > 0) and per.costo / per.n or nil, euro_netto = per.euro }
    reg.riga_periodo(giorno, x)
    stato.periodi_giorno = stato.periodi_giorno or {}
    stato.periodi_giorno[giorno] = stato.periodi_giorno[giorno] or {}
    table.insert(stato.periodi_giorno[giorno], x)
  end
  s.periodo = nil
end

local function apri_periodo(p, t, azione, motivo)
  local s = stato.sim[p]
  s.periodo = { inizio = t, azione = azione, motivo = motivo, soc0 = s.soc, cfv = 0, crete = 0, sca = 0, prel = 0,
                imm = 0, nord = 0, costo = 0, n = 0, euro = 0 }
end

-- ------------------------------------------------------------------ chiusura del giorno
local function chiudi_giorno(g)
  local a = stato.accumulo
  if not a or a.giorno ~= g then return end
  local fine = T.mezzanotte(T.giorno(T.mezzanotte(g) + 43200, 1))
  for _, p in ipairs(c.PROFILI) do
    if stato.sim[p] and stato.sim[p].periodo then
      local az, mot = stato.sim[p].periodo.azione, stato.sim[p].periodo.motivo
      chiudi_periodo(p, fine)
      apri_periodo(p, fine, az, mot)
    end
  end
  reg.svuota()
  -- ottimo a posteriori con i dati veri del giorno (stesso SOC iniziale)
  local prezzi = GME.carica(PREZZI, g)
  local quarti = {}
  if prezzi then
    local m0 = T.mezzanotte(g)
    for k = 1, T.ore_del_giorno(g) * 4 do
      local qd = a.quarti[tostring(k)]
      if not qd or qd.n == 0 then quarti = nil; break end
      local tm = m0 + (k - 1) * 900 + 450
      local h = prezzi.ore[math.floor((k - 1) / 4) + 1]
      local qq = prezzi.quarti and prezzi.quarti[k]
      quarti[k] = { t = m0 + (k - 1) * 900, giorno = g, fv = qd.fv / qd.n, carico = qd.car / qd.n,
        di_giorno = qd.fv / qd.n >= c.FV_MIN_GIORNO_W, mezzanotte = (k == 1), vend = PA.valore_cessione(c, nord_cessione(h, qq)),
        costo = PA.costi(c, stato, tm, h.pun) }
    end
  else
    quarti = nil
  end
  local r = { giorno = g, tipo_giorno = T.calendario(T.mezzanotte(g) + 43200).tipo, letture = a.letture, ore_integrate = a.ore,
    fv_kwh = a.fv, carico_kwh = a.carico, reale_prel_kwh = a.reale.prel, reale_imm_kwh = a.reale.imm,
    auto_prel_kwh = a.auto.prel, auto_imm_kwh = a.auto.imm, auto_soc_fine = (stato.sim.auto or {}).soc,
    mae_carico_sera_w = (a.err.cn > 0) and a.err.cs / a.err.cn or nil, mae_fv_sera_w = (a.err.fn > 0) and a.err.fs / a.err.fn or nil,
    mae_carico_modello_w = (a.err.mn > 0) and a.err.ms / a.err.mn or nil, mae_fv_modello_w = (a.err.mfn > 0) and a.err.mfs / a.err.mfn or nil,
    ore_soc_alto_reale = a.ore_alto_reale, chiamate_huawei = stato.chiamate_huawei, dispacciamento_eur_kwh = c.DISPACCIAMENTO }
  local e = MOD.efficienze(modelli, c)
  r.eta_carica, r.eta_scarica = e.c, e.d
  local note = {}
  local vf = quarti and valore_fine(quarti, serie_meteo()) or nil
  local ott
  if quarti and #quarti > 0 then
    local prof_in = {}
    for _, p in ipairs(c.PROFILI) do
      prof_in[p] = { soc0 = a.soc_inizio[p] or 50, prev_azione = "AUTO", finestre_oggi = 0, giorno_oggi = g,
                     carica_rete = (c.PROFILI_CARICA_RETE or {})[p] }
    end
    local ok, res = pcall(O.pianifica, c, e, quarti, c.PROFILI, prof_in, usura, vf)
    if ok then ott = res else log("Ottimo a posteriori non calcolato: " .. tostring(res)) end
  else
    note[#note + 1] = "Ottimo a posteriori non calcolato: dati del giorno incompleti (letture mancanti in qualche quarto d'ora)."
  end
  local z = a.zero or { prel = 0, imm = 0, costo = 0, ricavo = 0 }
  r.zero_prel_kwh, r.zero_imm_kwh, r.zero_costo_eur, r.zero_ricavo_eur = z.prel, z.imm, z.costo, z.ricavo
  for _, p in ipairs(c.PROFILI) do
    local x = acc_profilo(a, p)
    local s = stato.sim[p] or {}
    r[p .. "_prel_kwh"], r[p .. "_imm_kwh"] = x.prel, x.imm
    r[p .. "_beneficio_vs_zero_eur"] = (z.costo - z.ricavo) - (x.costo - x.ricavo + x.usura) - (x.interventi or 0)
    r[p .. "_auto_vs_zero_eur"] = (z.costo - z.ricavo) - (x.auto_costo - x.auto_ricavo + x.auto_usura)
    r[p .. "_scarica_forzata_kwh"] = s.scarica_forzata_oggi or 0
    r[p .. "_costo_eur"], r[p .. "_ricavo_eur"], r[p .. "_usura_eur"] = x.costo, x.ricavo, x.usura
    r[p .. "_auto_costo_eur"], r[p .. "_auto_ricavo_eur"], r[p .. "_auto_usura_eur"] = x.auto_costo, x.auto_ricavo, x.auto_usura
    r[p .. "_maggiore_acquisto_kwh"] = x.prel - a.auto.prel
    r[p .. "_maggiore_acquisto_eur"] = x.costo - x.auto_costo
    r[p .. "_maggiore_cessione_kwh"] = x.imm - a.auto.imm
    r[p .. "_maggiore_cessione_eur"] = x.ricavo - x.auto_ricavo
    r[p .. "_costo_interventi_eur"] = x.interventi or 0
    r[p .. "_beneficio_eur"] = (x.auto_costo - x.auto_ricavo + x.auto_usura) - (x.costo - x.ricavo + x.usura) - (x.interventi or 0)
    local vk = vf and vf[p].costo or PA.costo_da_energia(c, c.PREZZO_FISSO_A)
    local val_kwh = math.max(0, (vk - usura) * S.eta_scarica(e, 1000))
    r[p .. "_beneficio_con_soc_eur"] = r[p .. "_beneficio_eur"] +
      (((s.soc or 0) - ((stato.sim.auto or {}).soc or 0)) / 100 * c.CAPACITA_KWH * val_kwh)
    r[p .. "_soc_fine"] = s.soc
    r[p .. "_finestre"], r[p .. "_comandi"] = s.finestre_oggi or 0, s.comandi_oggi or 0
    r[p .. "_reale_costo_eur"], r[p .. "_reale_ricavo_eur"] = x.reale_costo, x.reale_ricavo
    r[p .. "_sforamenti_kwh"], r[p .. "_ore_soc_alto"] = x.sfor, x.ore_alto
    if ott and ott[p] then
      local soc_ini = a.soc_inizio[p] or 50
      local ottimo = ott[p].valore_piano + math.max(0, (ott[p].soc_fine - c.SOC_MIN)) / 100 * c.CAPACITA_KWH * val_kwh
      local ottenuto = (x.ricavo - x.costo - x.usura - (x.interventi or 0)) + math.max(0, ((s.soc or soc_ini) - c.SOC_MIN)) / 100 * c.CAPACITA_KWH * val_kwh
      r[p .. "_ottimo_eur"], r[p .. "_ottenuto_eur"], r[p .. "_rimpianto_eur"] = ottimo, ottenuto, ottimo - ottenuto
    end
    if x.sfor > 0.01 then note[#note + 1] = string.format("Profilo %s: %.2f kWh oltre il prelievo massimo di %d W.", p, x.sfor, c.P_MAX_PRELIEVO_W) end
  end
  if (c.DISPACCIAMENTO or 0) == 0 then note[#note + 1] = "Dispacciamento non noto (calcolato a 0): inserirlo in config.lua quando disponibile." end
  local k = a.lavoro
  if k and k.cicli > 0 then
    r.cicli, r.cpu_medio_s, r.cpu_max_s, r.piano_max_s = k.cicli, k.cpu / k.cicli, k.cpu_max, k.piano_max
    r.memoria_max_kb, r.scritti_kb = k.mem_max, k.scritti / 1024
    local camp = stato.campione_lettura
    r.huawei_chiamate_mango, r.gme_chiamate, r.meteo_chiamate, r.github_chiamate_mango = k.hw, k.gme, k.meteo, k.gh
    -- dati ricevuti: quelli reali piu', per le letture rigiocate dallo storico, la dimensione misurata di una lettura reale
    r.rete_kb = (k.byte + ((camp and camp.byte) or 0) / 3 * (k.hw_sim or 0)) / 1024
    r.rete_s, r.fattore_mango = k.rete_s, c.FATTORE_MANGO
  end
  reg.riga_riepilogo(r)
  -- giorni simili: comportamento medio per quarto d'ora del giorno chiuso
  local comp = {}
  for q, x in pairs(a.comp) do if x.n > 0 then comp[tonumber(q)] = x.s / x.n end end
  local serie = serie_meteo()
  MOD.chiudi_giorno(modelli, { g = g, tipo = r.tipo_giorno, tmed = tmed_giorno(serie, g), comp = comp,
    x = (a.nx or 0) > 0 and a.xs or nil, n_x = a.nx, carico_medio = (a.ore > 0) and a.carico * 1000 / a.ore or nil })
  -- report e invio
  local cart_g = DATI .. "/giorni/" .. g
  F.cartella(cart_g)
  local periodi = (stato.periodi_giorno or {})[g] or {}
  F.scrivi(cart_g .. "/report.md", REG.report(c, r, periodi, note))
  F.scrivi(cart_g .. "/modelli_mango.json", J.encode(modelli))
  local remoto = "dati/" .. g:sub(1, 4) .. "-" .. g:sub(5, 6) .. "-" .. g:sub(7, 8) .. "/"
  local function invia_se(locale, nome, comprimi)
    if not F.esiste(locale) then return end
    local f = locale
    if comprimi then
      local gz = F.gzip(locale)
      if gz then f = gz; nome = nome .. ".gz" end
    end
    gh.accoda(f, remoto .. nome)
  end
  invia_se(DATI .. "/dataset_" .. g .. ".csv", "dataset.csv", true)
  invia_se(DATI .. "/periodi_" .. g .. ".csv", "periodi.csv", false)
  invia_se(DATI .. "/carico_" .. g .. ".csv", "carico_mango.csv", true)
  invia_se(DATI .. "/piano_sera_" .. g .. ".csv", "piano_sera.csv", false)
  invia_se(DATI .. "/meteo_previsto_" .. g .. ".csv", "meteo_previsto.csv", false)
  invia_se(PREZZI .. "/prezzi_" .. g .. ".json", "prezzi.json", false)
  invia_se(cart_g .. "/report.md", "report.md", false)
  invia_se(cart_g .. "/modelli_mango.json", "modelli_mango.json", false)
  gh.accoda(DATI .. "/riepilogo.csv", "riepilogo.csv")
  F.scrivi(cart_g .. "/README_ultimo.md", REG.report(c, r, periodi, note))
  gh.accoda(cart_g .. "/README_ultimo.md", "ULTIMO_REPORT.md")
  stato.giorni_completati = (stato.giorni_completati or 0) + 1
  if stato.giorni_completati == c.DURATA_PROVA_GIORNI and not stato.fine_prova then
    F.scrivi(cart_g .. "/FINE_PROVA.md", "# Fine dei " .. c.DURATA_PROVA_GIORNI .. " giorni di prova\n\nUltimo giorno: " .. g ..
      "\n\nIl riepilogo completo e' in riepilogo.csv; i dati di ogni giorno sono nella cartella dati/.\n" ..
      "La simulazione continua: per fermarla togliere la riga di ems_sim.lua da /etc/crontabs/root.\n")
    gh.accoda(cart_g .. "/FINE_PROVA.md", "FINE_PROVA.md")
    stato.fine_prova = true
    log("FINE PROVA: " .. c.DURATA_PROVA_GIORNI .. " giorni completati, file finali in coda per GitHub")
  end
  local seg = RAM .. "/segnale_giorno.json"
  F.scrivi(seg, J.encode({ tipo = "giorno", giorno = g, ts = T.adesso() }))
  gh.accoda(seg, "segnali/addestra.json")
  -- pulizia (il CSV non compresso resta finche' non c'e' la copia compressa)
  if F.esiste(DATI .. "/dataset_" .. g .. ".csv.gz") then os.remove(DATI .. "/dataset_" .. g .. ".csv") end
  for _, nome in ipairs(F.elenco(DATI, "^dataset_%d+%.csv$")) do
    if nome < "dataset_" .. T.giorno(T.mezzanotte(g) + 43200, -10) then os.remove(DATI .. "/" .. nome) end
  end
  if stato.periodi_giorno then stato.periodi_giorno[g] = nil end
  for _, nome in ipairs(F.elenco(DATI, "^dataset_%d+%.csv%.gz$")) do
    if nome < "dataset_" .. T.giorno(T.mezzanotte(g) + 43200, -10) then os.remove(DATI .. "/" .. nome) end
  end
  for _, nome in ipairs(F.elenco(PREZZI, "^grezzo_")) do
    if nome < "grezzo_" .. T.giorno(T.mezzanotte(g) + 43200, -3) then os.remove(PREZZI .. "/" .. nome) end
  end
  for _, p in ipairs(c.PROFILI) do
    local sp = stato.sim[p]
    if sp then
      -- un periodo forzato che continua dopo mezzanotte conta come nuova finestra del nuovo giorno
      sp.finestre_oggi = (S.categoria(sp.azione or "AUTO") ~= "auto") and 1 or 0
      sp.comandi_oggi = 0
      sp.scarica_forzata_oggi = 0
    end
  end
  if stato.prev_sera then
    for k in pairs(stato.prev_sera) do if k <= g then stato.prev_sera[k] = nil end end
  end
  stato.flash_modelli, stato.flash_modelli_sim = 0, 0      -- al prossimo salvataggio i modelli vanno in memoria interna
  local parti = {}
  for _, p in ipairs(c.PROFILI) do
    parti[#parti + 1] = string.format("%s %.2f EUR (rispetto a senza batteria %.2f EUR)", p, r[p .. "_beneficio_eur"] or 0,
      r[p .. "_beneficio_vs_zero_eur"] or 0)
  end
  log("Giorno " .. g .. " chiuso: beneficio rispetto all'automatico " .. table.concat(parti, ", "))
end

-- ------------------------------------------------------------------ istantanea della sera (piano e meteo del giorno dopo)
local function istantanea_sera(domani, quarti, ris, serie)
  local righe = { "profilo,inizio,azione,soc,fv_w,carico_w,prelievo_w,immissione_w,euro\n" }
  for _, p in ipairs(c.PROFILI) do
    for _, x in ipairs(ris[p].piano) do
      if T.giorno(x.t) == domani then
        righe[#righe + 1] = F.riga_csv({ "profilo", "inizio", "azione", "soc", "fv_w", "carico_w", "prelievo_w", "immissione_w", "euro" },
          { profilo = p, inizio = T.calendario(x.t).iso, azione = x.azione, soc = x.soc, fv_w = x.fv, carico_w = x.carico,
            prelievo_w = x.prelievo_w, immissione_w = x.immissione_w, euro = x.euro })
      end
    end
  end
  F.scrivi(DATI .. "/piano_sera_" .. domani .. ".csv", table.concat(righe))
  -- previsioni della sera (senza margine) per il controllo dell'errore del giorno dopo
  stato.prev_sera = stato.prev_sera or {}
  local pv = {}
  local m0 = T.mezzanotte(domani)
  local mrow = { "inizio,temp_c,umidita,nuvole,ghi_wm2,vento,pioggia,ghi_disp,temp_disp,n_modelli,prev_carico_w,prev_fv_w\n" }
  for k = 1, T.ore_del_giorno(domani) * 4 do
    local tm = m0 + (k - 1) * 900 + 450
    local car, fv = previsione(tm, serie)
    pv[tostring(k)] = { carico = car, fv = fv }
    if (k - 1) % 4 == 0 then
      local met = MET.istante(serie, tm) or {}
      mrow[#mrow + 1] = F.riga_csv({ "inizio", "temp", "umid", "nuvole", "ghi", "vento", "pioggia", "ghi_disp", "temp_disp", "n_modelli", "car", "fv" },
        { inizio = T.calendario(m0 + (k - 1) * 900).iso, temp = met.temp, umid = met.umid, nuvole = met.nuvole, ghi = met.ghi,
          vento = met.vento, pioggia = met.pioggia, ghi_disp = met.ghi_disp, temp_disp = met.temp_disp, n_modelli = met.n_modelli,
          car = car, fv = fv })
    end
  end
  stato.prev_sera[domani] = pv
  F.scrivi(DATI .. "/meteo_previsto_" .. domani .. ".csv", table.concat(mrow))
  stato.istantanea_sera = domani
  log("Piano della sera per " .. domani .. " salvato")
end

-- richiesta delle previsioni a GitHub (modello completo addestrato la')
local function richiedi_previsioni_github(domani, serie)
  if not gh.configurato() then return end
  local m0 = T.mezzanotte(domani)
  local q = {}
  for k = 1, T.ore_del_giorno(domani) * 4 do
    local tm = m0 + (k - 1) * 900 + 450
    local cal = T.calendario(tm)
    local met = MET.istante(serie, tm) or {}
    q[k] = { q = k, ts = m0 + (k - 1) * 900, quarto_orologio = cal.quarto_orologio, ora = cal.ora, tipo_giorno = cal.tipo,
             settimana = cal.settimana, mese = cal.mese, temp = met.temp, temp_lag3h = MET.temp_media(serie, tm, 3),
             umidita = met.umid, nuvole = met.nuvole, ghi = met.ghi, vento = met.vento, ghi_disp = met.ghi_disp }
  end
  local f = RAM .. "/richiesta_" .. domani .. ".json"
  F.scrivi(f, J.encode({ giorno = domani, generato_il = T.adesso(), quarti = q }))
  gh.accoda(f, "richieste/richiesta_" .. domani .. ".json")
  local seg = RAM .. "/segnale_richiesta.json"
  F.scrivi(seg, J.encode({ tipo = "previsione", giorno = domani, ts = T.adesso() }))
  gh.accoda(seg, "segnali/addestra.json")
  stato.github.richiesta = domani
  log("Richiesta delle previsioni di " .. domani .. " inviata a GitHub")
end

local function controlla_github()
  if not gh.configurato() then return end
  stato.github = stato.github or {}
  local adesso = T.adesso()
  -- previsioni richieste
  local dom = stato.github.richiesta
  -- si controlla ogni 15 minuti finche' le previsioni non sono accettate, ma solo prima dell'inizio di quel giorno
  if dom and not (modelli.github_prev or {})[dom] and adesso < T.mezzanotte(dom)
     and adesso - (stato.github.ultimo_controllo_prev or 0) >= 900 then
    stato.github.ultimo_controllo_prev = adesso
    local ok, cont = pcall(gh.leggi, "previsioni/prev_" .. dom .. ".json")
    if ok and cont then
      local ok2, d = pcall(J.decode, cont)
      if ok2 and d.accettato and d.giorno == dom then
        local car, fv = {}, {}
        for k, v in pairs(d.carico_w or {}) do car[tonumber(k)] = tonumber(v) end
        for k, v in pairs(d.fv_w or {}) do fv[tonumber(k)] = tonumber(v) end
        modelli.github_prev = modelli.github_prev or {}
        modelli.github_prev[dom] = { carico = car, fv = fv }
        cache_giorno[dom] = nil
        log("Previsioni di GitHub per " .. dom .. " ricevute e accettate")
      elseif ok2 and d.giorno == dom then
        modelli.github_prev = modelli.github_prev or {}
        if modelli.github_prev[dom] == nil then
          log("Previsioni di GitHub per " .. dom .. " non accettate (" .. tostring(d.motivo) .. "): uso le mie")
        end
        modelli.github_prev[dom] = false
      end
    end
  end
  -- coefficienti nuovi (una volta al giorno dopo le 4)
  local ora = T.italia(adesso).hour
  if ora >= 4 and stato.github.giorno_modelli ~= T.giorno(adesso) then
    stato.github.giorno_modelli = T.giorno(adesso)
    local ok, cont, sha = pcall(gh.leggi, "modelli/coefficienti_mango.json")
    if ok and cont and sha ~= stato.github.sha_modelli then
      local ok2, d = pcall(J.decode, cont)
      if ok2 then
        local applicato, info = MOD.applica_github(modelli, d)
        log("Coefficienti da GitHub: " .. (applicato and ("applicati, " .. info) or ("non applicati: " .. info)))
        stato.github.sha_modelli = sha
      end
    end
  end
  -- pulizia previsioni vecchie
  for g in pairs(modelli.github_prev or {}) do
    if g < T.giorno(adesso, -2) then modelli.github_prev[g] = nil end
  end
end

-- ------------------------------------------------------------------ CICLO
local function ciclo()
  local adesso = T.adesso()
  if tonumber(os.date("!%Y", adesso)) < 2026 then log("Orologio del Mango non sincronizzato: ciclo saltato"); return end
  local oggi = T.giorno(adesso)
  if stato.giorno_chiamate ~= oggi then stato.giorno_chiamate, stato.chiamate_huawei = oggi, 0 end
  stato.github = stato.github or {}

  -- GIORNO 0: storico
  if stato.fase ~= "simulazione" then
    stato.fase = "storico"
    local ok, imp = pcall(hw.impianto)
    if not ok then log("Huawei non raggiungibile: " .. tostring(imp)); return end
    local ok2, finito = pcall(STO.passo, c, { stato = stato, huawei = hw, log = log, cartella_dati = DATI,
      cartella_ram = RAM, modelli = modelli, github = gh })
    if not ok2 then log("Storico: errore " .. tostring(finito)) end
    if ok2 and finito then stato.fase = "simulazione"; stato.avvio_simulazione = adesso end
    gh.invia_coda(10)
    salva(true, true)
    return
  end

  -- cambio di giorno
  if stato.giorno and stato.giorno ~= oggi then
    local ok, err = pcall(chiudi_giorno, stato.giorno)
    if not ok then log("Chiusura del giorno " .. stato.giorno .. " non riuscita: " .. tostring(err)) end
    stato.accumulo = nil
  end
  stato.giorno = oggi
  stato.accumulo = stato.accumulo or nuovo_accumulo(oggi)
  local acc = stato.accumulo

  -- prezzi di oggi e (dalle 13:30) di domani
  local p_oggi = prezzi_giorno(oggi, true)
  local ora_dec = T.italia(adesso).hour + T.italia(adesso).min / 60
  local domani = T.giorno(adesso, 1)
  local p_domani = prezzi_giorno(domani, ora_dec >= c.ORA_PREZZI)
  if p_oggi then PA.aggiungi_giorno(stato, p_oggi) end
  if p_domani then PA.aggiungi_giorno(stato, p_domani) end

  -- meteo e lettura dell'impianto
  aggiorna_meteo(false)
  local serie = serie_meteo()
  local l
  if hw.chiamate_disponibili(3) then
    local ok, r = pcall(hw.leggi)
    if ok then l = r; l.t = adesso else log("Lettura Huawei non riuscita: " .. tostring(r)) end
  else
    log("Limite giornaliero di chiamate Huawei raggiunto: lettura saltata")
  end

  local riga = {}
  local cal = T.calendario(adesso)
  cal.epoca = adesso
  riga.ts, riga.data_ora, riga.giorno, riga.ora, riga.minuto = adesso, cal.iso, cal.giorno, cal.ora, cal.minuto
  riga.quarto_gme, riga.ora_gme, riga.settimana, riga.tipo_giorno, riga.fascia, riga.mese =
    cal.quarto_gme, cal.ora_gme, cal.settimana, cal.tipo, cal.fascia, cal.mese
  riga.chiamate_huawei = stato.chiamate_huawei
  local e = MOD.efficienze(modelli, c)
  riga.eta_carica, riga.eta_scarica = e.c, e.d
  riga.eta_inv_500, riga.eta_inv_1000, riga.eta_inv_2000, riga.eta_inv_oltre = e.inv[1], e.inv[2], e.inv[3], e.inv[4]
  riga.fonte_rendimenti = "carica " .. e.fonte.c .. ", scarica " .. e.fonte.d

  -- previsione per adesso (prima di aggiornare i modelli)
  local p_car, p_fv, det, _, met, tlag = previsione(adesso, serie)
  local pc_corr, pf_corr = MOD.correggi(modelli, adesso, p_car, p_fv)
  local ps = ((stato.prev_sera or {})[oggi] or {})[tostring(cal.quarto_gme)]
  met = met or {}
  riga.temp_c, riga.temp_lag3h_c, riga.umidita, riga.nuvole, riga.ghi_wm2, riga.vento, riga.pioggia =
    met.temp, tlag, met.umid, met.nuvole, met.ghi, met.vento, met.pioggia
  riga.ghi_disp, riga.temp_disp, riga.n_modelli_meteo = met.ghi_disp, met.temp_disp, met.n_modelli
  riga.prev_carico_w, riga.prev_fv_w, riga.prev_carico_corr_w, riga.prev_fv_corr_w = p_car, p_fv, pc_corr, pf_corr
  riga.prev_carico_sera_w, riga.prev_fv_sera_w = ps and ps.carico, ps and ps.fv
  riga.fonte_prev, riga.pdc_stima_w, riga.comportamento_w, riga.coef_fv, riga.cielo =
    det.fonte, det.pdc, det.comportamento, det.coef_fv, det.cielo
  riga.sigma_carico_w, riga.sigma_fv_rel = MOD.sigma(modelli, cal.ora)

  local h, qq = prezzo_ora(adesso)
  if h then
    riga.nord, riga.pun = h.nord, h.pun
    local costi = PA.costi(c, stato, adesso, h.pun)
    riga.costo_acquisto = costi[c.PROFILI[1]]
    riga.valore_cessione = PA.valore_cessione(c, nord_cessione(h, qq))
  end
  if qq then riga.nord_15, riga.pun_15 = qq.nord, qq.pun end
  riga.usura = usura

  local prec = stato.lettura_prec
  riga.qualita = l and "ok" or "lettura mancante"
  riga.integrato = 0
  if l then
    riga.fv_w, riga.carico_w, riga.inverter_w, riga.batteria_w, riga.soc, riga.contatore_w =
      l.fv_w, l.carico_w, l.inverter_w, l.batteria_w, l.soc, l.contatore_w
    riga.prelievo_w, riga.immissione_w = math.max(0, -l.contatore_w), math.max(0, l.contatore_w)
    riga.modo_reale_cod, riga.modo_reale, riga.stato_batteria_cod, riga.stato_batteria = l.modo_cod, l.modo, l.stato_batt_cod, l.stato_batt
    if p_car then riga.err_carico_w = l.carico_w - p_car end
    if p_fv then riga.err_fv_w = l.fv_w - p_fv end
    -- inizializzazione dei SOC simulati dal SOC reale (prima lettura)
    stato.sim.auto = stato.sim.auto or { soc = l.soc }
    for _, p in ipairs(c.PROFILI) do
      if not stato.sim[p] then
        stato.sim[p] = { soc = l.soc, azione = "AUTO", motivo = "avvio", finestre_oggi = 0, comandi_oggi = 0 }
        apri_periodo(p, adesso, "AUTO", "avvio")
      end
      acc.soc_inizio[p] = acc.soc_inizio[p] or stato.sim[p].soc
    end
    acc.soc_inizio.auto = acc.soc_inizio.auto or stato.sim.auto.soc
  end

  -- integrazione dell'intervallo [prec, adesso]
  if l and prec and prec.t and adesso > prec.t then
    local dt_s = adesso - prec.t
    riga.dt_s = dt_s
    if dt_s <= c.BUCO_MAX_MIN * 60 then
      riga.integrato = 1
      local dt = dt_s / 3600
      local fv = (l.fv_w + prec.fv_w) / 2
      local car = (l.carico_w + prec.carico_w) / 2
      local tm = prec.t + dt_s / 2
      local hm, qm = prezzo_ora(tm)
      if not hm then hm, qm = h, qq end
      local costi = hm and PA.costi(c, stato, tm, hm.pun) or nil
      local vend = hm and PA.valore_cessione(c, nord_cessione(hm, qm)) or 0
      local di_giorno = fv >= c.FV_MIN_GIORNO_W
      acc.letture, acc.ore, acc.fv, acc.carico = acc.letture + 1, acc.ore + dt, acc.fv + fv * dt / 1000, acc.carico + car * dt / 1000
      local cont = (l.contatore_w + prec.contatore_w) / 2
      local rp, ri = math.max(0, -cont) * dt / 1000, math.max(0, cont) * dt / 1000
      acc.reale.prel, acc.reale.imm = acc.reale.prel + rp, acc.reale.imm + ri
      riga.reale_prel_kwh, riga.reale_imm_kwh, riga.reale_ricavo_eur = rp, ri, ri * vend
      if l.soc >= c.ORE_SOC_ALTO then acc.ore_alto_reale = (acc.ore_alto_reale or 0) + dt end
      -- quarti d'ora reali (per l'ottimo a posteriori) e comportamento per i giorni simili
      local cm = T.calendario(tm)
      local kq = tostring(cm.quarto_gme)
      acc.quarti[kq] = acc.quarti[kq] or { fv = 0, car = 0, n = 0 }
      acc.quarti[kq].fv, acc.quarti[kq].car, acc.quarti[kq].n = acc.quarti[kq].fv + fv, acc.quarti[kq].car + car, acc.quarti[kq].n + 1
      local kc = tostring(cm.quarto_orologio)
      acc.comp[kc] = acc.comp[kc] or { s = 0, n = 0 }
      acc.comp[kc].s, acc.comp[kc].n = acc.comp[kc].s + math.max(0, car - (det.pdc or 0)), acc.comp[kc].n + 1
      if met and met.temp then
        local xx = MOD.caratteristiche(tlag or met.temp, met.vento, met.ghi)
        acc.xs = acc.xs or { 0, 0, 0, 0, 0 }
        for i = 1, 5 do acc.xs[i] = acc.xs[i] + xx[i] end
        acc.nx = (acc.nx or 0) + 1
      end
      -- scenario solo autoconsumo
      local fa = S.passo(c, e, stato.sim.auto.soc, "AUTO", fv, car, dt, di_giorno)
      stato.sim.auto.soc = fa.soc
      riga.auto_soc, riga.auto_batteria_w = fa.soc, fa.batteria_w
      for _, f in ipairs(REG.FLUSSI) do riga["auto_" .. f .. "_w"] = fa[f .. "_w"] end
      riga.auto_tagliato_w, riga.auto_sforamento_w = fa.fv_tagliato_w, fa.sforamento_w
      riga.auto_prel_kwh, riga.auto_imm_kwh, riga.auto_scarica_kwh = fa.prelievo_w * dt / 1000, fa.immissione_w * dt / 1000, fa.scarica_w * dt / 1000
      acc.auto.prel, acc.auto.imm, acc.auto.sca = acc.auto.prel + riga.auto_prel_kwh, acc.auto.imm + riga.auto_imm_kwh, acc.auto.sca + riga.auto_scarica_kwh
      -- scenario 0: senza batteria (stesso prezzo d'acquisto del primo profilo)
      local zp, zi = senza_batteria(fv, car)
      local zc = costi and costi[c.PROFILI[1]] or 0
      acc.zero = acc.zero or { prel = 0, imm = 0, costo = 0, ricavo = 0 }
      riga.zero_prel_kwh, riga.zero_imm_kwh = zp * dt / 1000, zi * dt / 1000
      riga.zero_costo_eur, riga.zero_ricavo_eur = riga.zero_prel_kwh * zc, riga.zero_imm_kwh * vend
      acc.zero.prel, acc.zero.imm = acc.zero.prel + riga.zero_prel_kwh, acc.zero.imm + riga.zero_imm_kwh
      acc.zero.costo, acc.zero.ricavo = acc.zero.costo + riga.zero_costo_eur, acc.zero.ricavo + riga.zero_ricavo_eur
      -- profili
      for _, p in ipairs(c.PROFILI) do
        local s = stato.sim[p]
        local fp = S.passo(c, e, s.soc, s.azione, fv, car, dt, di_giorno)
        s.soc = fp.soc
        if S.categoria(s.azione) == "scarica" then s.scarica_forzata_oggi = (s.scarica_forzata_oggi or 0) + fp.scarica_w * dt / 1000 end
        local x = acc_profilo(acc, p)
        local e_prel, e_imm, e_sca = fp.prelievo_w * dt / 1000, fp.immissione_w * dt / 1000, fp.scarica_w * dt / 1000
        local cp = costi and costi[p] or 0
        local costo, ricavo, us = e_prel * cp, e_imm * vend, e_sca * usura
        local ac, ar, au = riga.auto_prel_kwh * cp, riga.auto_imm_kwh * vend, riga.auto_scarica_kwh * usura
        x.prel, x.imm, x.sca = x.prel + e_prel, x.imm + e_imm, x.sca + e_sca
        x.costo, x.ricavo, x.usura = x.costo + costo, x.ricavo + ricavo, x.usura + us
        x.auto_costo, x.auto_ricavo, x.auto_usura = x.auto_costo + ac, x.auto_ricavo + ar, x.auto_usura + au
        x.reale_costo, x.reale_ricavo = x.reale_costo + rp * cp, x.reale_ricavo + ri * vend
        x.sfor = x.sfor + fp.sforamento_w * dt / 1000
        if fp.soc >= c.ORE_SOC_ALTO then x.ore_alto = x.ore_alto + dt end
        riga[p .. "_azione"], riga[p .. "_categoria"], riga[p .. "_soc"], riga[p .. "_batteria_w"] = s.azione, S.categoria(s.azione), fp.soc, fp.batteria_w
        for _, f in ipairs(REG.FLUSSI) do riga[p .. "_" .. f .. "_w"] = fp[f .. "_w"] end
        riga[p .. "_tagliato_w"], riga[p .. "_sforamento_w"] = fp.fv_tagliato_w, fp.sforamento_w
        riga[p .. "_prel_kwh"], riga[p .. "_imm_kwh"], riga[p .. "_scarica_kwh"] = e_prel, e_imm, e_sca
        riga[p .. "_costo_eur"], riga[p .. "_ricavo_eur"], riga[p .. "_usura_eur"] = costo, ricavo, us
        riga[p .. "_auto_costo_eur"], riga[p .. "_auto_ricavo_eur"], riga[p .. "_auto_usura_eur"] = ac, ar, au
        riga[p .. "_reale_costo_eur"] = rp * cp
        riga[p .. "_beneficio_eur"] = (ac - ar + au) - (costo - ricavo + us)
        riga[p .. "_ore_soc_alto"] = x.ore_alto
        local per = s.periodo
        if per then
          per.cfv, per.crete, per.sca = per.cfv + fp.fv_batt_w * dt / 1000, per.crete + fp.rete_batt_w * dt / 1000, per.sca + e_sca
          per.prel, per.imm, per.euro = per.prel + e_prel, per.imm + e_imm, per.euro + (ricavo - costo - us)
          per.nord, per.costo, per.n = per.nord + (hm and hm.nord or 0), per.costo + cp, per.n + 1
        end
      end
      -- errori di previsione del giorno
      if ps and ps.carico then acc.err.cs, acc.err.cn = acc.err.cs + math.abs(l.carico_w - ps.carico), acc.err.cn + 1 end
      if ps and ps.fv then acc.err.fs, acc.err.fn = acc.err.fs + math.abs(l.fv_w - ps.fv), acc.err.fn + 1 end
      if p_car then acc.err.ms, acc.err.mn = acc.err.ms + math.abs(l.carico_w - p_car), acc.err.mn + 1 end
      if p_fv then acc.err.mfs, acc.err.mfn = acc.err.mfs + math.abs(l.fv_w - p_fv), acc.err.mfn + 1 end
      -- apprendimento
      MOD.aggiorna(modelli, c, cal, met, tlag, l, { carico = p_car, fv = p_fv }, ps, dt, prec)
    else
      riga.qualita = "buco di " .. math.floor(dt_s / 60) .. " minuti (non integrato)"
    end
  end
  riga.ore_soc_alto_reale = acc.ore_alto_reale
  if l then stato.lettura_prec = { t = adesso, fv_w = l.fv_w, carico_w = l.carico_w, batteria_w = l.batteria_w,
                                   soc = l.soc, contatore_w = l.contatore_w, inverter_w = l.inverter_w } end

  -- decisione ogni quarto d'ora
  local chiave_q = oggi .. "-" .. cal.quarto_gme
  if stato.sim.auto and stato.quarto_deciso ~= chiave_q and p_oggi then
    local t1 = os.clock()
    local quarti = costruisci_quarti(adesso, serie, true)
    if #quarti > 0 then
      local prof_in = {}
      for _, p in ipairs(c.PROFILI) do
        local s = stato.sim[p]
        prof_in[p] = { soc0 = s.soc, prev_azione = s.azione, finestre_oggi = s.finestre_oggi or 0, giorno_oggi = oggi,
                       carica_rete = (c.PROFILI_CARICA_RETE or {})[p], scarica_forzata_oggi = s.scarica_forzata_oggi or 0 }
      end
      local ok, ris = pcall(O.pianifica, c, e, quarti, c.PROFILI, prof_in, usura, valore_fine(quarti, serie))
      if ok then
        stato.quarto_deciso = chiave_q
        for _, p in ipairs(c.PROFILI) do
          local s = stato.sim[p]
          local nuova = ris[p].primo.azione
          local alt = ris[p].primo.alternative or {}
          local v_auto = alt.AUTO
          local motivo = string.format("piano %.2f EUR fino a fine prezzi; %s", ris[p].valore_piano,
            v_auto and string.format("vantaggio su AUTO %.3f EUR", (alt[nuova] or 0) - v_auto) or "")
          if ris[p].troncato then motivo = motivo .. " (limitato: max " .. c.MAX_FINESTRE_GIORNO .. " finestre e " ..
            (c.MAX_CICLI_FORZATI_GIORNO or 1) .. " ciclo di scarica forzata al giorno)" end
          riga[p .. "_decisione"], riga[p .. "_motivo"] = nuova, motivo
          riga[p .. "_vantaggio_eur"] = v_auto and ((alt[nuova] or 0) - v_auto) or nil
          riga[p .. "_valore_piano_eur"] = ris[p].valore_piano
          if nuova ~= s.azione then
            local cat_n, cat_v = S.categoria(nuova), S.categoria(s.azione)
            if cat_n ~= "auto" and cat_n ~= cat_v then s.finestre_oggi = (s.finestre_oggi or 0) + 1 end
            s.comandi_oggi = (s.comandi_oggi or 0) + 1
            acc_profilo(acc, p).interventi = (acc_profilo(acc, p).interventi or 0) + c.PENALITA_CAMBIO_EUR
            riga[p .. "_costo_interventi_eur"] = c.PENALITA_CAMBIO_EUR
            chiudi_periodo(p, T.inizio_quarto(adesso))
            apri_periodo(p, T.inizio_quarto(adesso), nuova, motivo)
            s.azione = nuova
          end
          s.motivo = motivo
          riga[p .. "_finestre_oggi"], riga[p .. "_comandi_oggi"] = s.finestre_oggi, s.comandi_oggi
        end
        stato.ultimo_piano_s = os.clock() - t1
        stato._piano_ciclo = stato.ultimo_piano_s
        -- istantanea della sera: quando ci sono i prezzi di domani, dopo l'arrivo delle previsioni GitHub o alle 21
        if p_domani and stato.istantanea_sera ~= domani then
          if stato.github.richiesta ~= domani and gh.configurato() then richiedi_previsioni_github(domani, serie) end
          local gh_ok = (modelli.github_prev or {})[domani] ~= nil
          if gh_ok or ora_dec >= c.ORA_LIMITE_PREVISIONI_GITHUB or not gh.configurato() then
            istantanea_sera(domani, quarti, ris, serie)
          end
        end
      else
        log("Ottimizzatore non riuscito: " .. tostring(ris))
      end
    end
  end
  reg.riga_dataset(oggi, riga)

  -- ogni ora: memoria interna, GitHub
  local ora_k = oggi .. T.italia(adesso).hour
  controlla_github()
  if stato.ultimo_flush ~= ora_k then
    reg.svuota()
    gh.invia_coda(25)
    stato.ultimo_flush = ora_k
    salva(true)
  else
    salva(false)
  end
end

-- ------------------------------------------------------------------ carico di lavoro (misurato a ogni ciclo)
local COL_CARICO = { "ts", "data_ora", "cpu_s", "memoria_kb", "scritti_byte", "piano_s", "huawei_reali", "huawei_equivalenti",
  "gme", "meteo", "github_reali", "github_equivalenti", "byte_ricevuti", "secondi_rete" }

local function copia_stat()
  local t = {}
  for k, v in pairs(HT.stat) do t[k] = { n = v.n, ricevuti = v.ricevuti, secondi = v.secondi } end
  return t
end

local function ciclo_misurato()
  local cpu0, scr0, st0 = os.clock(), F.scritti, copia_stat()
  local eq0 = stato.chiamate_equivalenti or 0
  local gheq0 = (stato.github_equivalenti or { n = 0 }).n
  stato._piano_ciclo = nil
  local ok, err = pcall(ciclo)
  if not ok then log("ERRORE nel ciclo: " .. tostring(err)) end
  local function d(sv, campo) return ((HT.stat[sv] or {})[campo] or 0) - ((st0[sv] or {})[campo] or 0) end
  local ricevuti, secondi = 0, 0
  for sv in pairs(HT.stat) do ricevuti, secondi = ricevuti + d(sv, "ricevuti"), secondi + d(sv, "secondi") end
  local hw_eq = (stato.chiamate_equivalenti or 0) - eq0
  local riga = { ts = T.adesso(), data_ora = T.calendario(T.adesso()).iso, cpu_s = os.clock() - cpu0,
    memoria_kb = collectgarbage("count"), scritti_byte = F.scritti - scr0, piano_s = stato._piano_ciclo,
    huawei_reali = d("huawei", "n"), huawei_equivalenti = (hw_eq > 0) and hw_eq or d("huawei", "n"),
    gme = d("gme", "n"), meteo = d("meteo", "n"), github_reali = d("github", "n"),
    github_equivalenti = ((stato.github_equivalenti or { n = 0 }).n - gheq0) + d("github", "n"),
    byte_ricevuti = ricevuti, secondi_rete = secondi }
  stato._piano_ciclo = nil
  if stato.fase == "simulazione" and stato.accumulo then
    local a = stato.accumulo
    a.lavoro = a.lavoro or { cicli = 0, cpu = 0, cpu_max = 0, piano_max = 0, mem_max = 0, scritti = 0, hw = 0, gme = 0,
                             meteo = 0, gh = 0, byte = 0, rete_s = 0 }
    local k = a.lavoro
    k.cicli = k.cicli + 1
    k.cpu, k.cpu_max = k.cpu + riga.cpu_s, math.max(k.cpu_max, riga.cpu_s)
    k.piano_max = math.max(k.piano_max, riga.piano_s or 0)
    k.mem_max = math.max(k.mem_max, riga.memoria_kb)
    k.scritti = k.scritti + riga.scritti_byte
    k.hw, k.gme, k.meteo, k.gh = k.hw + riga.huawei_equivalenti, k.gme + riga.gme, k.meteo + riga.meteo, k.gh + riga.github_equivalenti
    k.hw_sim = (k.hw_sim or 0) + math.max(0, hw_eq)
    k.byte, k.rete_s = k.byte + riga.byte_ricevuti, k.rete_s + riga.secondi_rete
    F.accoda(RAM .. "/buffer_carico_" .. a.giorno .. ".csv", F.riga_csv(COL_CARICO, riga))
  end
  return ok
end

-- ------------------------------------------------------------------ comandi
local comando = arg and arg[1] or "ciclo"
local blocco = RAM .. "/in_corso.lock"

if comando == "ciclo" then
  local b = F.leggi(blocco)
  if b and os.time() - (tonumber(b) or 0) < 900 then os.exit(0) end
  F.scrivi(blocco, tostring(os.time()))
  local ok = ciclo_misurato()
  if not ok then pcall(salva, false) end
  pcall(salva, false)
  os.remove(blocco)
elseif comando == "github" then
  -- MODALITA' GITHUB: rigioca, ciclo per ciclo, le letture a 5 minuti dello storico Huawei come farebbe il Mango
  local inizio_run = os.time()
  local repo = os.getenv("EMS_REPO_DIR")
  if repo and not F.esiste(DATI .. "/riepilogo.csv") and F.esiste(repo .. "/riepilogo.csv") then
    F.scrivi(DATI .. "/riepilogo.csv", F.leggi(repo .. "/riepilogo.csv"))
    log("Riepilogo recuperato dal repository")
  end
  -- fattore di conversione dei tempi: misure/benchmark_mango.txt (prova sul Mango) / misure/benchmark_github.txt
  if not c.FATTORE_MANGO and os.getenv("EMS_REPO_DIR") then
    local function totale(nome)
      local t = F.leggi(os.getenv("EMS_REPO_DIR") .. "/misure/" .. nome)
      return t and tonumber(t:match("totale%s+([%d%.]+)%s*s"))
    end
    local tm, tg = totale("benchmark_mango.txt"), totale("benchmark_github.txt")
    if tm and tg and tg > 0 then c.FATTORE_MANGO = tm / tg end
  end
  local ora_reale = tonumber(os.getenv("EMS_ORA_REALE") or "") or os.time()     -- (prove: orario simulato)
  if stato.fase ~= "simulazione" then
    -- giorno 0: piu' cicli di seguito, ma ci si ferma se un ciclo non fa progressi (errore, rete, limite chiamate)
    local function firma()
      local st = stato.storico or {}
      local n = 0
      for _ in pairs(st.addestrati or {}) do n = n + 1 end
      return table.concat({ tostring(stato.fase), tostring(st.fase), tostring(st.fatti), tostring(n),
                            tostring(st.meteo_fatti and #st.meteo_fatti or 0) }, "|")
    end
    for _ = 1, 40 do
      if stato.fase == "simulazione" or os.time() - inizio_run >= 1500 then break end
      T.ora_forzata = nil
      local prima = firma()
      local ok = ciclo_misurato()
      if not ok or firma() == prima then break end
      if stato.fase ~= "simulazione" and not hw.chiamate_disponibili(2) then break end
    end
    stato.ultimo_rigiocato = nil
  end
  if stato.fase == "simulazione" then
    local fine = math.floor((ora_reale - c.RITARDO_STORICO_MIN * 60) / 300) * 300
    local da = stato.ultimo_rigiocato or (fine - 7200)
    if fine - da > 3 * 86400 then
      log("Recupero limitato agli ultimi 3 giorni")
      da = fine - 3 * 86400
    end
    if fine > da then
      local ok, letture = pcall(hw.finestra_storico, da, fine)
      if ok then
        local n = 0
        for _ in pairs(letture) do n = n + 1 end
        log(string.format("GitHub: rigioco %s -> %s (%d letture dallo storico)", T.testo(da), T.testo(fine), n))
        hw.sorgente = letture
        local t = da + 300
        while t <= fine do
          T.ora_forzata = t
          ciclo_misurato()
          t = t + 300
        end
        hw.sorgente = nil
        T.ora_forzata = nil
        stato.ultimo_rigiocato = fine
        -- campione in tempo reale (3 chiamate): misura tempi e dimensioni delle letture che farebbe il Mango
        local s0 = copia_stat()
        local okc = pcall(hw.leggi)
        local st = HT.stat.huawei or {}
        if okc then
          stato.campione_lettura = { byte = (st.ricevuti or 0) - ((s0.huawei or {}).ricevuti or 0),
                                     secondi = (st.secondi or 0) - ((s0.huawei or {}).secondi or 0), ts = os.time() }
        end
      else
        log("Storico Huawei non disponibile: " .. tostring(letture))
      end
    end
  end
  T.ora_forzata = nil
  reg.svuota()
  gh.invia_coda(200)
  salva(true, true)
elseif comando == "autorizza" then
  local ok, err = pcall(hw.autorizza)
  if not ok then print("ERRORE: " .. tostring(err)); os.exit(1) end
  local ok2, imp = pcall(hw.impianto)
  if ok2 then print("Impianto trovato: " .. imp.codice .. "  coordinate " .. tostring(imp.lat) .. ", " .. tostring(imp.lon)) end
  salva(true, true)
elseif comando == "prova" then
  print("== PROVA ==")
  local ok, imp = pcall(hw.impianto)
  print("Huawei impianto: " .. (ok and (imp.codice .. " coordinate " .. tostring(imp.lat) .. ", " .. tostring(imp.lon)) or tostring(imp)))
  local ok2, l = pcall(hw.leggi)
  if ok2 then
    print(string.format("Lettura: FV %.0f W, casa %.0f W, batteria %.0f W, SOC %s %%, contatore %.0f W, modo %s, stato %s",
      l.fv_w, l.carico_w, l.batteria_w, tostring(l.soc), l.contatore_w, tostring(l.modo), tostring(l.stato_batt)))
  else print("Lettura Huawei: " .. tostring(l)) end
  local okp, p = pcall(GME.scarica, c, CARTELLA, PREZZI, T.giorno(nil), function(m) print(m) end)
  print("GME oggi: " .. (okp and (#p.ore .. " ore") or tostring(p)))
  if okp then PA.aggiungi_giorno(stato, p) end
  aggiorna_meteo(true)
  local n = 0
  for _ in pairs(stato.meteo.serie or {}) do n = n + 1 end
  print("Meteo: " .. n .. " ore in memoria")
  print("GitHub: " .. (gh.configurato() and "token presente" or "token MANCANTE (file github.token)"))
  if gh.configurato() then
    local okg, err = pcall(gh.leggi, "README.md")
    print("GitHub lettura README.md: " .. (okg and "ok" or tostring(err)))
  end
  if okp then
    local t1 = os.clock()
    local quarti = costruisci_quarti(T.adesso(), serie_meteo(), true)
    local prof_in = {}
    local soc0 = ok2 and l.soc or 50
    for _, pp in ipairs(c.PROFILI) do prof_in[pp] = { soc0 = soc0, prev_azione = "AUTO", finestre_oggi = 0, giorno_oggi = T.giorno(nil),
      carica_rete = (c.PROFILI_CARICA_RETE or {})[pp] } end
    local e = MOD.efficienze(modelli, c)
    local okr, ris = pcall(O.pianifica, c, e, quarti, c.PROFILI, prof_in, usura, valore_fine(quarti, serie_meteo()))
    print(string.format("Ottimizzatore: %d quarti d'ora in %.1f s (%s)", #quarti, os.clock() - t1,
      okr and ("prima azione " .. c.PROFILI[1] .. " " .. ris[c.PROFILI[1]].primo.azione) or tostring(ris)))
  end
  print("Memoria interna libera: " .. tostring(F.spazio_libero_kb(DATI)) .. " kB")
  salva(true, true)
elseif comando == "stato" then
  print("Fase: " .. tostring(stato.fase) .. "  giorni completati: " .. tostring(stato.giorni_completati or 0))
  if stato.storico then print("Storico: " .. tostring(stato.storico.fase) .. ", " .. tostring(stato.storico.fatti) .. " giorni") end
  print("Chiamate Huawei oggi: " .. tostring(stato.chiamate_huawei))
  for _, p in ipairs(c.PROFILI) do
    local s = stato.sim[p]
    if s then print(string.format("Profilo %s: SOC %.1f %%, azione %s, finestre %d, comandi %d", p, s.soc, s.azione,
      s.finestre_oggi or 0, s.comandi_oggi or 0)) end
  end
  if stato.sim.auto then print(string.format("Solo autoconsumo: SOC %.1f %%", stato.sim.auto.soc)) end
  print("File in coda per GitHub: " .. #((stato.github or {}).coda or {}))
  print("Ultimo calcolo del piano: " .. tostring(stato.ultimo_piano_s) .. " s")
elseif comando == "invia" then
  reg.svuota()
  gh.invia_coda(100)
  salva(true, true)
else
  print("Comandi: ciclo | autorizza | prova | stato | invia")
end
