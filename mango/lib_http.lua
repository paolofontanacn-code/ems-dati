-- lib_http.lua - richieste HTTPS tramite il programma curl del router
local J = require "lib_json"
local M = {}

local function q(s)   -- quoting sicuro per la shell
  return "'" .. tostring(s):gsub("'", "'\\''") .. "'"
end

local function leggi(nome)
  local f = io.open(nome, "rb")
  if not f then return "" end
  local t = f:read("*a")
  f:close()
  return t
end

function M.urlencode(t)
  local parti = {}
  for k, v in pairs(t) do
    local function enc(s)
      return (tostring(s):gsub("[^%w%-%._~]", function(c) return string.format("%%%02X", c:byte()) end))
    end
    parti[#parti + 1] = enc(k) .. "=" .. enc(v)
  end
  table.sort(parti)
  return table.concat(parti, "&")
end

-- richiesta generica; corpo = stringa gia' codificata o nil. Ritorna codice_http, testo_risposta (oppure errore Lua)
-- statistiche delle chiamate (per misurare il carico del Mango): per servizio numero, byte, secondi
M.stat = {}
local function servizio(url)
  if url:find("fusionsolar") or url:find("/hw") or url:find("/oauth") then return "huawei" end
  if url:find("mercatoelettrico") or url:find("/gme") then return "gme" end
  if url:find("open%-meteo") or url:find("/meteo") then return "meteo" end
  if url:find("github") or url:find("/gh") then return "github" end
  return "altro"
end

function M.richiesta(metodo, url, corpo, intestazioni, timeout)
  local f_in, f_out, f_err = os.tmpname(), os.tmpname(), os.tmpname()
  local cmd = { "curl -sS --max-time", tostring(timeout or 60), "-o", q(f_out), "-w '%{http_code} %{time_total}' -X", metodo }
  for _, h in ipairs(intestazioni or {}) do cmd[#cmd + 1] = "-H " .. q(h) end
  if corpo then
    local f = assert(io.open(f_in, "wb"))
    f:write(corpo)
    f:close()
    cmd[#cmd + 1] = "--data-binary @" .. q(f_in)
  end
  cmd[#cmd + 1] = q(url)
  cmd[#cmd + 1] = "2>" .. q(f_err)
  local p = io.popen(table.concat(cmd, " "))
  local uscita = p:read("*a") or ""
  p:close()
  local codice, durata = uscita:match("^%s*(%d+)%s*([%d%.]*)")
  local risposta, err = leggi(f_out), leggi(f_err)
  os.remove(f_in); os.remove(f_out); os.remove(f_err)
  codice = tonumber(codice)
  if not codice or codice == 0 then
    local nota = ""
    if err:find("certificate") or err:find("SSL") then
      nota = " (certificati: installare ca-bundle con  opkg update && opkg install ca-bundle)"
    elseif err:find("not found") then
      nota = " (manca curl: opkg update && opkg install curl ca-bundle)"
    end
    error("rete: " .. (err ~= "" and err:gsub("%s+$", "") or "nessuna risposta") .. " verso " .. url .. nota, 0)
  end
  local sv = servizio(url)
  local st = M.stat[sv] or { n = 0, inviati = 0, ricevuti = 0, secondi = 0 }
  st.n = st.n + 1
  st.inviati = st.inviati + #(corpo or "")
  st.ricevuti = st.ricevuti + #risposta
  st.secondi = st.secondi + (tonumber(durata) or 0)
  M.stat[sv] = st
  return codice, risposta
end

function M.post(url, corpo, intestazioni, timeout)
  return M.richiesta("POST", url, corpo or "", intestazioni, timeout)
end

function M.get(url, intestazioni, timeout)
  return M.richiesta("GET", url, nil, intestazioni, timeout)
end

-- POST con corpo JSON; ritorna la tabella decodificata
function M.post_json(url, tabella, intestazioni, timeout)
  local h = { "Content-Type: application/json", "Accept: application/json" }
  for _, x in ipairs(intestazioni or {}) do h[#h + 1] = x end
  local codice, testo = M.post(url, J.encode(tabella), h, timeout)
  if codice >= 400 then error(string.format("HTTP %d da %s: %s", codice, url, testo:sub(1, 300)), 0) end
  local ok, dati = pcall(J.decode, testo)
  if not ok then error("risposta non JSON da " .. url .. ": " .. testo:sub(1, 200), 0) end
  return dati
end

-- POST form-urlencoded (OAuth); ritorna la tabella decodificata (anche con codice di errore)
function M.post_form(url, campi, timeout)
  local codice, testo = M.post(url, M.urlencode(campi),
    { "Content-Type: application/x-www-form-urlencoded", "Accept: application/json" }, timeout)
  local ok, dati = pcall(J.decode, testo)
  if not ok then error(string.format("HTTP %d, risposta non JSON da %s: %s", codice, url, testo:sub(1, 200)), 0) end
  return dati, codice
end

M.q = q
return M
