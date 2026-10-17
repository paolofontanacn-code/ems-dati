-- benchmark_mango.lua - misura la velocita' di calcolo con un carico FISSO e sempre uguale
-- Si lancia sia su GitHub (ad ogni giro, file misure/benchmark_github.txt) sia una volta sul Mango in SSH:
--   lua benchmark_mango.lua
-- FATTORE_MANGO = secondi sul Mango / secondi su GitHub  -> da scrivere in config.lua
-- Il carico e' quello tipico di un ciclo: 288 passi del modello batteria, un piano dell'ottimizzatore
-- (3 profili, 136 quarti d'ora) e lettura/scrittura JSON di dimensione simile a stato e modelli.
local CARTELLA = (arg and arg[0] or ""):match("^(.*)/[^/]*$") or "."
package.path = CARTELLA .. "/?.lua;" .. package.path
local J = require "lib_json"
local S = require "simulatore"
local O = require "ottimizzatore"
local c = dofile(CARTELLA .. "/config.lua")

local e = { c = 0.95, d = 0.97, inv = { 0.9, 0.95, 0.97, 0.97 } }
local function orologio() return os.clock() end

local risultati = {}
local t0 = orologio()

-- 1) modello batteria: 288 passi x 4 scenari
local soc = 50
for k = 1, 288 * 4 do
  local h = (k % 288) / 12
  local fv = (h > 7 and h < 18) and 4000 * math.sin(math.pi * (h - 7) / 11) or 0
  local r = S.passo(c, e, soc, (k % 3 == 0) and "AUTO" or "RITARDATA", fv, 900 + (k % 7) * 100, 5 / 60, fv > 100)
  soc = r.soc
end
local t1 = orologio()
risultati.batteria_s = t1 - t0

-- 2) ottimizzatore: 136 quarti d'ora, 3 profili
local quarti = {}
for k = 1, 136 do
  local h = ((14 * 60 + (k - 1) * 15) % 1440) / 60
  local fv = (h > 7 and h < 18) and 6000 * math.sin(math.pi * (h - 7) / 11) or 0
  local car = 600 + ((h >= 18 and h < 23) and 1500 or 0) + ((h < 7) and 900 or 0)
  local nord = 0.11 + ((h >= 18 and h < 21) and 0.10 or 0)
  quarti[k] = { t = k * 900, giorno = (k <= 40) and "20990101" or "20990102", fv = fv, carico = car, di_giorno = fv >= 100,
    mezzanotte = (k == 41), vend = nord * 0.6, costo = { A = 0.223, B = 0.25, C = 0.24 + nord * 0.1 } }
end
local prof = {}
for _, p in ipairs({ "A", "B", "C" }) do prof[p] = { soc0 = 40, prev_azione = "AUTO", finestre_oggi = 0, giorno_oggi = "20990101" } end
local vf = {}
for _, p in ipairs({ "A", "B", "C" }) do vf[p] = { costo = 0.24, vend = 0.07, e_notte = 8 } end
O.pianifica(c, e, quarti, { "A", "B", "C" }, prof, 0.0667, vf)
local t2 = orologio()
risultati.ottimizzatore_s = t2 - t1

-- 3) JSON: struttura di circa 150 kB codificata e decodificata 3 volte
local grande = { giorni = {} }
for g = 1, 120 do
  local comp = {}
  for q = 1, 96 do comp[q] = 500 + (g * q) % 700 + 0.123 end
  grande.giorni[g] = { g = string.format("2099%04d", g), tipo = "feriale", tmed = 10.5, comp = comp }
end
for _ = 1, 3 do grande = J.decode(J.encode(grande)) end
local t3 = orologio()
risultati.json_s = t3 - t2

risultati.totale_s = t3 - t0
print(string.format("BENCHMARK totale %.3f s  (batteria %.3f s, ottimizzatore %.3f s, json %.3f s)",
  risultati.totale_s, risultati.batteria_s, risultati.ottimizzatore_s, risultati.json_s))
print("Lua: " .. tostring(_VERSION) .. "  memoria " .. string.format("%.0f kB", collectgarbage("count")))
