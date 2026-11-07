-- Revisione R07 - 31/10/2026 - tolte le medie del PUN per fascia (si usa solo il prezzo fisso F0)
-- prezzi_acquisto.lua - costo del kWh prelevato e valore del kWh ceduto
--   costo = [PREZZO_FISSO_A x (1 + PERDITE) + DISPACCIAMENTO + TRASPORTO + ONERI + ACCISE] x (1 + IVA), uguale per
--   tutti i profili (prezzo fisso F0); cessione = NORD x (1 - IMPOSTA_CESSIONI)
local T = require "lib_tempo"
local M = {}

function M.costo_da_energia(c, energia)
  return (energia * (1 + c.PERDITE) + c.DISPACCIAMENTO + c.TRASPORTO + c.ONERI + c.ACCISE) * (1 + c.IVA)
end

function M.valore_cessione(c, nord)
  return nord * (1 - c.IMPOSTA_CESSIONI)
end

-- costo d'acquisto di ogni profilo per un istante t (prezzo fisso: uguale per tutti)
function M.costi(c, t)
  local cal = T.calendario(t)
  local v = M.costo_da_energia(c, c.PREZZO_FISSO_A)
  local r = {}
  for _, p in ipairs(c.PROFILI) do r[p] = v end
  return r, nil, cal.fascia
end

return M
