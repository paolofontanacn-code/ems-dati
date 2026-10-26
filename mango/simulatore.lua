-- Revisione R05 - 26/10/2026 - scarica forzata mai sotto P_MIN_SCARICA_W (2 kW): sotto, la batteria si ferma
-- simulatore.lua - modello energetico della batteria simulata (SOLO SIMULAZIONE)
--
-- Dati FV e consumi (W medi nell'intervallo) e un'azione, calcola i flussi:
--   fv_carichi, fv_batt, rete_batt, batt_carichi, batt_rete, fv_rete, rete_carichi, fv_tagliato
-- e il nuovo SOC. L'energia scaricata in simulazione e' "spesa": il SOC prosegue da un passo all'altro.
--
-- Azioni:
--   AUTO          massimo autoconsumo: FV ai carichi, eccedenza in batteria poi in rete; la batteria
--                 copre i carichi quando il FV non basta. Mai rete -> batteria.
--   RITARDATA     come AUTO ma con potenza di carica limitata (P_CARICA_RITARDATA_W): l'eccedenza va in rete
--   CARICA_FV     carica forzata (finestra TOU senza carica da rete): la batteria non scarica,
--                 si carica con l'eccedenza FV
--   CARICA_RETE_<W> come CARICA_FV piu' rete -> batteria fino a <W> watt (carica AC; solo di giorno se
--                 CARICA_RETE_SOLO_GIORNO). CARICA_RETE senza livello = P_MAX_CARICA_RETE_W (versioni precedenti)
--   SCARICA_<W>   scarica forzata a <W> watt: copre i carichi, il resto va in rete; si ferma a SOC_MIN_VENDITA
-- Limiti: prelievo <= P_MAX_PRELIEVO_W (la batteria interviene anche fuori da AUTO), immissione
-- <= P_MAX_IMMISSIONE_W e uscita AC dell'inverter <= P_MAX_AC_INVERTER_W (oltre: FV tagliato).
local M = {}
local min, max = math.min, math.max

-- categoria per il conteggio delle finestre: auto, carica, scarica
function M.categoria(azione)
  if azione == "AUTO" or azione == "RITARDATA" then return "auto" end
  if azione == "CARICA_FV" or azione:sub(1, 11) == "CARICA_RETE" then return "carica" end
  return "scarica"
end

function M.azioni(c)
  local a = { "AUTO", "RITARDATA", "CARICA_FV" }
  if c.CARICA_DA_RETE_AMMESSA then
    for _, w in ipairs(c.LIVELLI_CARICA_RETE_W or { c.P_MAX_CARICA_RETE_W }) do a[#a + 1] = "CARICA_RETE_" .. w end
  end
  for _, w in ipairs(c.LIVELLI_SCARICA_W) do a[#a + 1] = "SCARICA_" .. w end
  return a
end

-- rendimento AC complessivo in scarica in funzione della potenza (rendimenti e: c = carica, d = scarica batteria,
-- inv = tabella {fino a 500 W, fino a 1000 W, fino a 2000 W, oltre})
local function eta_scarica(e, p)
  local i = (p < 500 and 1) or (p < 1000 and 2) or (p < 2000 and 3) or 4
  return e.d * (e.inv[i] or e.inv[4])
end
M.eta_scarica = eta_scarica

local function p_sca_max(c, e, soc, dt, lim, p_rif)
  local disp = max(0, (soc - lim) / 100 * c.CAPACITA_KWH)
  return min(c.P_MAX_SCARICA_W, disp * eta_scarica(e, p_rif) / dt * 1000)
end

-- passo numerico (nessuna tabella creata: usato migliaia di volte dall'ottimizzatore)
-- ritorna: soc2, prelievo, immissione, scarica_ac, sforamento, fv_carichi, fv_batt, rete_batt,
--          batt_carichi, batt_rete, fv_rete, rete_carichi, fv_tagliato
function M.passo_num(c, e, soc, azione, fv, carico, dt, di_giorno)
  if fv < 0 then fv = 0 end
  if carico < 0 then carico = 0 end
  local cap = c.CAPACITA_KWH
  local spazio = max(0, (c.SOC_MAX - soc) / 100 * cap)
  local p_car_max = min(c.P_MAX_CARICA_W, spazio / (e.c * dt) * 1000)

  local fv_car = min(fv, carico)
  local ecc = fv - fv_car
  local manca = carico - fv_car
  local fv_batt, rete_batt, batt_car, batt_rete, fv_rete, rete_car = 0, 0, 0, 0, 0, 0

  local cat = M.categoria(azione)
  if cat == "scarica" then
    local livello = tonumber(azione:match("_(%d+)$")) or c.P_MAX_SCARICA_W
    local p = min(livello, p_sca_max(c, e, soc, dt, max(c.SOC_MIN, c.SOC_MIN_VENDITA), livello))
    if p < (c.P_MIN_SCARICA_W or 0) then p = 0 end           -- R05: scarica modulabile solo tra 2 e 5 kW
    batt_car = min(manca, p)
    batt_rete = p - batt_car
    rete_car = manca - batt_car
    fv_rete = ecc
  else
    local lim_car = p_car_max
    if azione == "RITARDATA" then lim_car = min(lim_car, c.P_CARICA_RITARDATA_W) end
    fv_batt = min(ecc, lim_car)
    fv_rete = ecc - fv_batt
    if azione:sub(1, 11) == "CARICA_RETE" and (di_giorno or not c.CARICA_RETE_SOLO_GIORNO) then
      local liv = tonumber(azione:match("_(%d+)$")) or c.P_MAX_CARICA_RETE_W
      rete_batt = max(0, min(liv, p_car_max - fv_batt))
    end
    if cat == "auto" then batt_car = min(manca, p_sca_max(c, e, soc, dt, c.SOC_MIN, manca)) end
    rete_car = manca - batt_car
  end

  local tagliato = 0
  -- immissione massima: prima si riduce la batteria, poi si taglia il FV
  local imm = fv_rete + batt_rete
  if imm > c.P_MAX_IMMISSIONE_W then
    local ecc2 = imm - c.P_MAX_IMMISSIONE_W
    local r = min(batt_rete, ecc2); batt_rete = batt_rete - r; ecc2 = ecc2 - r
    r = min(fv_rete, ecc2); fv_rete = fv_rete - r; tagliato = tagliato + r
  end
  -- uscita AC massima dell'inverter
  local ac = fv_car + fv_rete + batt_car + batt_rete
  if ac > c.P_MAX_AC_INVERTER_W then
    local ecc2 = ac - c.P_MAX_AC_INVERTER_W
    local r = min(batt_rete, ecc2); batt_rete = batt_rete - r; ecc2 = ecc2 - r
    r = min(fv_rete, ecc2); fv_rete = fv_rete - r; tagliato = tagliato + r; ecc2 = ecc2 - r
    r = min(batt_car, ecc2); batt_car = batt_car - r; rete_car = rete_car + r; ecc2 = ecc2 - r
    r = min(fv_car, ecc2); fv_car = fv_car - r; rete_car = rete_car + r; tagliato = tagliato + r
  end
  -- prelievo massimo: prima si riduce la carica da rete, poi interviene la batteria (anche fuori da AUTO)
  local sfor = 0
  local prel = rete_car + rete_batt
  if prel > c.P_MAX_PRELIEVO_W then
    local ecc2 = prel - c.P_MAX_PRELIEVO_W
    local r = min(rete_batt, ecc2); rete_batt = rete_batt - r; ecc2 = ecc2 - r
    if ecc2 > 0 then
      local resto = max(0, p_sca_max(c, e, soc, dt, c.SOC_MIN, batt_car + batt_rete + ecc2) - batt_car - batt_rete)
      resto = min(resto, c.P_MAX_AC_INVERTER_W - (fv_car + fv_rete + batt_car + batt_rete))
      r = max(0, min(resto, ecc2, rete_car))
      batt_car = batt_car + r; rete_car = rete_car - r; ecc2 = ecc2 - r
    end
    sfor = ecc2
  end

  local scarica_ac = batt_car + batt_rete
  -- controllo finale dell'energia disponibile (il rendimento dipende dalla potenza effettiva)
  if scarica_ac > 0 then
    local lim = (cat == "scarica") and max(c.SOC_MIN, c.SOC_MIN_VENDITA) or c.SOC_MIN
    local disp = max(0, (soc - lim) / 100 * cap)
    local serve = scarica_ac / eta_scarica(e, scarica_ac) * dt / 1000
    if serve > disp + 1e-12 then
      local k = (serve > 0) and disp / serve or 0
      -- la potenza ridotta ha un rendimento diverso: si ripete il calcolo una volta e si prende il minimo
      local nuovo = scarica_ac * k
      if nuovo > 0 then
        local serve2 = nuovo / eta_scarica(e, nuovo) * dt / 1000
        if serve2 > disp then nuovo = nuovo * disp / serve2 end
      end
      k = (scarica_ac > 0) and nuovo / scarica_ac or 0
      local riduci_car = batt_car * (1 - k)
      batt_car = batt_car - riduci_car
      rete_car = rete_car + riduci_car
      batt_rete = batt_rete * k
      scarica_ac = batt_car + batt_rete
      local prel2 = rete_car + rete_batt
      if prel2 > c.P_MAX_PRELIEVO_W then sfor = max(sfor, prel2 - c.P_MAX_PRELIEVO_W) end
    end
  end
  local soc2 = soc + ((fv_batt + rete_batt) * e.c - (scarica_ac > 0 and scarica_ac / eta_scarica(e, scarica_ac) or 0))
    * dt / 1000 / cap * 100
  if soc2 < 0 then soc2 = 0 elseif soc2 > 100 then soc2 = 100 end
  return soc2, rete_car + rete_batt, fv_rete + batt_rete, scarica_ac, sfor,
    fv_car, fv_batt, rete_batt, batt_car, batt_rete, fv_rete, rete_car, tagliato
end

-- versione con tabella (per la simulazione e il registro)
function M.passo(c, e, soc, azione, fv, carico, dt, di_giorno)
  local soc2, prel, imm, sca, sfor, fc, fb, rb, bc, br, fr, rc, tg = M.passo_num(c, e, soc, azione, fv, carico, dt, di_giorno)
  return {
    soc = soc2, prelievo_w = prel, immissione_w = imm, scarica_w = sca, carica_w = fb + rb, sforamento_w = sfor,
    fv_carichi_w = fc, fv_batt_w = fb, rete_batt_w = rb, batt_carichi_w = bc, batt_rete_w = br,
    fv_rete_w = fr, rete_carichi_w = rc, fv_tagliato_w = tg, batteria_w = fb + rb - sca,
  }
end

return M
