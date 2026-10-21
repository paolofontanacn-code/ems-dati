-- meteo.lua - meteo osservato/previsto da Open-Meteo (gratuito, senza account)
-- Variabili orarie: temperatura, umidita', nuvolosita', irraggiamento globale orizzontale (GHI), vento, pioggia.
-- Con piu' modelli meteo calcola media e dispersione (incertezza).
-- Convenzione Open-Meteo: temperatura/umidita'/nuvole/vento istantanei all'ora indicata;
-- irraggiamento e pioggia = media/somma dell'ora PRECEDENTE.
local J = require "lib_json"
local H = require "lib_http"
local M = {}

local VARIABILI = { "temperature_2m", "relative_humidity_2m", "cloud_cover", "shortwave_radiation",
                    "wind_speed_10m", "precipitation" }
local NOMI = { temperature_2m = "temp", relative_humidity_2m = "umid", cloud_cover = "nuvole",
               shortwave_radiation = "ghi", wind_speed_10m = "vento", precipitation = "pioggia" }

-- trasforma la risposta in { [epoca_ora] = { temp=, umid=, nuvole=, ghi=, vento=, pioggia=, ghi_disp=, temp_disp=, n_modelli= } }
local function interpreta(r)
  local h = r.hourly or {}
  local tempi = h.time or {}
  local out = {}
  for i, t in ipairs(tempi) do
    local x = {}
    local n_mod = 0
    for _, v in ipairs(VARIABILI) do
      local valori = {}
      for k, serie in pairs(h) do
        if (k == v or k:sub(1, #v + 1) == v .. "_") and type(serie) == "table" then
          -- esclude variabili diverse con lo stesso prefisso (es. temperature_2m_max)
          local suffisso = k:sub(#v + 2)
          if k == v or not suffisso:match("^m[ia][nx]") then
            local val = serie[i]
            if type(val) == "number" then valori[#valori + 1] = val end
          end
        end
      end
      if #valori > 0 then
        local s = 0
        for _, val in ipairs(valori) do s = s + val end
        local media = s / #valori
        local d = 0
        for _, val in ipairs(valori) do d = d + (val - media) ^ 2 end
        x[NOMI[v]] = media
        x[NOMI[v] .. "_disp"] = (#valori > 1) and math.sqrt(d / (#valori - 1)) or 0
        n_mod = math.max(n_mod, #valori)
      end
    end
    x.n_modelli = n_mod
    out[tonumber(t)] = x
  end
  return out
end

local function url(base, c, lat, lon, extra)
  return string.format("%s?latitude=%.4f&longitude=%.4f&hourly=%s&timeformat=unixtime&timezone=GMT%s",
    base, lat, lon, table.concat(VARIABILI, ","), extra or "")
end

local function scarica(u)
  -- attesa breve e un secondo tentativo dopo 10 s solo per errori di rete (visti timeout da GitHub)
  local ok0, codice, testo = pcall(H.get, u, { "Accept: application/json" }, 25)
  if not ok0 and tostring(codice):match("^rete:") then
    os.execute("sleep 10")
    ok0, codice, testo = pcall(H.get, u, { "Accept: application/json" }, 25)
  end
  if not ok0 then error(codice, 0) end
  local ok, r = pcall(J.decode, testo)
  if codice ~= 200 or not ok then
    error(string.format("Open-Meteo HTTP %s: %s", tostring(codice), (testo or ""):sub(1, 200)), 0)
  end
  if r.error then error("Open-Meteo: " .. tostring(r.reason), 0) end
  return r
end

-- previsioni: ieri + 3 giorni; prima con piu' modelli, se rifiutato con il modello predefinito
function M.previsioni(c, lat, lon, log)
  local base = "&past_days=1&forecast_days=3"
  local ok, r = pcall(scarica, url(c.URL_METEO, c, lat, lon, base .. "&models=" .. c.MODELLI_METEO))
  if not ok then
    log("Meteo multi-modello non disponibile (" .. tostring(r) .. "): uso il modello predefinito")
    r = scarica(url(c.URL_METEO, c, lat, lon, base))
  end
  return interpreta(r)
end

-- storico (archivio): date "AAAA-MM-GG"
function M.storico(c, lat, lon, da, a)
  return interpreta(scarica(url(c.URL_METEO_STORICO, c, lat, lon, "&start_date=" .. da .. "&end_date=" .. a)))
end

-- valori per l'intervallo [t, t+...) a partire dalla serie oraria
function M.istante(serie, t)
  if not serie then return nil end
  local h0 = math.floor(t / 3600) * 3600
  local a, b = serie[h0], serie[h0 + 3600]
  if not a and not b then return nil end
  a, b = a or b, b or a
  local f = (t - h0) / 3600
  local function interp(k)
    if a[k] == nil and b[k] == nil then return nil end
    local va, vb = a[k] or b[k], b[k] or a[k]
    return va + (vb - va) * f
  end
  return {
    temp = interp("temp"), umid = interp("umid"), nuvole = interp("nuvole"), vento = interp("vento"),
    ghi = b.ghi or a.ghi, pioggia = b.pioggia or a.pioggia,          -- media/somma dell'ora che termina a h0+1h
    ghi_disp = b.ghi_disp or a.ghi_disp, temp_disp = interp("temp_disp"), n_modelli = b.n_modelli or a.n_modelli,
  }
end

-- temperatura media delle ultime "ore" ore (inerzia della casa)
function M.temp_media(serie, t, ore)
  if not serie then return nil end
  local s, n = 0, 0
  local h = math.floor(t / 3600) * 3600
  for k = 0, ore do
    local x = serie[h - k * 3600]
    if x and x.temp then s, n = s + x.temp, n + 1 end
  end
  if n == 0 then return nil end
  return s / n
end

-- tiene solo le ore in una finestra (riduce la memoria)
function M.ritaglia(serie, da, a)
  local out = {}
  for t, x in pairs(serie or {}) do
    if t >= da and t <= a then out[t] = x end
  end
  return out
end

-- serializzazione con chiavi stringa (JSON)
function M.a_testo(serie)
  local t = {}
  for k, v in pairs(serie or {}) do t[tostring(k)] = v end
  return t
end

function M.da_testo(t)
  local s = {}
  for k, v in pairs(t or {}) do s[tonumber(k)] = v end
  return s
end

return M
