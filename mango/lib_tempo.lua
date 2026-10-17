-- lib_tempo.lua - ora italiana calcolata da UTC (non dipende dal fuso orario impostato sul router)
-- Regola UE: ora legale dall'ultima domenica di marzo all'ultima domenica di ottobre, cambio alle 01:00 UTC.
local M = {}
local floor = math.floor

-- giorni dal 1970-01-01 per una data del calendario gregoriano (algoritmo "days from civil")
local function giorni_da_civile(a, m, g)
  if m <= 2 then a = a - 1 end
  local era = floor(a / 400)
  local yoe = a - era * 400
  local mp = (m + 9) % 12
  local doy = floor((153 * mp + 2) / 5) + g - 1
  local doe = yoe * 365 + floor(yoe / 4) - floor(yoe / 100) + doy
  return era * 146097 + doe - 719468
end

function M.epoca_utc(a, m, g, h, mi, s)
  return giorni_da_civile(a, m, g) * 86400 + (h or 0) * 3600 + (mi or 0) * 60 + (s or 0)
end

-- giorno della settimana: 0 = domenica
local function settimana(a, m, g)
  return (giorni_da_civile(a, m, g) + 4) % 7
end

local function giorni_mese(a, m)
  local gm = { 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 }
  if m == 2 and ((a % 4 == 0 and a % 100 ~= 0) or a % 400 == 0) then return 29 end
  return gm[m]
end

local function ultima_domenica(a, m)
  local g = giorni_mese(a, m)
  return g - settimana(a, m, g)
end

-- scarto in secondi dell'ora italiana rispetto a UTC per un istante (epoca)
function M.scarto(t)
  local a = tonumber(os.date("!%Y", t))
  local inizio = M.epoca_utc(a, 3, ultima_domenica(a, 3), 1)
  local fine = M.epoca_utc(a, 10, ultima_domenica(a, 10), 1)
  if t >= inizio and t < fine then return 7200 end
  return 3600
end

-- istante attuale (EMS_ORA permette di simulare l'orario nelle prove)
M.ora_forzata = nil      -- usata in modalita' GitHub per rigiocare le letture dello storico
function M.adesso()
  return M.ora_forzata or tonumber(os.getenv("EMS_ORA") or "") or os.time()
end

-- tabella con anno, mese, giorno, ora, minuto, secondo italiani
function M.italia(t)
  t = t or M.adesso()
  local s = M.scarto(t)
  local d = os.date("!*t", t + s)
  d.scarto = s
  d.epoca = t
  return d
end

function M.testo(t, formato)
  t = t or M.adesso()
  return os.date("!" .. (formato or "%Y-%m-%d %H:%M:%S"), t + M.scarto(t))
end

-- "YYYYMMDD" del giorno italiano di t, piu' eventuali giorni di differenza
function M.giorno(t, delta)
  local d = M.italia(t)
  local e = M.epoca_utc(d.year, d.month, d.day, 12) + (delta or 0) * 86400
  return os.date("!%Y%m%d", e)
end

-- istante UTC della mezzanotte italiana del giorno "YYYYMMDD"
function M.mezzanotte(giorno)
  local a, m, g = tonumber(giorno:sub(1, 4)), tonumber(giorno:sub(5, 6)), tonumber(giorno:sub(7, 8))
  local u = M.epoca_utc(a, m, g)
  return u - M.scarto(u - 3600)
end

-- numero di ore del giorno italiano (23, 24 o 25)
function M.ore_del_giorno(giorno)
  local a, m, g = tonumber(giorno:sub(1, 4)), tonumber(giorno:sub(5, 6)), tonumber(giorno:sub(7, 8))
  local dopo = os.date("!%Y%m%d", M.epoca_utc(a, m, g, 12) + 86400)
  return floor((M.mezzanotte(dopo) - M.mezzanotte(giorno)) / 3600 + 0.5)
end

-- ora del giorno come numerata dal GME (1 = 00:00-01:00; nel giorno di 25 ore la 02-03 compare due volte)
function M.ora_gme(t)
  t = t or M.adesso()
  local giorno = M.giorno(t)
  return floor((t - M.mezzanotte(giorno)) / 3600) + 1, giorno
end

-- inizio ISO con scarto dell'ora GME n del giorno
function M.inizio_ora_iso(giorno, n)
  local t = M.mezzanotte(giorno) + (n - 1) * 3600
  local s = M.scarto(t)
  return os.date("!%Y-%m-%dT%H:%M:%S", t + s) .. string.format("+%02d:00", s / 3600), os.date("!%H:%M", t + s)
end

-- ------------------------------------------------------------------ calendario
-- Pasqua (calendario gregoriano, algoritmo anonimo): ritorna mese, giorno
local function pasqua(a)
  local A, B, C = a % 19, floor(a / 100), a % 100
  local D, E = floor(B / 4), B % 4
  local F = floor((B + 8) / 25)
  local G = floor((B - F + 1) / 3)
  local H = (19 * A + B - D - G + 15) % 30
  local I, K = floor(C / 4), C % 4
  local L = (32 + 2 * E + 2 * I - H - K) % 7
  local Mm = floor((A + 11 * H + 22 * L) / 451)
  local mese = floor((H + L - 7 * Mm + 114) / 31)
  local giorno = (H + L - 7 * Mm + 114) % 31 + 1
  return mese, giorno
end

-- festivita' nazionali italiane (non comprende il santo patrono locale)
function M.festivo(a, m, g)
  local fissi = { ["1-1"] = 1, ["1-6"] = 1, ["4-25"] = 1, ["5-1"] = 1, ["6-2"] = 1, ["8-15"] = 1,
                  ["11-1"] = 1, ["12-8"] = 1, ["12-25"] = 1, ["12-26"] = 1 }
  if fissi[m .. "-" .. g] then return true end
  -- 4 ottobre (San Francesco d'Assisi): festivo nelle fasce orarie dal 2026 (ARERA 338/2026/R/eel)
  if a >= 2026 and m == 10 and g == 4 then return true end
  local pm, pg = pasqua(a)
  local lunedi = giorni_da_civile(a, pm, pg) + 1
  return giorni_da_civile(a, m, g) == lunedi or giorni_da_civile(a, m, g) == lunedi - 1
end

-- informazioni di calendario per un istante: tipo di giorno, fascia ARERA, quarto d'ora
function M.calendario(t)
  local d = M.italia(t)
  local sett = settimana(d.year, d.month, d.day)          -- 0 = domenica
  local fest = M.festivo(d.year, d.month, d.day)
  local tipo_fascia = (sett == 0 or fest) and "festivo" or (sett == 6 and "sabato" or "feriale")
  -- tipo di giorno per i profili di consumo: feriale, ponte, sabato, domenica, festivo (infrasettimanale)
  local tipo
  if sett == 0 then tipo = "domenica"
  elseif fest then tipo = "festivo"
  elseif sett == 6 then tipo = "sabato"
  else
    local e = giorni_da_civile(d.year, d.month, d.day)
    local function fest_e(x)
      local dd = os.date("!*t", x * 86400)
      local s2 = (x + 4) % 7
      return s2 == 0 or s2 == 6 or M.festivo(dd.year, dd.month, dd.day)
    end
    -- ponte: feriale isolato tra un giorno festivo/weekend e un altro (es. venerdi' dopo giovedi' festivo)
    local prima = fest_e(e - 1) and not ((e - 1 + 4) % 7 == 0 or (e - 1 + 4) % 7 == 6)
    local dopo = fest_e(e + 1) and not ((e + 1 + 4) % 7 == 0 or (e + 1 + 4) % 7 == 6)
    if (prima and fest_e(e + 1)) or (dopo and fest_e(e - 1)) then tipo = "ponte" else tipo = "feriale" end
  end
  local h = d.hour
  local fascia
  if tipo_fascia == "festivo" then fascia = "F3"
  elseif tipo_fascia == "sabato" then fascia = (h >= 7 and h < 23) and "F2" or "F3"
  elseif h >= 8 and h < 19 then fascia = "F1"
  elseif h == 7 or (h >= 19 and h < 23) then fascia = "F2"
  else fascia = "F3" end
  local giorno = string.format("%04d%02d%02d", d.year, d.month, d.day)
  return {
    giorno = giorno, anno = d.year, mese = d.month, gg = d.day, ora = h, minuto = d.min,
    settimana = (sett == 0) and 7 or sett,                  -- 1 = lunedi' ... 7 = domenica
    festivo = fest, tipo = tipo, fascia = fascia,
    giorno_sett = sett,
    quarto_orologio = floor((h * 60 + d.min) / 15) + 1,     -- 1..96 sull'ora dell'orologio
    quarto_gme = floor((t - M.mezzanotte(giorno)) / 900) + 1, -- numerazione GME (92/96/100 nel giorno)
    ora_gme = floor((t - M.mezzanotte(giorno)) / 3600) + 1,
    iso = os.date("!%Y-%m-%dT%H:%M:%S", t + d.scarto) .. string.format("+%02d:00", d.scarto / 3600),
  }
end

-- inizio (epoca) del quarto d'ora che contiene t
function M.inizio_quarto(t)
  local g = M.giorno(t)
  local m0 = M.mezzanotte(g)
  return m0 + floor((t - m0) / 900) * 900
end

return M
