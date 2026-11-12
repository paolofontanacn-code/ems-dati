-- Revisione R10 - 12/11/2026 - prezzo di acquisto ORARIO (struttura): la parte "energia" puo' venire ora per ora da un
--   file (PREZZO_ENERGIA_ORARIO_FILE); le altre componenti restano fisse. Senza file: prezzo fisso F0 (come prima).
--   Nuova funzione componenti() per i grafici.
-- Revisione R07 - 31/10/2026 - tolte le medie del PUN per fascia (si usa solo il prezzo fisso F0)
-- prezzi_acquisto.lua - costo del kWh prelevato e valore del kWh ceduto
--   costo = [energia x (1 + PERDITE) + DISPACCIAMENTO + TRASPORTO + ONERI + ACCISE] x (1 + IVA), uguale per
--   tutti i profili; energia = PREZZO_FISSO_A (F0) oppure il valore orario del file; cessione = NORD x (1 - IMPOSTA_CESSIONI)
local T = require "lib_tempo"
local J = require "lib_json"
local F = require "lib_file"
local M = {}

function M.costo_da_energia(c, energia)
  return (energia * (1 + c.PERDITE) + c.DISPACCIAMENTO + c.TRASPORTO + c.ONERI + c.ACCISE) * (1 + c.IVA)
end

-- componenti del costo di un kWh prelevato (EUR/kWh, IVA compresa in ogni voce) per i grafici
function M.componenti(c, energia)
  local k = 1 + c.IVA
  return { energia = energia * k, perdite = energia * c.PERDITE * k, dispacciamento = c.DISPACCIAMENTO * k,
           trasporto = c.TRASPORTO * k, oneri = c.ONERI * k, accise = c.ACCISE * k,
           totale = M.costo_da_energia(c, energia) }
end

function M.valore_cessione(c, nord)
  return nord * (1 - c.IMPOSTA_CESSIONI)
end

-- parte "energia" oraria dal file (se configurato): { "AAAAMMGG": [24 valori EUR/kWh] }
local orari, letto = nil, false
local function energia_oraria(c, t)
  if not c.PREZZO_ENERGIA_ORARIO_FILE then return nil end
  if not letto then
    letto = true
    local nome = c.PREZZO_ENERGIA_ORARIO_FILE
    local cart = c.CARTELLA_DATI or os.getenv("EMS_DATI")
    local testo = F.leggi(nome) or (cart and F.leggi(cart .. "/" .. nome))
    if testo then
      local ok, d = pcall(J.decode, testo)
      if ok and type(d) == "table" then orari = d end
    end
  end
  if not orari then return nil end
  local cal = T.calendario(t)
  local g = tostring(cal.giorno or ""):gsub("-", "")
  local v = orari[g]
  return v and tonumber(v[(cal.ora or 0) + 1]) or nil
end

-- energia usata per l'istante t: oraria se disponibile, altrimenti prezzo fisso F0
function M.energia(c, t)
  return energia_oraria(c, t) or c.PREZZO_FISSO_A
end

-- costo d'acquisto di ogni profilo per un istante t (uguale per tutti i profili)
function M.costi(c, t)
  local cal = T.calendario(t)
  local v = M.costo_da_energia(c, M.energia(c, t))
  local r = {}
  for _, p in ipairs(c.PROFILI) do r[p] = v end
  return r, nil, cal.fascia
end

-- compatibilita' (modo "prova" di ems_sim.lua): i prezzi di acquisto non dipendono dal GME
function M.aggiungi_giorno() end

return M
