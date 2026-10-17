-- storico.lua - GIORNO 0: importazione dello storico FusionSolar (dati a 5 minuti) e del meteo storico,
-- addestramento iniziale dei modelli e invio dello storico su GitHub.
-- Ogni giorno passato costa 2 chiamate Huawei (contatore + inverter). Va avanti a ritroso finche' Huawei
-- restituisce dati (3 giorni vuoti di fila = fine dello storico conservato) o fino a STORICO_GIORNI_MAX.
local J = require "lib_json"
local F = require "lib_file"
local T = require "lib_tempo"
local MET = require "meteo"
local MOD = require "modelli"
local M = {}

local COLONNE = { "ts", "fv_w", "inverter_w", "contatore_w", "carico_w" }

local function num(v)
  if type(v) == "number" then return v end
  if type(v) == "string" then return tonumber(v) end
  return nil
end

-- un passo (chiamato a ogni ciclo): ritorna true quando tutto e' finito
function M.passo(c, ctx)
  local st, hw, log = ctx.stato, ctx.huawei, ctx.log
  -- sul Mango lo storico sta in RAM (la memoria interna e' piccola); su GitHub nella memoria persistente
  local cart = os.getenv("EMS_STORICO") or (ctx.cartella_ram .. "/storico")
  F.cartella(cart)
  st.storico = st.storico or { fase = "huawei", giorno = T.giorno(T.adesso(), -1), fatti = 0, vuoti = 0, mesi = {} }
  local s = st.storico
  local inizio = os.time()

  if s.fase == "huawei" then
    while os.time() - inizio < 200 do
      if s.fatti >= c.STORICO_GIORNI_MAX or s.vuoti >= 3 then s.fase = "meteo"; break end
      if not hw.chiamate_disponibili(2) then
        log("Storico: chiamate Huawei di oggi esaurite, riprendo domani (" .. s.fatti .. " giorni importati)")
        return false
      end
      local g = s.giorno
      local m0 = T.mezzanotte(g)
      local ok, cont = pcall(hw.storico_giorno, "contatore", g)
      local ok2, inv = false, nil
      if ok then ok2, inv = pcall(hw.storico_giorno, "inverter", g) end
      if not ok or not ok2 then
        log("Storico: errore il " .. g .. ": " .. tostring(ok and inv or cont))
        s.errori = (s.errori or 0) + 1
        if s.errori >= 5 then log("Storico: troppi errori, passo oltre"); s.fase = "meteo" end
        return false
      end
      local righe, n = {}, 0
      for t, xi in pairs(inv) do
        local xc = cont[t]
        local p_inv = num(xi.active_power)
        local p_cont = xc and num(xc.active_power)
        local fv = num(xi.mppt_power)
        if p_inv and p_cont then
          righe[#righe + 1] = { ts = t, fv_w = fv and math.max(0, fv * 1000), inverter_w = p_inv * 1000,
                                contatore_w = p_cont, carico_w = math.max(0, p_inv * 1000 - p_cont) }
          n = n + 1
        end
      end
      table.sort(righe, function(a, b) return a.ts < b.ts end)
      if n == 0 then s.vuoti = s.vuoti + 1 else s.vuoti = 0 end
      if n > 0 then
        local mese = g:sub(1, 6)
        local f = cart .. "/storico_" .. mese .. ".csv"
        if not F.esiste(f) then F.accoda(f, F.intestazione_csv(COLONNE)) end
        local parti = {}
        for _, r in ipairs(righe) do parti[#parti + 1] = F.riga_csv(COLONNE, r) end
        F.accoda(f, table.concat(parti))
        s.mesi[mese] = true
      end
      s.fatti = s.fatti + 1
      s.giorno = T.giorno(m0 + 43200, -1)
    end
    log(string.format("Storico: %d giorni letti (fino al %s), %d chiamate Huawei oggi", s.fatti, s.giorno,
      st.chiamate_huawei or 0))
    if s.fase == "huawei" then return false end
  end

  if s.fase == "meteo" then
    local imp = st.impianto or {}
    local lat, lon = c.LATITUDINE or imp.lat, c.LONGITUDINE or imp.lon
    if not (lat and lon) then
      log("Storico: coordinate dell'impianto non disponibili: niente meteo storico")
      s.fase = "addestra"
    else
      s.meteo_fatti = s.meteo_fatti or {}
      for mese in pairs(s.mesi) do
        if not s.meteo_fatti[mese] and os.time() - inizio < 200 then
          local a, m = tonumber(mese:sub(1, 4)), tonumber(mese:sub(5, 6))
          local fine_m = (m == 12) and string.format("%04d-12-31", a) or
            os.date("!%Y-%m-%d", T.epoca_utc(a, m + 1, 1) - 86400)
          local ok, serie = pcall(MET.storico, c, lat, lon, string.format("%04d-%02d-01", a, m), fine_m)
          if ok then
            F.scrivi(cart .. "/meteo_" .. mese .. ".json", J.encode(MET.a_testo(serie)))
            s.meteo_fatti[mese] = true
          else
            log("Storico: meteo " .. mese .. " non disponibile: " .. tostring(serie))
            s.meteo_fatti[mese] = "errore"
          end
        end
      end
      local finito = true
      for mese in pairs(s.mesi) do if not s.meteo_fatti[mese] then finito = false end end
      if finito then s.fase = "addestra" else return false end
    end
  end

  if s.fase == "addestra" then
    -- addestramento iniziale: un mese per ciclo, in ordine cronologico
    local mesi = {}
    for mese in pairs(s.mesi) do mesi[#mesi + 1] = mese end
    table.sort(mesi)
    s.addestrati = s.addestrati or {}
    for _, mese in ipairs(mesi) do
      if not s.addestrati[mese] then
        M.addestra_mese(c, ctx, cart, mese)
        s.addestrati[mese] = true
        log("Storico: modelli addestrati con " .. mese)
        return false
      end
    end
    s.fase = "invio"
  end

  if s.fase == "invio" then
    if ctx.github.configurato() then
      for mese in pairs(s.mesi) do
        local f = cart .. "/storico_" .. mese .. ".csv"
        local gz = F.gzip(f)
        if gz then os.remove(f) end
        ctx.github.accoda(gz or f, "storico/storico_" .. mese .. ".csv" .. (gz and ".gz" or ""), true)
        if F.esiste(cart .. "/meteo_" .. mese .. ".json") then
          ctx.github.accoda(cart .. "/meteo_" .. mese .. ".json", "storico/meteo_" .. mese .. ".json", true)
        end
      end
      local seg = ctx.cartella_ram .. "/segnale_storico.json"
      F.scrivi(seg, J.encode({ tipo = "storico", giorni = s.fatti, ts = os.time() }))
      ctx.github.accoda(seg, "segnali/addestra.json")
    end
    s.fase = "finito"
    log(string.format("STORICO COMPLETATO: %d giorni importati. Parte la simulazione.", s.fatti))
    return true
  end
  return s.fase == "finito"
end

-- legge un mese di storico e aggiorna i modelli in ordine cronologico
function M.addestra_mese(c, ctx, cart, mese)
  local testo = F.leggi(cart .. "/storico_" .. mese .. ".csv") or ""
  local righe = {}
  local primo = true
  for riga in testo:gmatch("[^\n]+") do
    if primo then primo = false
    else
      local ts, fv, inv, cont, car = riga:match("^([^,]*),([^,]*),([^,]*),([^,]*),([^,]*)$")
      ts = tonumber(ts)
      if ts and tonumber(car) then
        righe[#righe + 1] = { t = ts, fv_w = tonumber(fv) or 0, inverter_w = tonumber(inv) or 0,
                              contatore_w = tonumber(cont) or 0, carico_w = tonumber(car) }
      end
    end
  end
  table.sort(righe, function(a, b) return a.t < b.t end)
  local mt = F.leggi(cart .. "/meteo_" .. mese .. ".json")
  local serie = mt and MET.da_testo(J.decode(mt)) or nil
  local mod = ctx.modelli
  local giorno_corr, acc = nil, nil
  local function chiudi()
    if giorno_corr and acc and acc.n > 100 then
      local comp = {}
      for q, x in pairs(acc.comp) do comp[q] = x.s / x.n end
      MOD.chiudi_giorno(mod, { g = giorno_corr, tipo = acc.tipo, tmed = (acc.nt > 0) and acc.st / acc.nt or nil,
                               ghi = (acc.ng > 0) and acc.sg / acc.ng or nil, comp = comp,
                               x = acc.nx > 0 and acc.x or nil, n_x = acc.nx, carico_medio = acc.cs / acc.n })
    end
  end
  for _, r in ipairs(righe) do
    local cal = T.calendario(r.t)
    cal.epoca = r.t
    if cal.giorno ~= giorno_corr then
      chiudi()
      giorno_corr = cal.giorno
      acc = { n = 0, comp = {}, tipo = cal.tipo, st = 0, nt = 0, sg = 0, ng = 0, x = { 0, 0, 0, 0, 0 }, nx = 0, cs = 0 }
    end
    local met = serie and MET.istante(serie, r.t) or nil
    local tlag = serie and MET.temp_media(serie, r.t, 3) or nil
    local l = { carico_w = r.carico_w, fv_w = r.fv_w }
    local prev_c, prev_f = MOD.prevedi(mod, c, cal, met, tlag, nil)
    MOD.aggiorna(mod, c, cal, met, tlag, l, { carico = prev_c, fv = prev_f }, nil, nil, nil)
    local x = MOD.caratteristiche(tlag or (met and met.temp), met and met.vento, met and met.ghi)
    local comp_v = math.max(0, r.carico_w - MOD.pompa(mod, c, x))
    local q = cal.quarto_orologio
    acc.comp[q] = acc.comp[q] or { s = 0, n = 0 }
    acc.comp[q].s = acc.comp[q].s + comp_v
    acc.comp[q].n = acc.comp[q].n + 1
    acc.n = acc.n + 1
    acc.cs = acc.cs + r.carico_w
    if met and met.temp then
      for i = 1, 5 do acc.x[i] = acc.x[i] + x[i] end
      acc.nx = acc.nx + 1
    end
    if met and met.temp then acc.st, acc.nt = acc.st + met.temp, acc.nt + 1 end
    if met and met.ghi then acc.sg, acc.ng = acc.sg + met.ghi, acc.ng + 1 end
  end
  chiudi()
  -- la correzione in giornata non deve partire da dati vecchi
  mod.corr = { car = { e = 0, t = 0 }, fv = { r = 1, t = 0 } }
end

return M
