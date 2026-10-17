-- lib_file.lua - file, cartelle, CSV e compressione
local M = {}

local function q(s) return "'" .. tostring(s):gsub("'", "'\\''") .. "'" end
M.q = q

function M.leggi(nome)
  local f = io.open(nome, "rb")
  if not f then return nil end
  local t = f:read("*a")
  f:close()
  return t
end

-- conteggio dei byte scritti nella "memoria interna" (cartella dati): serve a stimare l'usura della flash
M.scritti = 0
M.prefisso_conteggio = nil
local function conta(nome, n)
  if M.prefisso_conteggio and nome:sub(1, #M.prefisso_conteggio) == M.prefisso_conteggio then M.scritti = M.scritti + n end
end

-- scrittura atomica (file temporaneo + rinomina)
function M.scrivi(nome, testo)
  conta(nome, #testo)
  local tmp = nome .. ".tmp"
  local f = assert(io.open(tmp, "wb"))
  f:write(testo)
  f:close()
  assert(os.rename(tmp, nome))
end

function M.accoda(nome, testo)
  conta(nome, #testo)
  local f = assert(io.open(nome, "ab"))
  f:write(testo)
  f:close()
end

function M.esiste(nome)
  local f = io.open(nome, "rb")
  if f then f:close(); return true end
  return false
end

function M.cartella(nome)
  os.execute("mkdir -p " .. q(nome))
end

function M.elenco(cartella, schema)
  local out = {}
  local p = io.popen("ls -1 " .. q(cartella) .. " 2>/dev/null")
  for riga in p:lines() do
    if not schema or riga:match(schema) then out[#out + 1] = riga end
  end
  p:close()
  table.sort(out)
  return out
end

function M.spazio_libero_kb(cartella)
  local p = io.popen("df -k " .. q(cartella) .. " 2>/dev/null | tail -1")
  local riga = p:read("*a") or ""
  p:close()
  local disp = riga:match("^%S+%s+%d+%s+%d+%s+(%d+)")
  return tonumber(disp)
end

-- comprime con gzip se disponibile; ritorna il nome del file prodotto
function M.gzip(nome)
  local ok = os.execute("gzip -c " .. q(nome) .. " > " .. q(nome .. ".gz") .. " 2>/dev/null")
  if (ok == 0 or ok == true) and M.esiste(nome .. ".gz") then
    local t = M.leggi(nome .. ".gz")
    if t and #t > 0 then return nome .. ".gz" end
  end
  os.remove(nome .. ".gz")
  return nil
end

-- ------------------------------------------------------------------ CSV (separatore virgola, decimale punto)
local function campo_csv(v)
  if v == nil then return "" end
  if type(v) == "boolean" then return v and "1" or "0" end
  if type(v) == "number" then
    if v ~= v then return "" end
    if v % 1 == 0 and math.abs(v) < 1e15 then return string.format("%d", v) end
    return (string.format("%.6f", v):gsub("0+$", ""):gsub("%.$", ""))
  end
  local s = tostring(v)
  if s:find('[,"\n\r]') then s = '"' .. s:gsub('"', '""') .. '"' end
  return s
end

function M.riga_csv(colonne, valori)
  local parti = {}
  for i, c in ipairs(colonne) do parti[i] = campo_csv(valori[c]) end
  return table.concat(parti, ",") .. "\n"
end

function M.intestazione_csv(colonne)
  return table.concat(colonne, ",") .. "\n"
end

return M
