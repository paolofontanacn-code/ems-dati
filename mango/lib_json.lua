-- lib_json.lua - JSON in Lua puro (Lua 5.1, nessuna libreria esterna)
local M = {}

-- ------------------------------------------------------------------ decodifica
local function errore(s, i, msg)
  error(string.format("JSON non valido (%s) vicino alla posizione %d: %s", msg, i, s:sub(i, i + 30)), 0)
end

local function salta_spazi(s, i)
  local _, f = s:find("^[ \t\r\n]*", i)
  return f + 1
end

local function utf8(cp)
  if cp < 0x80 then return string.char(cp) end
  if cp < 0x800 then
    return string.char(0xC0 + math.floor(cp / 0x40), 0x80 + cp % 0x40)
  end
  if cp < 0x10000 then
    return string.char(0xE0 + math.floor(cp / 0x1000), 0x80 + math.floor(cp / 0x40) % 0x40, 0x80 + cp % 0x40)
  end
  return string.char(0xF0 + math.floor(cp / 0x40000), 0x80 + math.floor(cp / 0x1000) % 0x40,
    0x80 + math.floor(cp / 0x40) % 0x40, 0x80 + cp % 0x40)
end

local ESCAPE = { ['"'] = '"', ["\\"] = "\\", ["/"] = "/", b = "\b", f = "\f", n = "\n", r = "\r", t = "\t" }

local leggi_valore

local function leggi_stringa(s, i)
  local parti, j = {}, i + 1
  while true do
    local k = s:find('["\\]', j)
    if not k then errore(s, i, "stringa non chiusa") end
    parti[#parti + 1] = s:sub(j, k - 1)
    if s:sub(k, k) == '"' then return table.concat(parti), k + 1 end
    local c = s:sub(k + 1, k + 1)
    if c == "u" then
      local cp = tonumber(s:sub(k + 2, k + 5), 16)
      if not cp then errore(s, k, "\\u non valido") end
      local avanti = 6
      if cp >= 0xD800 and cp <= 0xDBFF and s:sub(k + 6, k + 7) == "\\u" then
        local basso = tonumber(s:sub(k + 8, k + 11), 16)
        if basso and basso >= 0xDC00 and basso <= 0xDFFF then
          cp = 0x10000 + (cp - 0xD800) * 0x400 + (basso - 0xDC00)
          avanti = 12
        end
      end
      parti[#parti + 1] = utf8(cp)
      j = k + avanti
    elseif ESCAPE[c] then
      parti[#parti + 1] = ESCAPE[c]
      j = k + 2
    else
      errore(s, k, "escape non valido")
    end
  end
end

local function leggi_numero(s, i)
  local _, f = s:find("^-?%d+%.?%d*[eE]?[-+]?%d*", i)
  if not f then errore(s, i, "numero") end
  local n = tonumber(s:sub(i, f))
  if not n then errore(s, i, "numero") end
  return n, f + 1
end

M.null = setmetatable({}, { __tostring = function() return "null" end })

leggi_valore = function(s, i)
  i = salta_spazi(s, i)
  local c = s:sub(i, i)
  if c == "{" then
    local t = {}
    i = salta_spazi(s, i + 1)
    if s:sub(i, i) == "}" then return t, i + 1 end
    while true do
      if s:sub(i, i) ~= '"' then errore(s, i, "attesa chiave") end
      local k
      k, i = leggi_stringa(s, i)
      i = salta_spazi(s, i)
      if s:sub(i, i) ~= ":" then errore(s, i, "attesi due punti") end
      local v
      v, i = leggi_valore(s, i + 1)
      if v ~= M.null then t[k] = v end
      i = salta_spazi(s, i)
      local d = s:sub(i, i)
      if d == "}" then return t, i + 1 end
      if d ~= "," then errore(s, i, "attesa virgola") end
      i = salta_spazi(s, i + 1)
    end
  elseif c == "[" then
    local t, n = {}, 0
    i = salta_spazi(s, i + 1)
    if s:sub(i, i) == "]" then return t, i + 1 end
    while true do
      local v
      v, i = leggi_valore(s, i)
      n = n + 1
      if v ~= M.null then t[n] = v end
      i = salta_spazi(s, i)
      local d = s:sub(i, i)
      if d == "]" then return t, i + 1 end
      if d ~= "," then errore(s, i, "attesa virgola") end
      i = i + 1
    end
  elseif c == '"' then
    return leggi_stringa(s, i)
  elseif s:sub(i, i + 3) == "true" then
    return true, i + 4
  elseif s:sub(i, i + 4) == "false" then
    return false, i + 5
  elseif s:sub(i, i + 3) == "null" then
    return M.null, i + 4
  else
    return leggi_numero(s, i)
  end
end

function M.decode(s)
  if type(s) ~= "string" then error("JSON: testo mancante", 0) end
  if s:sub(1, 3) == "\239\187\191" then s = s:sub(4) end   -- BOM UTF-8
  local v, i = leggi_valore(s, 1)
  i = salta_spazi(s, i)
  if i <= #s then errore(s, i, "testo in eccesso") end
  if v == M.null then return nil end
  return v
end

-- ------------------------------------------------------------------ codifica
local function codifica_stringa(s)
  return '"' .. s:gsub('[%c"\\]', function(c)
    local e = { ['"'] = '\\"', ["\\"] = "\\\\", ["\n"] = "\\n", ["\r"] = "\\r", ["\t"] = "\\t" }
    return e[c] or string.format("\\u%04x", c:byte())
  end) .. '"'
end

local function e_lista(t)
  local n = 0
  for k in pairs(t) do
    if type(k) ~= "number" or k < 1 or k % 1 ~= 0 then return false end
    n = n + 1
  end
  for k = 1, n do if t[k] == nil then return false end end
  return true, n
end

local function codifica(v, rientro, livello)
  local tipo = type(v)
  if v == nil or v == M.null then return "null" end
  if tipo == "boolean" then return tostring(v) end
  if tipo == "number" then
    if v ~= v or v == math.huge or v == -math.huge then return "null" end
    if v % 1 == 0 and math.abs(v) < 1e15 then return string.format("%d", v) end
    return string.format("%.10g", v)
  end
  if tipo == "string" then return codifica_stringa(v) end
  if tipo ~= "table" then error("JSON: tipo non codificabile " .. tipo, 0) end
  local a_capo = rientro and ("\n" .. string.rep(rientro, livello + 1)) or ""
  local fine = rientro and ("\n" .. string.rep(rientro, livello)) or ""
  local lista, n = e_lista(v)
  local parti = {}
  if lista then
    if n == 0 and next(v) == nil then return "[]" end
    for k = 1, n do parti[k] = a_capo .. codifica(v[k], rientro, livello + 1) end
    return "[" .. table.concat(parti, ",") .. fine .. "]"
  end
  local chiavi = {}
  for k in pairs(v) do chiavi[#chiavi + 1] = tostring(k) end
  table.sort(chiavi)
  for _, k in ipairs(chiavi) do
    local val = v[k]
    if val == nil then val = v[tonumber(k)] end
    parti[#parti + 1] = a_capo .. codifica_stringa(k) .. (rientro and ": " or ":") .. codifica(val, rientro, livello + 1)
  end
  return "{" .. table.concat(parti, ",") .. fine .. "}"
end

function M.encode(v, rientro)
  return codifica(v, rientro, 0)
end

return M
