-- gme.lua - prezzi MGP dal servizio API del GME: NORD e PUN, orari (decisioni) e a 15 minuti (registro)
-- File salvato: prezzi_AAAAMMGG.json con valori in EUR/kWh
--   ore[h]    = { nord = ..., pun = ... }   h = ora GME 1..23/24/25
--   quarti[q] = { nord = ..., pun = ... }   q = quarto GME 1..92/96/100 (se disponibili)
local J = require "lib_json"
local H = require "lib_http"
local Z = require "lib_zip"
local T = require "lib_tempo"
local F = require "lib_file"
local M = {}

local function campo(d, nome)
  if type(d) ~= "table" then return nil end
  if d[nome] ~= nil then return d[nome] end
  local n = nome:lower()
  for k, v in pairs(d) do
    if (tostring(k):lower():gsub(" ", "")) == n then return v end
  end
  return nil
end

local function numero(v)
  if type(v) == "number" then return v end
  if type(v) ~= "string" then return nil end
  local s = v:gsub("^%s+", ""):gsub("%s+$", "")
  if s:find(",") and s:find("%.") then s = s:gsub("%.", ""):gsub(",", ".")
  else s = s:gsub(",", ".") end
  return tonumber(s)
end

function M.file(cartella, giorno) return cartella .. "/prezzi_" .. giorno .. ".json" end

function M.carica(cartella, giorno)
  local t = F.leggi(M.file(cartella, giorno))
  if not t then return nil end
  local ok, d = pcall(J.decode, t)
  if ok and type(d) == "table" and type(d.ore) == "table" and #d.ore > 0 then return d end
  return nil
end

local function token_gme(c, cartella)
  local t = F.leggi(cartella .. "/gme_credenziali.json")
  if not t then error("manca gme_credenziali.json nella cartella del programma", 0) end
  local cred = J.decode(t)
  local a = H.post_json(c.URL_API_GME .. "/Auth", { Login = cred.Login, Password = cred.Password })
  local tok = campo(a, "token")
  if not campo(a, "Success") or not tok or tok == "" then
    error("accesso al GME non riuscito: " .. tostring(campo(a, "Reason")) ..
      " (la password GME scade ogni 6 mesi: si cambia su https://api.mercatoelettrico.org/users/)", 0)
  end
  return tok
end

local function richiedi(c, token, giorno, gran, cartella_prezzi, log)
  local r = H.post_json(c.URL_API_GME .. "/RequestData", {
    Platform = "PublicMarketResults", Segment = "MGP", DataName = "ME_ZonalPrices",
    IntervalStart = tonumber(giorno), IntervalEnd = tonumber(giorno),
    Attributes = { GranularityType = gran } }, { "Authorization: Bearer " .. token }, 120)
  local contenuto = campo(r, "ContentResponse")
  if not contenuto or contenuto == "" then
    error("nessun dato GME " .. gran .. " per il " .. giorno .. ": " .. tostring(campo(r, "ResultRequest")), 0)
  end
  local testo
  for _, x in ipairs(Z.estrai(Z.base64_decode(contenuto))) do
    if x.nome:lower():match("%.json$") then testo = x.dati; break end
  end
  if not testo then error("lo zip del GME non contiene un file JSON", 0) end
  F.scrivi(cartella_prezzi .. "/grezzo_" .. giorno .. "_" .. gran .. ".json", testo)
  local per, note = {}, {}
  for _, x in ipairs(J.decode(testo)) do
    local nota = campo(x, "Notes")
    if type(nota) == "string" and nota:match("%S") then note[nota] = true end
    local fd = tostring(campo(x, "FlowDate") or "")
    local zona = (tostring(campo(x, "Zone") or ""):upper():gsub("%s", ""))
    local p = numero(campo(x, "Period"))
    if gran == "PT60" and not p then p = numero(campo(x, "Hour")) end
    local prezzo = numero(campo(x, "Price"))
    if (fd == "" or fd == giorno) and (zona == c.ZONA or zona == "PUN") and p and p >= 1 and prezzo then
      per[math.floor(p)] = per[math.floor(p)] or {}
      per[math.floor(p)][zona == "PUN" and "pun" or "nord"] = prezzo / 1000      -- EUR/MWh -> EUR/kWh
    end
  end
  for n in pairs(note) do log("Nota GME (" .. gran .. "): " .. n) end
  return per
end

-- scarica i prezzi del giorno "AAAAMMGG" e li salva; ritorna la tabella
function M.scarica(c, cartella, cartella_prezzi, giorno, log)
  local token = token_gme(c, cartella)
  local n_ore = T.ore_del_giorno(giorno)
  local ore = richiedi(c, token, giorno, "PT60", cartella_prezzi, log)
  for h = 1, n_ore do
    if not (ore[h] and ore[h].nord and ore[h].pun) then
      error(string.format("prezzo NORD o PUN dell'ora %d mancante (attese %d ore): dati del %s non usati", h, n_ore, giorno), 0)
    end
  end
  if ore[n_ore + 1] then error("ore in eccesso nei dati GME del " .. giorno, 0) end
  local quarti = {}
  local ok, q = pcall(richiedi, c, token, giorno, "PT15", cartella_prezzi, log)
  if ok then
    local completo = true
    for k = 1, n_ore * 4 do if not (q[k] and q[k].nord) then completo = false end end
    if completo then quarti = q else log("Prezzi a 15 minuti incompleti: registro solo quelli orari") end
  else
    log("Prezzi a 15 minuti non disponibili (" .. tostring(q) .. "): registro solo quelli orari")
  end
  local d = { giorno = giorno, scaricato_il = T.testo(nil, "%Y-%m-%dT%H:%M:%S"), unita = "EUR/kWh",
              zona = c.ZONA, ore = {}, quarti = {} }
  local mx, mn = -1e9, 1e9
  for h = 1, n_ore do
    d.ore[h] = { nord = ore[h].nord, pun = ore[h].pun }
    mx, mn = math.max(mx, ore[h].nord), math.min(mn, ore[h].nord)
  end
  for k = 1, #quarti do d.quarti[k] = { nord = quarti[k].nord, pun = quarti[k].pun } end
  F.scrivi(M.file(cartella_prezzi, giorno), J.encode(d))
  log(string.format("Prezzi GME del %s salvati: %d ore, NORD da %.4f a %.4f EUR/kWh%s", giorno, n_ore, mn, mx,
    (#d.quarti > 0) and ", con quarti d'ora" or ""))
  return d
end

return M
