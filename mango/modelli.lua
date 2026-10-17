-- modelli.lua - modelli ad autoapprendimento sul Mango (leggeri)
--
-- CONSUMI = comportamento + pompa di calore
--   comportamento: profilo per quarto d'ora dell'orologio e tipo di giorno (feriale, ponte, sabato, domenica,
--                  festivo), media pesata che si aggiorna a ogni lettura; per il giorno dopo si usano i "giorni
--                  simili" (stesso gruppo di giorni, temperatura media vicina, piu' recenti).
--   pompa di calore: regressione sui dati GIORNALIERI (minimi quadrati ricorsivi, un punto per giorno):
--                  consumo medio del giorno = livello del tipo di giorno + gradi sotto 18 C (con l'inerzia: media
--                  delle ultime 3 ore) + il loro quadrato (la resa cala col freddo) + vento e sole + gradi sopra 24 C.
--                  A livello giornaliero la pompa e il comportamento si separano bene; i coefficienti si applicano
--                  poi a ogni quarto d'ora. Segni vincolati (il sole riduce, freddo e vento aumentano).
--                  Limitata a P_MAX_POMPA_CALORE_W.
-- FV = irraggiamento orizzontale (pannelli a 5 gradi) / 1000 x 11 kW x coefficiente imparato per ora e cielo
-- CORREZIONE IN GIORNATA: lo scarto delle ultime letture corregge le ore successive (si attenua col tempo)
-- MARGINE: errore medio delle previsioni per ora del giorno (consumi in W, FV in frazione)
-- RENDIMENTI: carica/scarica batteria da SOC ed energia misurati; inverter in scarica di notte per potenza
local M = {}
local exp, max, min, abs = math.exp, math.max, math.min, math.abs

local TB_RISC, TB_RAFF, ORE_INERZIA = 18, 24, 3
local GRUPPO = { feriale = "lavoro", ponte = "lavoro", sabato = "sabato", domenica = "festa", festivo = "festa" }
local TIPI = { "feriale", "ponte", "sabato", "domenica", "festivo" }
local N_FEAT = 5

local IDX_GRUPPO = { lavoro = 1, sabato = 2, festa = 3 }

function M.nuovo()
  return {
    versione = 3,
    profili = {},                          -- profili[tipo][q] = { v = W, n = letture }
    theta = { 120, 0, 0, 0, 80 },          -- iniziale (IPOTESI): 120 W per grado sotto 18 C, 80 W per grado sopra 24 C
    livelli = { 800, 800, 800 },           -- consumo medio senza pompa per gruppo di giorni
    n_giorni_reg = 0,
    giorni = {},                           -- storico giornaliero per i giorni simili
    fv_coef = {},                          -- fv_coef[ora][classe] = { v =, n = }
    fv_prof = {},                          -- profilo FV per quarto d'ora (riserva se manca il meteo)
    corr = { car = { e = 0, t = 0 }, fv = { r = 1, t = 0 } },
    sig = { car = {}, fv = {} },
    eff = { seg = nil, car = { e_in = 0, imm = 0 }, sca = { e_out = 0, tolta = 0 }, inv = {} },
    ore_soc_alto = 0,
    github = {},
  }
end

-- dopo la lettura da JSON: chiavi numeriche ripristinate (il JSON le salva come testo)
local function chiavi_numeriche(t)
  if type(t) ~= "table" then return t end
  local out = {}
  for k, v in pairs(t) do out[tonumber(k) or k] = v end
  return out
end

function M.normalizza(mod)
  local base = M.nuovo()
  if (mod.versione or 1) < 3 then mod.P, mod.livelli, mod.versione = nil, base.livelli, 3 end
  for k, v in pairs(base) do if mod[k] == nil then mod[k] = v end end
  for tipo, p in pairs(mod.profili) do mod.profili[tipo] = chiavi_numeriche(p) end
  for ora, h in pairs(mod.fv_coef) do mod.fv_coef[ora] = chiavi_numeriche(h) end
  mod.fv_prof = chiavi_numeriche(mod.fv_prof)
  for _, d in ipairs(mod.giorni) do d.comp = chiavi_numeriche(d.comp); d.xm = d.xm end
  for g, x in pairs(mod.github_prev or {}) do
    if type(x) == "table" then x.carico = chiavi_numeriche(x.carico); x.fv = chiavi_numeriche(x.fv) end
  end
  mod._cache = nil
  return mod
end

-- ------------------------------------------------------------------ pompa di calore
function M.caratteristiche(temp_lag, vento, ghi)
  temp_lag = temp_lag or TB_RISC
  local hdd = max(0, TB_RISC - temp_lag)
  return { hdd, hdd * hdd / 10, hdd * (vento or 0) / 10, hdd * (ghi or 0) / 1000, max(0, temp_lag - TB_RAFF) }
end

function M.pompa(mod, c, x)
  local s = 0
  for i = 1, N_FEAT do s = s + (mod.theta[i] or 0) * x[i] end
  return max(0, min(c.P_MAX_POMPA_CALORE_W, s))
end

-- stima della pompa di calore sui dati giornalieri: minimi quadrati pesati (giorni recenti contano di piu'),
-- con una leggera regolarizzazione e vincoli di segno (una caratteristica con segno sbagliato viene esclusa)
local function risolvi(A, b)
  local n = #b
  local M2 = {}
  for i = 1, n do
    M2[i] = {}
    for j = 1, n do M2[i][j] = A[i][j] end
    M2[i][n + 1] = b[i]
  end
  for k = 1, n do
    local piv, r = 0, k
    for i = k, n do if abs(M2[i][k]) > piv then piv, r = abs(M2[i][k]), i end end
    if piv < 1e-12 then return nil end
    M2[k], M2[r] = M2[r], M2[k]
    for i = k + 1, n do
      local f = M2[i][k] / M2[k][k]
      for j = k, n + 1 do M2[i][j] = M2[i][j] - f * M2[k][j] end
    end
  end
  local x = {}
  for i = n, 1, -1 do
    local s = M2[i][n + 1]
    for j = i + 1, n do s = s - M2[i][j] * x[j] end
    x[i] = s / M2[i][i]
  end
  return x
end

local SEGNO = { 1, 1, 1, -1, 1 }        -- freddo, freddo^2, freddo x vento, freddo x sole (riduce), caldo

function M.stima_pompa(mod)
  local dati = {}
  for _, d in ipairs(mod.giorni) do
    if d.carico_medio and d.xm then dati[#dati + 1] = d end
  end
  if #dati < 10 then return false end
  local attive = { true, true, true, true, true }
  for _ = 1, 6 do
    local idx = { 1, 2, 3 }                       -- livelli dei tre gruppi di giorni
    for i = 1, N_FEAT do if attive[i] then idx[#idx + 1] = 3 + i end end
    local n = #idx
    local A, b = {}, {}
    for i = 1, n do A[i] = {}; b[i] = 0; for j = 1, n do A[i][j] = 0 end end
    for k, d in ipairs(dati) do
      local w = 0.99 ^ (#dati - k)
      local x = { 0, 0, 0 }
      x[IDX_GRUPPO[GRUPPO[d.tipo] or "lavoro"]] = 1
      for i = 1, N_FEAT do x[3 + i] = d.xm[i] end
      for i = 1, n do
        b[i] = b[i] + w * x[idx[i]] * d.carico_medio
        for j = 1, n do A[i][j] = A[i][j] + w * x[idx[i]] * x[idx[j]] end
      end
    end
    for i = 4, n do A[i][i] = A[i][i] + 1.0 end    -- regolarizzazione leggera sulle caratteristiche
    for i = 1, 3 do A[i][i] = A[i][i] + 1e-6 end   -- un gruppo senza giorni non blocca il calcolo
    local th = risolvi(A, b)
    if not th then return false end
    local sbagliato = false
    for i = 4, n do
      local f = idx[i] - 3
      if th[i] * SEGNO[f] < 0 then attive[f] = false; sbagliato = true end
    end
    if not sbagliato then
      local nuovo = { 0, 0, 0, 0, 0 }
      for i = 4, n do nuovo[idx[i] - 3] = th[i] end
      mod.theta = nuovo
      for i = 1, 3 do mod.livelli[i] = th[i] end
      mod.n_giorni_reg = #dati
      return true
    end
  end
  return false
end

-- ------------------------------------------------------------------ comportamento
local function profilo(mod, tipo, q)
  local p = mod.profili[tipo]
  if p and p[q] and p[q].n >= 3 then return p[q].v end
  for _, t2 in ipairs(TIPI) do                       -- stesso gruppo, poi qualunque tipo
    if GRUPPO[t2] == GRUPPO[tipo] and mod.profili[t2] and mod.profili[t2][q] and mod.profili[t2][q].n >= 3 then
      return mod.profili[t2][q].v
    end
  end
  for _, t2 in ipairs(TIPI) do
    if mod.profili[t2] and mod.profili[t2][q] and mod.profili[t2][q].n >= 1 then return mod.profili[t2][q].v end
  end
  return nil
end

-- giorni simili: media pesata del comportamento dei giorni dello stesso gruppo piu' simili
function M.simili(mod, tipo, tmed, giorno)
  mod._cache = mod._cache or {}
  local chiave = giorno .. tipo .. string.format("%.0f", tmed or 99)
  if mod._cache[chiave] then return mod._cache[chiave] end
  local cand = {}
  for _, d in ipairs(mod.giorni) do
    if GRUPPO[d.tipo] == GRUPPO[tipo] and d.g < giorno and d.comp then
      local eta = 0
      local a, m, g = tonumber(giorno:sub(1, 4)), tonumber(giorno:sub(5, 6)), tonumber(giorno:sub(7, 8))
      local a2, m2, g2 = tonumber(d.g:sub(1, 4)), tonumber(d.g:sub(5, 6)), tonumber(d.g:sub(7, 8))
      eta = abs((a * 372 + m * 31 + g) - (a2 * 372 + m2 * 31 + g2))
      local dist = abs((tmed or d.tmed or 0) - (d.tmed or tmed or 0)) / 3 + eta / 30 + (d.tipo == tipo and 0 or 0.5)
      cand[#cand + 1] = { d = d, dist = dist }
    end
  end
  if #cand < 3 then mod._cache[chiave] = false; return false end
  table.sort(cand, function(x, y) return x.dist < y.dist end)
  local out = {}
  for q = 1, 96 do
    local s, w = 0, 0
    for k = 1, min(5, #cand) do
      local v = cand[k].d.comp[q]
      if v then
        local p = 1 / (0.5 + cand[k].dist)
        s, w = s + v * p, w + p
      end
    end
    out[q] = (w > 0) and s / w or nil
  end
  mod._cache[chiave] = out
  return out
end

-- ------------------------------------------------------------------ FV
local function classe_cielo(nuvole)
  if not nuvole then return 2 end
  if nuvole < 30 then return 1 elseif nuvole < 70 then return 2 else return 3 end
end

local function coef_fv(mod, ora, cls)
  local h = mod.fv_coef[tostring(ora)]
  if h and h[cls] and h[cls].n >= 6 then return h[cls].v end
  if h then
    local s, n = 0, 0
    for k = 1, 3 do if h[k] and h[k].n > 0 then s, n = s + h[k].v * h[k].n, n + h[k].n end end
    if n >= 3 then return s / n end
  end
  local s, n = 0, 0
  for _, hh in pairs(mod.fv_coef) do
    for k = 1, 3 do if hh[k] and hh[k].n > 0 then s, n = s + hh[k].v * hh[k].n, n + hh[k].n end end
  end
  if n >= 6 then return s / n end
  return 0.80                                   -- IPOTESI iniziale (rendimento tipico)
end

-- ------------------------------------------------------------------ previsione
-- cal = calendario dell'istante, met = meteo dell'istante, tlag = temperatura media ultime ore
-- ritorna carico_w, fv_w, dettagli
function M.prevedi(mod, c, cal, met, tlag, prev_giorno)
  met = met or {}
  local x = M.caratteristiche(tlag or met.temp, met.vento, met.ghi)
  local pdc = M.pompa(mod, c, x)
  local comp
  local sim = prev_giorno and prev_giorno.simili
  if sim and sim[cal.quarto_orologio] then comp = sim[cal.quarto_orologio] end
  comp = comp or profilo(mod, cal.tipo, cal.quarto_orologio)
  local carico = comp and (comp + pdc) or nil
  local coef = coef_fv(mod, cal.ora, classe_cielo(met.nuvole))
  local fv = met.ghi and min(c.P_NOMINALE_FV_W, coef * met.ghi / 1000 * c.P_NOMINALE_FV_W) or nil
  if not fv and mod.fv_prof[cal.quarto_orologio] then fv = mod.fv_prof[cal.quarto_orologio].v end
  -- previsioni da GitHub (modello completo), se accettate
  local gh = prev_giorno and prev_giorno.github
  if gh then
    if gh.carico and gh.carico[cal.quarto_gme] then carico = gh.carico[cal.quarto_gme] end
    if gh.fv and gh.fv[cal.quarto_gme] then fv = gh.fv[cal.quarto_gme] end
  end
  return carico, fv, { pdc = pdc, comportamento = comp, coef_fv = coef, cielo = classe_cielo(met.nuvole),
                       fonte = gh and "github" or (sim and "giorni simili" or "profilo") }
end

-- correzione in giornata per un istante futuro (t_fut) a partire dagli scarti recenti
function M.correggi(mod, t_fut, carico, fv)
  local cc, cf = mod.corr.car, mod.corr.fv
  if carico and cc.t > 0 then carico = max(0, carico + cc.e * exp(-max(0, t_fut - cc.t) / 5400)) end
  if fv and cf.t > 0 then fv = max(0, fv * (1 + (cf.r - 1) * exp(-max(0, t_fut - cf.t) / 7200))) end
  return carico, fv
end

function M.sigma(mod, ora)
  local sc = mod.sig.car[tostring(ora)] or 300
  local sf = mod.sig.fv[tostring(ora)] or 0.25
  return sc, sf
end

-- ------------------------------------------------------------------ aggiornamento con una lettura reale
-- l = lettura Huawei; prev = { carico =, fv = } previsione del modello per l'istante (prima dell'aggiornamento)
-- prev_sera = previsione della sera prima (per il margine), dt_h = durata dell'intervallo, l_prec = lettura precedente
function M.aggiorna(mod, c, cal, met, tlag, l, prev, prev_sera, dt_h, l_prec)
  met = met or {}
  -- pompa di calore e comportamento
  local x = M.caratteristiche(tlag or met.temp, met.vento, met.ghi)
  local pdc = M.pompa(mod, c, x)
  local target = max(0, l.carico_w - pdc)
  mod.profili[cal.tipo] = mod.profili[cal.tipo] or {}
  local p = mod.profili[cal.tipo][cal.quarto_orologio]
  if not p then
    mod.profili[cal.tipo][cal.quarto_orologio] = { v = target, n = 1 }
  else
    p.n = p.n + 1
    local a = (p.n <= 10) and (1 / p.n) or 0.053      -- circa il 15 % di peso per ogni nuovo giorno
    p.v = p.v + a * (target - p.v)
  end
  -- FV
  if met.ghi and met.ghi > 50 then
    local obs = l.fv_w / (met.ghi / 1000 * c.P_NOMINALE_FV_W)
    obs = max(0, min(1.3, obs))
    local k = tostring(cal.ora)
    mod.fv_coef[k] = mod.fv_coef[k] or {}
    local cls = classe_cielo(met.nuvole)
    local b = mod.fv_coef[k][cls]
    if not b then mod.fv_coef[k][cls] = { v = obs, n = 1 }
    else
      b.n = b.n + 1
      b.v = b.v + ((b.n <= 10) and (1 / b.n) or 0.05) * (obs - b.v)
    end
  end
  local fp = mod.fv_prof[cal.quarto_orologio]
  if not fp then mod.fv_prof[cal.quarto_orologio] = { v = l.fv_w, n = 1 }
  else fp.n = fp.n + 1; fp.v = fp.v + ((fp.n <= 10) and (1 / fp.n) or 0.05) * (l.fv_w - fp.v) end
  -- correzione in giornata
  if prev and prev.carico then
    mod.corr.car.e = 0.7 * (mod.corr.car.e or 0) + 0.3 * (l.carico_w - prev.carico)
    mod.corr.car.t = cal.epoca
  end
  if prev and prev.fv and prev.fv > 300 then
    local r = max(0.2, min(2, l.fv_w / prev.fv))
    mod.corr.fv.r = 0.7 * (mod.corr.fv.r or 1) + 0.3 * r
    mod.corr.fv.t = cal.epoca
  end
  -- margine (errore della previsione della sera prima, altrimenti del modello)
  local rif = prev_sera or prev
  if rif then
    local k = tostring(cal.ora)
    if rif.carico then
      local s = mod.sig.car[k] or 300
      mod.sig.car[k] = s + 0.03 * (1.25 * abs(l.carico_w - rif.carico) - s)
    end
    if rif.fv and (rif.fv > 200 or l.fv_w > 200) then
      local s = mod.sig.fv[k] or 0.25
      mod.sig.fv[k] = s + 0.03 * (1.25 * abs(l.fv_w - rif.fv) / max(rif.fv, 500) - s)
    end
  end
  -- rendimenti e ore a SOC alto
  if dt_h and dt_h > 0 and l_prec then
    if l.soc >= c.ORE_SOC_ALTO then mod.ore_soc_alto = mod.ore_soc_alto + dt_h end
    local pb = (l.batteria_w + l_prec.batteria_w) / 2
    local segno = (pb > 100 and 1) or (pb < -100 and -1) or 0
    local s = mod.eff.seg
    if s and s.segno ~= segno then
      local dsoc = l_prec.soc - s.soc0
      if s.durata >= 0.5 and abs(dsoc) >= 3 and abs(s.e_wh) > 0 then
        if s.segno == 1 and dsoc > 0 then
          mod.eff.car.e_in = mod.eff.car.e_in + s.e_wh / 1000
          mod.eff.car.imm = mod.eff.car.imm + dsoc / 100 * c.CAPACITA_KWH
        elseif s.segno == -1 and dsoc < 0 then
          mod.eff.sca.e_out = mod.eff.sca.e_out - s.e_wh / 1000
          mod.eff.sca.tolta = mod.eff.sca.tolta - dsoc / 100 * c.CAPACITA_KWH
        end
      end
      s = nil
    end
    if not s then s = { segno = segno, soc0 = l_prec.soc, e_wh = 0, durata = 0 } end
    s.e_wh = s.e_wh + pb * dt_h
    s.durata = s.durata + dt_h
    mod.eff.seg = s
    if l.fv_w < 20 and l_prec.fv_w < 20 and pb < -50 then
      local p_dc = -pb
      local i = (p_dc < 500 and 1) or (p_dc < 1000 and 2) or (p_dc < 2000 and 3) or 4
      local k = tostring(i)
      mod.eff.inv[k] = mod.eff.inv[k] or { ac = 0, dc = 0 }
      local p_ac = (l.inverter_w + l_prec.inverter_w) / 2
      if p_ac > 0 then
        mod.eff.inv[k].ac = mod.eff.inv[k].ac + p_ac * dt_h / 1000
        mod.eff.inv[k].dc = mod.eff.inv[k].dc + p_dc * dt_h / 1000
      end
    end
  end
end

-- rendimenti da usare: misurati se ci sono abbastanza dati, altrimenti quelli della configurazione
function M.efficienze(mod, c)
  local e = { c = c.RENDIMENTO_CARICA, d = c.RENDIMENTO_SCARICA, inv = {}, fonte = {} }
  local ec = mod.eff.car
  if ec.e_in >= 3 then e.c = max(0.8, min(1, ec.imm / ec.e_in)); e.fonte.c = "misurato" else e.fonte.c = "ipotesi" end
  local es = mod.eff.sca
  if es.tolta >= 3 then e.d = max(0.8, min(1, es.e_out / es.tolta)); e.fonte.d = "misurato" else e.fonte.d = "ipotesi" end
  for i = 1, 4 do
    local b = mod.eff.inv[tostring(i)]
    if b and b.dc >= 1 then e.inv[i] = max(0.6, min(1, b.ac / b.dc)) else e.inv[i] = c.RENDIMENTO_INVERTER end
  end
  return e
end

-- ------------------------------------------------------------------ chiusura del giorno e GitHub
-- giornata = { giorno=, tipo=, tmed=, ghi=, comp = { [q orologio] = W comportamento medio } }
function M.chiudi_giorno(mod, giornata)
  -- media delle caratteristiche della pompa nel giorno (per la stima giornaliera)
  if giornata.x and giornata.n_x and giornata.n_x >= 200 then
    giornata.xm = {}
    for i = 1, N_FEAT do giornata.xm[i] = giornata.x[i] / giornata.n_x end
  else
    giornata.carico_medio = nil
  end
  giornata.x, giornata.n_x = nil, nil
  table.insert(mod.giorni, giornata)
  table.sort(mod.giorni, function(a, b) return a.g < b.g end)
  while #mod.giorni > 120 do table.remove(mod.giorni, 1) end
  mod._cache = nil
  M.stima_pompa(mod)
end

-- applica i coefficienti calcolati su GitHub (gia' verificati la' come migliori)
function M.applica_github(mod, g)
  if type(g) ~= "table" or not g.accettato then return false, "non accettato" end
  local n = 0
  for tipo, valori in pairs(g.profili or {}) do
    mod.profili[tipo] = mod.profili[tipo] or {}
    for q, v in pairs(valori) do
      local qq = tonumber(q)
      if qq and type(v) == "number" and v >= 0 and v < 20000 then
        mod.profili[tipo][qq] = { v = v, n = max(30, (mod.profili[tipo][qq] or { n = 0 }).n) }
        n = n + 1
      end
    end
  end
  if type(g.theta) == "table" and #g.theta == N_FEAT then
    local ok = true
    for i = 1, N_FEAT do if type(g.theta[i]) ~= "number" then ok = false end end
    if ok then mod.theta = g.theta end
  end
  for ora, classi in pairs(g.fv_coef or {}) do
    mod.fv_coef[tostring(ora)] = mod.fv_coef[tostring(ora)] or {}
    for k = 1, 3 do
      local v = classi[k]
      if type(v) == "number" and v >= 0 and v <= 1.3 then mod.fv_coef[tostring(ora)][k] = { v = v, n = 30 } end
    end
  end
  mod.github.versione = g.versione
  mod.github.applicato_il = os.time()
  return true, n .. " valori di profilo"
end

return M
