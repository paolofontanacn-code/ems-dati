-- ottimizzatore.lua - pianificazione a programmazione dinamica sul SOC, a passi di 15 minuti
--
-- Per ogni profilo di prezzo (A, B, C) trova la sequenza di azioni che massimizza
--   somma( cessioni nette - acquisti - usura - penalita' ) + valore dell'energia rimasta a fine orizzonte
-- rispettando: SOC, potenze, prelievo/immissione massimi (nel simulatore), al massimo MAX_FINESTRE_GIORNO periodi
-- forzati al giorno (vincolo gestito con un costo per finestra aumentato finche' il limite e' rispettato).
-- Le azioni cambiano solo ogni 15 minuti, quindi ogni modo dura almeno un quarto d'ora.
-- Ogni cambiamento di funzionamento (compreso il ritorno all'autoconsumo) costa PENALITA_CAMBIO_EUR.
local S = require "simulatore"
local M = {}
local floor, max, min = math.floor, math.max, math.min

local CAT_IDX = { auto = 1, carica = 2, scarica = 3 }
local DT = 0.25
local PEN_SFORAMENTO = 10        -- EUR/kWh oltre il prelievo massimo (praticamente vietato)

-- quarti[k] = { t, giorno, fv, carico, di_giorno, mezzanotte, vend = EUR/kWh netti, costo = { A=, B=, C= } }
-- profili[p] = { soc0, prev_azione (azione in corso), finestre_oggi, giorno_oggi }
local function un_passaggio(c, e, quarti, nomi, profili, usura, lambda, valore_fine)
  local N = #quarti
  local lo, hi = c.SOC_MIN, c.SOC_MAX
  local n = math.ceil((hi - lo) / (c.PASSO_SOC_KWH / c.CAPACITA_KWH * 100)) + 1
  local step = (hi - lo) / (n - 1)
  local griglia = {}
  for i = 1, n do griglia[i] = lo + (i - 1) * step end
  local azioni = S.azioni(c)
  local NA = #azioni
  local idx_az = {}
  for a, nome in ipairs(azioni) do idx_az[nome] = a end
  local cat_az = {}
  for a, nome in ipairs(azioni) do cat_az[a] = CAT_IDX[S.categoria(nome)] end
  local eta_fin = S.eta_scarica(e, 1000)

  -- valore dell'energia rimasta a fine orizzonte: i kWh che serviranno alla casa nella notte successiva
  -- (fino al ritorno del FV) valgono l'acquisto evitato; quelli in piu' valgono solo come cessione
  local Vn = {}
  for _, p in ipairs(nomi) do
    Vn[p] = {}
    local vf = valore_fine[p]
    local v_alto = max(0, vf.costo - usura)
    local v_basso = max(0, (vf.vend or 0) - usura)
    local base = {}
    for i = 1, n do
      local e_ac = (griglia[i] - lo) / 100 * c.CAPACITA_KWH * eta_fin
      local e1 = min(e_ac, vf.e_notte or e_ac)
      base[i] = e1 * v_alto + (e_ac - e1) * v_basso
    end
    for a = 1, #azioni do Vn[p][a] = base end
  end
  local pol = {}
  for _, p in ipairs(nomi) do pol[p] = {} end
  local s2, pr, im, sc, sf = {}, {}, {}, {}, {}
  local _ = CAT_IDX
  for a = 1, #azioni do s2[a], pr[a], im[a], sc[a], sf[a] = {}, {}, {}, {}, {} end
  local primo = {}

  local function interp(V, soc)
    local pos = (soc - lo) / step + 1
    local i = floor(pos)
    if i < 1 then return V[1] end
    if i >= n then return V[n] end
    local f = pos - i
    return V[i] + f * (V[i + 1] - V[i])
  end

  for k = N, 1, -1 do
    local q = quarti[k]
    local ammesse = {}
    for a, nome in ipairs(azioni) do
      if nome ~= "CARICA_RETE" or q.di_giorno then ammesse[#ammesse + 1] = a end
    end
    for _, a in ipairs(ammesse) do
      local nome = azioni[a]
      local S2, PR, IM, SC, SF = s2[a], pr[a], im[a], sc[a], sf[a]
      for i = 1, n do
        S2[i], PR[i], IM[i], SC[i], SF[i] = S.passo_num(c, e, griglia[i], nome, q.fv, q.carico, DT, q.di_giorno)
      end
    end
    for _, p in ipairs(nomi) do
      local costo = q.costo[p]
      local vend = q.vend
      local lam = lambda[p]
      local Vc = {}
      for a = 1, NA do Vc[a] = {} end
      local polk = {}
      local Vnp = Vn[p]
      local val = {}
      local pen_c = c.PENALITA_CAMBIO_EUR
      for i = 1, n do
        -- valore di ogni azione (indipendente dall'azione precedente)
        for _, a in ipairs(ammesse) do
          local r = (im[a][i] * vend - pr[a][i] * costo - sc[a][i] * usura - sf[a][i] * PEN_SFORAMENTO) * DT / 1000
          val[a] = r + interp(Vnp[a], s2[a][i])
        end
        for prev = 1, NA do
          local cp = cat_az[prev]
          local best, ba = -1e18, 1
          for _, a in ipairs(ammesse) do
            local v = val[a]
            if a ~= prev then
              v = v - pen_c                                -- ogni cambio di funzionamento costa PENALITA_CAMBIO_EUR
              local ca = cat_az[a]
              if ca ~= 1 and (ca ~= cp or q.mezzanotte) then v = v - lam end
            elseif cat_az[a] ~= 1 and q.mezzanotte then
              v = v - lam
            end
            if v > best then best, ba = v, a end
          end
          Vc[prev][i] = best
          polk[(prev - 1) * n + i] = ba
        end
      end
      pol[p][k] = polk
      if k == 1 then
        -- decisione esatta per il SOC attuale e valori delle alternative
        local pf = profili[p]
        local prev = idx_az[pf.prev_azione or "AUTO"] or 1
        local cp = cat_az[prev]
        local alt, best, ba = {}, -1e18, 1
        for _, a in ipairs(ammesse) do
          local nome = azioni[a]
          local so, prl, imm, sca, sfo = S.passo_num(c, e, pf.soc0, nome, q.fv, q.carico, DT, q.di_giorno)
          local v = (imm * vend - prl * costo - sca * usura - sfo * PEN_SFORAMENTO) * DT / 1000 + interp(Vnp[a], so)
          local ca = cat_az[a]
          local vv = v
          if a ~= prev then
            vv = vv - c.PENALITA_CAMBIO_EUR
            if ca ~= 1 and (ca ~= cp or q.mezzanotte) then vv = vv - lam end
          elseif ca ~= 1 and q.mezzanotte then vv = vv - lam end
          alt[nome] = vv
          if vv > best then best, ba = vv, a end
        end
        primo[p] = { azione = azioni[ba], valore = best, alternative = alt }
      end
      Vn[p] = Vc
    end
  end

  -- percorso in avanti
  local ris = {}
  for _, p in ipairs(nomi) do
    local pf = profili[p]
    local soc = pf.soc0
    local prev_a = idx_az[pf.prev_azione or "AUTO"] or 1
    local prev = cat_az[prev_a]
    local piano, finestre, comandi = {}, {}, {}
    local az_prec = pf.prev_azione or "AUTO"
    for k = 1, N do
      local q = quarti[k]
      local nome
      if k == 1 then nome = primo[p].azione
      else
        local pos = (min(hi, max(lo, soc)) - lo) / step + 1
        local i = min(n, max(1, floor(pos + 0.5)))
        nome = azioni[pol[p][k][(prev_a - 1) * n + i]]
      end
      local so, prl, imm, sca, sfo = S.passo_num(c, e, soc, nome, q.fv, q.carico, DT, q.di_giorno)
      local ca = CAT_IDX[S.categoria(nome)]
      if ca ~= 1 and (ca ~= prev or q.mezzanotte) then finestre[q.giorno] = (finestre[q.giorno] or 0) + 1 end
      if az_prec and nome ~= az_prec then comandi[q.giorno] = (comandi[q.giorno] or 0) + 1 end
      piano[k] = { t = q.t, azione = nome, soc = so, prelievo_w = prl, immissione_w = imm, scarica_w = sca,
                   sforamento_w = sfo, fv = q.fv, carico = q.carico,
                   euro = (imm * q.vend - prl * q.costo[p] - sca * usura) * DT / 1000 }
      soc, prev, az_prec, prev_a = so, ca, nome, idx_az[nome]
    end
    local gia = pf.finestre_oggi or 0
    if pf.giorno_oggi then finestre[pf.giorno_oggi] = (finestre[pf.giorno_oggi] or 0) + gia end
    local viol = false
    for _, nf in pairs(finestre) do if nf > c.MAX_FINESTRE_GIORNO then viol = true end end
    ris[p] = { piano = piano, finestre = finestre, comandi = comandi, primo = primo[p], violazione = viol,
               lambda = lambda[p], soc_fine = soc }
  end
  return ris
end

-- tronca le finestre oltre il limite (ultima difesa): da quel punto in poi solo AUTO in quel giorno
local function tronca(c, e, quarti, r, pf, usura, p)
  local cont = {}
  if pf.giorno_oggi then cont[pf.giorno_oggi] = pf.finestre_oggi or 0 end
  local soc, prev = pf.soc0, S.categoria(pf.prev_azione or "AUTO")
  for k, x in ipairs(r.piano) do
    local q = quarti[k]
    local cat = S.categoria(x.azione)
    if cat ~= "auto" and (cat ~= prev or q.mezzanotte) then
      if (cont[q.giorno] or 0) >= c.MAX_FINESTRE_GIORNO then x.azione = "AUTO"; cat = "auto"
      else cont[q.giorno] = (cont[q.giorno] or 0) + 1 end
    end
    local so, prl, imm, sca, sfo = S.passo_num(c, e, soc, x.azione, q.fv, q.carico, DT, q.di_giorno)
    x.soc, x.prelievo_w, x.immissione_w, x.scarica_w, x.sforamento_w = so, prl, imm, sca, sfo
    x.euro = (imm * q.vend - prl * q.costo[p] - sca * usura) * DT / 1000
    soc, prev = so, cat
  end
  r.finestre = cont
  r.primo.azione = r.piano[1] and r.piano[1].azione or "AUTO"
  r.troncato = true
  r.soc_fine = soc
end

-- interfaccia: ritorna per ogni profilo il piano e la prima azione
function M.pianifica(c, e, quarti, nomi, profili, usura, valore_fine)
  local lambda = {}
  for _, p in ipairs(nomi) do lambda[p] = c.PENALITA_FINESTRA_EUR or 0 end
  local ris
  for giro = 1, 6 do
    ris = un_passaggio(c, e, quarti, nomi, profili, usura, lambda, valore_fine)
    local altro = false
    for _, p in ipairs(nomi) do
      if ris[p].violazione then
        lambda[p] = math.max(0.05, lambda[p] * 3)
        altro = true
      end
    end
    if not altro then break end
  end
  for _, p in ipairs(nomi) do
    if ris[p].violazione then tronca(c, e, quarti, ris[p], profili[p], usura, p) end
    local v = 0
    for _, x in ipairs(ris[p].piano) do v = v + x.euro end
    ris[p].valore_piano = v
  end
  return ris
end

return M
