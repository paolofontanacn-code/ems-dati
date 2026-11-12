-- Revisione R10 - 12/11/2026 - pesi della potenza misurati (modelli/rendimenti_batteria.json) se presenti; prezzo di
--   acquisto orario (struttura) tramite prezzi_acquisto.lua
-- Revisione R08 - 07/11/2026 - prima versione: rigioco della condizione 2 su un giorno passato
-- rigioco.lua - SOLO SIMULAZIONE: rigioca la condizione 2 (senza carica dalla rete) su un giorno passato con lo stesso
-- ottimizzatore e lo stesso modello della batteria della simulazione vera.
-- Uso: lua rigioco.lua ingresso.json uscita.json
-- Ingresso (preparato da ml/rigioco_c2.py):
--   { giorno, soc0 = { C2 =, auto = }, ora_prezzi_domani = 13,
--     quarti = [ { t, giorno, mezzanotte, fv, carico (W reali), fv_prev, carico_prev (W previsti), nord (EUR/kWh) } ],
--     domani = [ { t, giorno, mezzanotte, fv_prev, carico_prev, nord } ] (vuoto se i prezzi di domani non ci sono) }
-- Decisione ogni ora (la simulazione vera decide ogni quarto d'ora) con le PREVISIONI; esecuzione di ogni quarto
-- d'ora con i dati REALI. In parallelo: automatico simulato (AUTO) e condizione 0 (senza batteria).
local CARTELLA = (arg and arg[0] or ""):match("^(.*)/[^/]*$") or "."
package.path = CARTELLA .. "/?.lua;" .. package.path
local J = require "lib_json"
local F = require "lib_file"
local S = require "simulatore"
local O = require "ottimizzatore"
local MOD = require "modelli"
local PA = require "prezzi_acquisto"
local c = dofile(CARTELLA .. "/config.lua")

local ing = J.decode(F.leggi(arg[1]))
local DT = 0.25
local P = "C2"
local usura = c.USURA_EUR_KWH

-- rendimenti: quelli misurati dal Mango se ci sono, altrimenti quelli di config.lua
local e = { c = c.RENDIMENTO_CARICA, d = c.RENDIMENTO_SCARICA, inv = { c.RENDIMENTO_INVERTER, c.RENDIMENTO_INVERTER,
            c.RENDIMENTO_INVERTER, c.RENDIMENTO_INVERTER } }
if ing.modelli and F.esiste(ing.modelli) then
  local ok, m = pcall(function() return MOD.normalizza(J.decode(F.leggi(ing.modelli))) end)
  if ok and m then
    local ok2, ee = pcall(MOD.efficienze, m, c)
    if ok2 and ee then e = ee end
  end
end

-- R10: pesi della potenza misurati (stesso file letto dalla simulazione); senza file: pesi fissi di config.lua
do
  local repo = os.getenv("EMS_REPO_DIR") or (CARTELLA .. "/..")
  local t = F.leggi(repo .. "/modelli/rendimenti_batteria.json")
  if t then
    local ok, d = pcall(J.decode, t)
    if ok and type(d) == "table" and type(d.pesi) == "table" then e.pesi = d.pesi end
  end
end

local function senza_batteria(fv, car)
  local fv_car = math.min(fv, car)
  local imm = math.max(0, math.min(fv - fv_car, c.P_MAX_IMMISSIONE_W, c.P_MAX_AC_INVERTER_W - fv_car))
  return car - fv_car, imm
end

local Q, D = ing.quarti, ing.domani or {}
-- prezzi: cessione = NORD x (1 - imposta); acquisto = prezzo fisso F0 con tutte le voci (prezzi_acquisto.lua)
local COSTO = PA.costo_da_energia(c, c.PREZZO_FISSO_A)
for _, l in ipairs({ Q, D }) do
  for _, x in ipairs(l) do x.vend = PA.valore_cessione(c, x.nord); x.costo = PA.costi(c, x.t)[P] or COSTO end
end
local soc, soc_auto = ing.soc0.C2 or 50, ing.soc0.auto or 50
local azione, finestre, scarica_forzata, lambda_e, comandi = "AUTO", 0, 0, nil, 0
local tot = { c2 = { prel = 0, imm = 0, sca = 0, costo = 0, ricavo = 0, usura = 0, interventi = 0 },
              auto = { prel = 0, imm = 0, sca = 0, costo = 0, ricavo = 0, usura = 0 },
              zero = { prel = 0, imm = 0, costo = 0, ricavo = 0 }, fv = 0, carico = 0 }
local righe, decisioni = {}, 0

for k, q in ipairs(Q) do
  -- decisione all'inizio di ogni ora
  if (k - 1) % 4 == 0 then
    local ora = (k - 1) / 4
    local quarti = {}
    local function aggiungi(x)
      quarti[#quarti + 1] = { t = x.t, giorno = x.giorno, fv = x.fv_prev or 0, carico = x.carico_prev or 800,
        di_giorno = (x.fv_prev or 0) >= c.FV_MIN_GIORNO_W, mezzanotte = x.mezzanotte and true or false,
        vend = x.vend, costo = { [P] = x.costo } }
    end
    for j = k, #Q do aggiungi(Q[j]) end
    local orizzonte_domani = ora >= (ing.ora_prezzi_domani or 13) and #D > 0
    if orizzonte_domani then for _, x in ipairs(D) do aggiungi(x) end end
    -- valore dell'energia a fine orizzonte (come la simulazione vera: consumi della notte dopo l'orizzonte)
    local s_c, s_v = 0, 0
    for _, x in ipairs(quarti) do s_c, s_v = s_c + x.costo[P], s_v + x.vend end
    local e_notte = 0
    local dopo = orizzonte_domani and {} or D
    for i = 1, math.min(56, #dopo) do
      local x = dopo[i]
      if (x.fv_prev or 0) >= (x.carico_prev or 0) and (x.fv_prev or 0) > c.FV_MIN_GIORNO_W then break end
      e_notte = e_notte + math.max(0, (x.carico_prev or 0) - (x.fv_prev or 0)) * 0.25 / 1000
    end
    if #dopo == 0 then e_notte = 8 end
    local vf = { [P] = { costo = s_c / #quarti, vend = s_v / #quarti, e_notte = e_notte } }
    local prof = { [P] = { soc0 = soc, prev_azione = azione, finestre_oggi = finestre, giorno_oggi = ing.giorno,
                           carica_rete_w = 0, scarica_forzata_oggi = scarica_forzata, lambda_e = lambda_e } }
    local ok, ris = pcall(O.pianifica, c, e, quarti, { P }, prof, usura, vf)
    if ok then
      decisioni = decisioni + 1
      local nuova = ris[P].primo.azione
      lambda_e = ris[P].lambda_e
      if nuova ~= azione then
        local cn, cv = S.categoria(nuova), S.categoria(azione)
        if cn ~= "auto" and cn ~= cv then finestre = finestre + 1 end
        comandi = comandi + 1
        tot.c2.interventi = tot.c2.interventi + c.PENALITA_CAMBIO_EUR
        azione = nuova
      end
    end
  end
  -- esecuzione del quarto d'ora con i dati reali
  local di_giorno = q.fv >= c.FV_MIN_GIORNO_W
  local r = S.passo(c, e, soc, azione, q.fv, q.carico, DT, di_giorno)
  soc = r.soc
  if S.categoria(azione) == "scarica" then scarica_forzata = scarica_forzata + r.scarica_w * DT / 1000 end
  local ep, ei, es = r.prelievo_w * DT / 1000, r.immissione_w * DT / 1000, r.scarica_w * DT / 1000
  local x = tot.c2
  x.prel, x.imm, x.sca = x.prel + ep, x.imm + ei, x.sca + es
  x.costo, x.ricavo, x.usura = x.costo + ep * q.costo, x.ricavo + ei * q.vend, x.usura + es * usura
  local a = S.passo(c, e, soc_auto, "AUTO", q.fv, q.carico, DT, di_giorno)
  soc_auto = a.soc
  local y = tot.auto
  local ap, ai, as = a.prelievo_w * DT / 1000, a.immissione_w * DT / 1000, a.scarica_w * DT / 1000
  y.prel, y.imm, y.sca = y.prel + ap, y.imm + ai, y.sca + as
  y.costo, y.ricavo, y.usura = y.costo + ap * q.costo, y.ricavo + ai * q.vend, y.usura + as * usura
  local zp, zi = senza_batteria(q.fv, q.carico)
  local z = tot.zero
  z.prel, z.imm = z.prel + zp * DT / 1000, z.imm + zi * DT / 1000
  z.costo, z.ricavo = z.costo + zp * DT / 1000 * q.costo, z.ricavo + zi * DT / 1000 * q.vend
  tot.fv, tot.carico = tot.fv + q.fv * DT / 1000, tot.carico + q.carico * DT / 1000
  righe[#righe + 1] = { t = q.t, azione = azione, categoria = S.categoria(azione), soc = r.soc, batteria_w = r.batteria_w,
                        prelievo_w = r.prelievo_w, immissione_w = r.immissione_w, auto_soc = a.soc, auto_batteria_w = a.batteria_w }
end

local netto = function(x) return x.costo - x.ricavo + (x.usura or 0) + (x.interventi or 0) end
local out = { giorno = ing.giorno, quarti = righe, soc_fine = { C2 = soc, auto = soc_auto }, decisioni = decisioni,
  comandi = comandi, finestre = finestre, rendimenti = { c = e.c, d = e.d },
  costo_acquisto = COSTO,
  totali = { fv_kwh = tot.fv, carico_kwh = tot.carico, c2 = tot.c2, auto = tot.auto, zero = tot.zero,
             c2_netto_eur = netto(tot.c2), auto_netto_eur = netto(tot.auto), c0_netto_eur = netto(tot.zero) } }
F.scrivi(arg[2], J.encode(out))
print(string.format("Rigioco %s: condizione 2 netto %.2f EUR, automatico %.2f EUR, senza batteria %.2f EUR, %d decisioni, %d cambi",
  ing.giorno, out.totali.c2_netto_eur, out.totali.auto_netto_eur, out.totali.c0_netto_eur, decisioni, comandi))
