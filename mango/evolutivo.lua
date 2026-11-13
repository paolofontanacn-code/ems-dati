-- Revisione R11 - 13/11/2026 - nuovo: pianificazione con ALGORITMO EVOLUTIVO (condizione 3), in aggiunta alla programmazione
--   dinamica di ottimizzatore.lua (condizione 2). Stessi dati, stesso modello della batteria, stessi costi e limiti.
-- evolutivo.lua - SOLO SIMULAZIONE
--
-- PIANO = un'azione per ogni ORA dell'orizzonte (comandi costanti nell'ora). Si cerca il piano con il valore piu' alto:
--   somma( cessioni - acquisti - usura ) + valore dell'energia rimasta a fine orizzonte (come la programmazione dinamica)
--   - pesi della potenza - costo dei cambi - costo delle ore a SOC alto
--   - 1 EUR per ogni periodo forzato oltre MAX_FINESTRE_GIORNO - 1 EUR/kWh di scarica forzata oltre il limite giornaliero.
-- RICERCA: popolazione di piani; semi = tutto automatico, batteria ferma, piano precedente (ore ancora valide), regola
--   semplice sui prezzi (prezzo di vendita alto -> scarica, basso con esubero FV -> carica); poi torneo, incrocio,
--   mutazione, e restano i migliori tra genitori e figli. I numeri casuali partono dall'ora del piano: stesso ingresso,
--   stesso risultato. NON usa il piano della programmazione dinamica come seme: i due metodi sono indipendenti.
local S = require "simulatore"
local M = {}
local floor, max, min = math.floor, math.max, math.min
local DT = 0.25
local PEN_SFORAMENTO = 10
local CAT = { auto = 1, carica = 2, scarica = 3, ferma = 4 }

-- pf = { soc0, prev_azione, finestre_oggi, giorno_oggi, scarica_forzata_oggi, genoma (facoltativo) }
-- vf = { costo, vend, e_notte }; tronca = funzione di ottimizzatore.lua (ultima difesa sui limiti)
function M.pianifica(c, e, quarti, p, pf, usura, vf, tronca)
  local N = #quarti
  local azioni = {}
  for _, nome in ipairs(S.azioni(c)) do
    if nome:sub(1, 11) ~= "CARICA_RETE" then azioni[#azioni + 1] = nome end       -- niente carica dalla rete
  end
  local NA = #azioni
  local idx, cat = {}, {}
  for a, nome in ipairs(azioni) do idx[nome] = a; cat[a] = CAT[S.categoria(nome)] end
  -- ore dell'orizzonte
  local h0 = floor(quarti[1].t / 3600)
  local ora_q = {}
  for k = 1, N do ora_q[k] = floor(quarti[k].t / 3600) - h0 + 1 end
  local NH = ora_q[N]
  local soglia_alta, pen_alta = c.ORE_SOC_ALTO or 101, (c.PENALITA_SOC_ALTO_EUR_ORA or 0) * DT
  local pen_c = c.PENALITA_CAMBIO_EUR or 0
  local lim_e = (c.MAX_CICLI_FORZATI_GIORNO or 1e9) * c.CAPACITA_KWH
  local eta_fin = S.eta_scarica(e, 1000)
  local v_alto, v_basso = max(0, vf.costo - usura), max(0, (vf.vend or 0) - usura)
  local prev_nome = S.normalizza(c, pf.prev_azione)
  local prev_cat0 = CAT[S.categoria(prev_nome)]

  -- valore di un piano; con dettaglio = true ritorna anche il piano quarto per quarto
  local function valuta(g, dettaglio)
    local soc, prev, az_prec = pf.soc0, prev_cat0, prev_nome
    local tot, veri = 0, 0
    local finestre, forzata, comandi, piano = {}, {}, {}, dettaglio and {} or nil
    for k = 1, N do
      local q = quarti[k]
      local a = g[ora_q[k]]
      local nome = azioni[a]
      local so, prl, imm, sca, sfo, _f, fb, rb, bc, br = S.passo_num(c, e, soc, nome, q.fv, q.carico, DT, q.di_giorno)
      local costo = q.costo[p]
      local euro = (imm * q.vend - prl * costo - sca * usura) * DT / 1000
      local wd, wc = 1 - S.peso(c, e, "scarica", sca), 1 - S.peso(c, e, "carica", fb + rb)
      local r = euro - (sfo * PEN_SFORAMENTO + (wd * bc + wc * rb) * costo + (wd * br + wc * fb) * q.vend) * DT / 1000
      if so > soglia_alta then r = r - pen_alta end
      if nome ~= az_prec then r = r - pen_c; comandi[q.giorno] = (comandi[q.giorno] or 0) + 1 end
      local ca = cat[a]
      if ca ~= 1 and (ca ~= prev or q.mezzanotte) then finestre[q.giorno] = (finestre[q.giorno] or 0) + 1 end
      if ca == 3 then forzata[q.giorno] = (forzata[q.giorno] or 0) + sca * DT / 1000 end
      tot, veri = tot + r, veri + euro
      if piano then
        piano[k] = { t = q.t, azione = nome, soc = so, prelievo_w = prl, immissione_w = imm, scarica_w = sca,
                     sforamento_w = sfo, fv = q.fv, carico = q.carico, euro = euro }
      end
      soc, prev, az_prec = so, ca, nome
    end
    if pf.giorno_oggi then
      finestre[pf.giorno_oggi] = (finestre[pf.giorno_oggi] or 0) + (pf.finestre_oggi or 0)
      forzata[pf.giorno_oggi] = (forzata[pf.giorno_oggi] or 0) + (pf.scarica_forzata_oggi or 0)
    end
    local viol, viol_e = false, false
    for _, nf in pairs(finestre) do
      if nf > c.MAX_FINESTRE_GIORNO then viol = true; tot = tot - (nf - c.MAX_FINESTRE_GIORNO) end
    end
    for _, kwh in pairs(forzata) do
      if kwh > lim_e + 0.05 then viol_e = true; tot = tot - (kwh - lim_e) end
    end
    local e_ac = max(0, soc - c.SOC_MIN) / 100 * c.CAPACITA_KWH * eta_fin
    local e1 = min(e_ac, vf.e_notte or e_ac)
    tot = tot + e1 * v_alto + (e_ac - e1) * v_basso
    if dettaglio then return tot, piano, finestre, forzata, comandi, viol, viol_e, soc, veri end
    return tot
  end

  -- numeri casuali ripetibili (non dipendono dalla libreria del sistema)
  local seme = (quarti[1].t % 2147483647) + 12345
  local function caso()
    seme = (seme * 16807) % 2147483647
    return seme / 2147483647
  end
  local function intero(n) return min(n, floor(caso() * n) + 1) end

  local POP = c.EV_POPOLAZIONE or 30
  local GEN = c.EV_GENERAZIONI or 40
  local function costante(a) local g = {}; for h = 1, NH do g[h] = a end; return g end
  local pop = { costante(idx.AUTO), costante(idx.BATTERIA_FERMA or idx.AUTO) }
  -- piano precedente, sulle ore ancora valide
  if type(pf.genoma) == "table" and type(pf.genoma.g) == "table" and pf.genoma.h0 then
    local g = costante(idx.AUTO)
    for h = 1, NH do
      local nome = pf.genoma.g[h + h0 - pf.genoma.h0]
      if nome and idx[nome] then g[h] = idx[nome] end
    end
    pop[#pop + 1] = g
  end
  -- regola semplice sui prezzi: vendita alta -> scarica, vendita bassa con esubero FV -> carica dai pannelli
  do
    local vend_h, ecc_h, n_h = {}, {}, {}
    for k = 1, N do
      local h, q = ora_q[k], quarti[k]
      vend_h[h] = (vend_h[h] or 0) + q.vend; ecc_h[h] = (ecc_h[h] or 0) + (q.fv - q.carico); n_h[h] = (n_h[h] or 0) + 1
    end
    local ord = {}
    for h = 1, NH do vend_h[h] = vend_h[h] / n_h[h]; ecc_h[h] = ecc_h[h] / n_h[h]; ord[h] = vend_h[h] end
    table.sort(ord)
    local alto, basso = ord[max(1, floor(NH * 0.8))], ord[max(1, floor(NH * 0.4))]
    for _, liv in ipairs({ "SCARICA_2000", "SCARICA_4000" }) do
      if idx[liv] then
        local g = costante(idx.AUTO)
        for h = 1, NH do
          if vend_h[h] >= alto then g[h] = idx[liv]
          elseif vend_h[h] <= basso and ecc_h[h] > 300 then g[h] = idx["CARICA_FV_" .. c.P_MAX_CARICA_W] or idx.AUTO end
        end
        pop[#pop + 1] = g
      end
    end
  end
  local n_semi = #pop
  while #pop < POP do
    local g = {}
    if caso() < 0.7 then
      local base = pop[intero(n_semi)]
      for h = 1, NH do g[h] = (caso() < 0.2) and intero(NA) or base[h] end
    else
      for h = 1, NH do g[h] = intero(NA) end
    end
    pop[#pop + 1] = g
  end
  local fit = {}
  for i = 1, #pop do fit[i] = valuta(pop[i]) end
  local valutazioni = #pop
  local function torneo()
    local b = intero(#pop)
    for _ = 1, 2 do local x = intero(#pop); if fit[x] > fit[b] then b = x end end
    return pop[b]
  end
  for _ = 1, GEN do
    local tutti = {}
    for i = 1, #pop do tutti[i] = { g = pop[i], f = fit[i] } end
    for _ = 1, POP do
      local a, b, g = torneo(), torneo(), {}
      for h = 1, NH do
        g[h] = (caso() < 0.5) and a[h] or b[h]
        if caso() < 0.10 then g[h] = intero(NA) end
      end
      -- mutazione "a blocco": un tratto di ore consecutive con la stessa azione (i piani buoni hanno pochi cambi)
      if caso() < 0.3 then
        local h1 = intero(NH); local lun, az = intero(4), intero(NA)
        for h = h1, min(NH, h1 + lun - 1) do g[h] = az end
      end
      tutti[#tutti + 1] = { g = g, f = valuta(g) }
      valutazioni = valutazioni + 1
    end
    table.sort(tutti, function(x, y) return x.f > y.f end)
    for i = 1, POP do pop[i], fit[i] = tutti[i].g, tutti[i].f end
    for i = POP + 1, #pop do pop[i], fit[i] = nil, nil end
  end

  local best = pop[1]
  -- pulizia: dove l'automatico vale quanto l'azione scelta (es. di notte senza FV) si lascia l'automatico
  do
    local f_best = fit[1]
    for h = 1, NH do
      if best[h] ~= idx.AUTO then
        local vecchia = best[h]
        best[h] = idx.AUTO
        local f = valuta(best)
        valutazioni = valutazioni + 1
        if f >= f_best - 1e-9 then f_best = f else best[h] = vecchia end
      end
    end
  end
  local valore, piano, finestre, forzata, comandi, viol, viol_e, soc_fine = valuta(best, true)
  -- alternativa "automatico" nella prima ora (per il vantaggio su AUTO)
  local alt = { [azioni[best[1]]] = valore }
  if best[1] ~= idx.AUTO then
    local g2 = {}
    for h = 1, NH do g2[h] = best[h] end
    g2[1] = idx.AUTO
    alt.AUTO = valuta(g2)
  else alt.AUTO = valore end
  local nomi_g = {}
  for h = 1, NH do nomi_g[h] = azioni[best[h]] end
  local r = { piano = piano, finestre = finestre, comandi = comandi, forzata = forzata, violazione = viol, violazione_e = viol_e,
              primo = { azione = azioni[best[1]], valore = valore, alternative = alt }, soc_fine = soc_fine,
              genoma = { h0 = h0, g = nomi_g }, valutazioni = valutazioni, algoritmo = "evolutivo" }
  if (viol or viol_e) and tronca then tronca(c, e, quarti, r, pf, usura, p) end
  local v = 0
  for _, x in ipairs(r.piano) do v = v + x.euro end
  r.valore_piano = v
  return r
end

return M
