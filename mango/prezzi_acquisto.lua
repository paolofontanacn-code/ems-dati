-- prezzi_acquisto.lua - costo del kWh prelevato per i profili A, B, C e valore del kWh ceduto
--   costo = [energia x (1 + PERDITE) + DISPACCIAMENTO + TRASPORTO + ONERI + ACCISE] x (1 + IVA)
--   A: energia = PREZZO_FISSO_A
--   B: energia = PUN medio mensile della fascia + SPREAD_B   (stimato con i giorni del mese gia' pubblicati)
--   C: energia = PUN orario + SPREAD_C
--   cessione = NORD orario x (1 - IMPOSTA_CESSIONI)
local T = require "lib_tempo"
local M = {}

function M.costo_da_energia(c, energia)
  return (energia * (1 + c.PERDITE) + c.DISPACCIAMENTO + c.TRASPORTO + c.ONERI + c.ACCISE) * (1 + c.IVA)
end

function M.valore_cessione(c, nord)
  return nord * (1 - c.IMPOSTA_CESSIONI)
end

-- aggiorna le medie mensili del PUN per fascia con i prezzi orari di un giorno (una sola volta per giorno)
-- archivio: stato.pun_fasce = { ["AAAAMM"] = { F1 = {s=, n=}, F2 = ..., F3 = ..., giorni = { ["AAAAMMGG"] = true } } }
function M.aggiungi_giorno(stato, prezzi)
  stato.pun_fasce = stato.pun_fasce or {}
  local g = prezzi.giorno
  local mese = g:sub(1, 6)
  local m = stato.pun_fasce[mese] or { F1 = { s = 0, n = 0 }, F2 = { s = 0, n = 0 }, F3 = { s = 0, n = 0 }, giorni = {} }
  stato.pun_fasce[mese] = m
  if m.giorni[g] then return end
  local m0 = T.mezzanotte(g)
  for h, x in ipairs(prezzi.ore) do
    local f = T.calendario(m0 + (h - 1) * 3600 + 60).fascia
    m[f].s = m[f].s + x.pun
    m[f].n = m[f].n + 1
  end
  m.giorni[g] = true
  -- tiene solo gli ultimi 3 mesi
  local mesi = {}
  for k in pairs(stato.pun_fasce) do mesi[#mesi + 1] = k end
  table.sort(mesi)
  for i = 1, #mesi - 3 do stato.pun_fasce[mesi[i]] = nil end
end

-- PUN medio della fascia del mese (stima con i dati disponibili). Ritorna valore, nota
function M.pun_fascia(stato, mese, fascia, pun_ora)
  local m = (stato.pun_fasce or {})[mese]
  if m and m[fascia].n > 0 then return m[fascia].s / m[fascia].n, "media mese" end
  -- mese precedente, stessa fascia
  local a, mm = tonumber(mese:sub(1, 4)), tonumber(mese:sub(5, 6))
  mm = mm - 1
  if mm == 0 then a, mm = a - 1, 12 end
  local prec = (stato.pun_fasce or {})[string.format("%04d%02d", a, mm)]
  if prec and prec[fascia].n > 0 then return prec[fascia].s / prec[fascia].n, "media mese precedente" end
  if m then
    local s, n = 0, 0
    for _, f in ipairs({ "F1", "F2", "F3" }) do s, n = s + m[f].s, n + m[f].n end
    if n > 0 then return s / n, "media mese tutte le fasce" end
  end
  return pun_ora, "PUN orario (nessuna media disponibile)"
end

-- costi dei tre profili per un istante t con prezzi orari (nord, pun in EUR/kWh)
function M.costi(c, stato, t, pun)
  local cal = T.calendario(t)
  local mese = cal.giorno:sub(1, 6)
  local pf = M.pun_fascia(stato, mese, cal.fascia, pun)
  return {
    A = M.costo_da_energia(c, c.PREZZO_FISSO_A),
    B = M.costo_da_energia(c, pf + c.SPREAD_B),
    C = M.costo_da_energia(c, pun + c.SPREAD_C),
  }, pf, cal.fascia
end

return M
