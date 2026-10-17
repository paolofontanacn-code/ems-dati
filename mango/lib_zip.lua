-- lib_zip.lua - base64, inflate (RFC 1951) e lettura file zip in Lua puro (Lua 5.1, senza operatori bit)
-- Serve per la risposta del GME: ContentResponse = zip codificato in base64 con data.json
local M = {}
local floor, char, byte = math.floor, string.char, string.byte

-- ------------------------------------------------------------------ base64
local B64 = {}
do
  local alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
  for i = 1, 64 do B64[byte(alfabeto, i)] = i - 1 end
  B64[byte("-")] = 62; B64[byte("_")] = 63      -- variante url-safe
end

function M.base64_decode(s)
  local out, n, acc, bits = {}, 0, 0, 0
  for i = 1, #s do
    local v = B64[byte(s, i)]
    if v then
      acc = acc * 64 + v
      bits = bits + 6
      if bits >= 8 then
        bits = bits - 8
        local p = 2 ^ bits
        local b = floor(acc / p)
        acc = acc - b * p
        n = n + 1
        out[n] = char(b)
      end
    end
  end
  return table.concat(out)
end


function M.base64_encode(s)
  local alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
  local out = {}
  for i = 1, #s, 3 do
    local a, b, c = byte(s, i, i + 2)
    local n = a * 65536 + (b or 0) * 256 + (c or 0)
    local c1, c2 = floor(n / 262144) % 64, floor(n / 4096) % 64
    local c3, c4 = floor(n / 64) % 64, n % 64
    out[#out + 1] = alfabeto:sub(c1 + 1, c1 + 1) .. alfabeto:sub(c2 + 1, c2 + 1) ..
      (b and alfabeto:sub(c3 + 1, c3 + 1) or "=") .. (c and alfabeto:sub(c4 + 1, c4 + 1) or "=")
  end
  return table.concat(out)
end

-- ------------------------------------------------------------------ inflate
local function nuovo_lettore(dati, inizio)
  return { s = dati, pos = inizio or 1, buf = 0, cnt = 0 }
end

local function bits(L, n)
  while L.cnt < n do
    local b = byte(L.s, L.pos)
    if not b then error("inflate: dati compressi terminati", 0) end
    L.pos = L.pos + 1
    L.buf = L.buf + b * 2 ^ L.cnt
    L.cnt = L.cnt + 8
  end
  local p = 2 ^ n
  local v = L.buf % p
  L.buf = floor(L.buf / p)
  L.cnt = L.cnt - n
  return v
end

-- tabella di Huffman canonica (come "puff" di zlib)
local function costruisci(lunghezze, n)
  local conta, simboli, offs = {}, {}, {}
  for l = 0, 15 do conta[l] = 0 end
  for s = 0, n - 1 do
    local l = lunghezze[s] or 0
    conta[l] = conta[l] + 1
  end
  offs[1] = 0
  for l = 1, 14 do offs[l + 1] = offs[l] + conta[l] end
  for s = 0, n - 1 do
    local l = lunghezze[s] or 0
    if l ~= 0 then
      simboli[offs[l]] = s
      offs[l] = offs[l] + 1
    end
  end
  return { conta = conta, simboli = simboli }
end

local function decodifica(L, h)
  local codice, primo, indice = 0, 0, 0
  for l = 1, 15 do
    codice = codice + bits(L, 1)
    local c = h.conta[l]
    if codice - c < primo then return h.simboli[indice + (codice - primo)] end
    indice = indice + c
    primo = (primo + c) * 2
    codice = codice * 2
  end
  error("inflate: codice di Huffman non valido", 0)
end

local LBASE = { 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258 }
local LEXT = { 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0 }
local DBASE = { 1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769, 1025, 1537, 2049, 3073,
  4097, 6145, 8193, 12289, 16385, 24577 }
local DEXT = { 0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13 }
local ORDINE = { 16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15 }

local FISSA_L, FISSA_D
do
  local l = {}
  for s = 0, 143 do l[s] = 8 end
  for s = 144, 255 do l[s] = 9 end
  for s = 256, 279 do l[s] = 7 end
  for s = 280, 287 do l[s] = 8 end
  FISSA_L = costruisci(l, 288)
  local d = {}
  for s = 0, 29 do d[s] = 5 end
  FISSA_D = costruisci(d, 30)
end

local function blocco_codificato(L, out, hl, hd)
  while true do
    local s = decodifica(L, hl)
    if s < 256 then
      out.n = out.n + 1
      out[out.n] = s
    elseif s == 256 then
      return
    else
      s = s - 257
      if s >= 29 then error("inflate: lunghezza non valida", 0) end
      local lung = LBASE[s + 1] + bits(L, LEXT[s + 1])
      local d = decodifica(L, hd)
      if d >= 30 then error("inflate: distanza non valida", 0) end
      local dist = DBASE[d + 1] + bits(L, DEXT[d + 1])
      if dist > out.n then error("inflate: distanza oltre l'inizio", 0) end
      local da = out.n - dist
      for k = 1, lung do
        out[out.n + k] = out[da + k]
      end
      out.n = out.n + lung
    end
  end
end

local function blocco_dinamico(L, out)
  local nlen = bits(L, 5) + 257
  local ndist = bits(L, 5) + 1
  local ncode = bits(L, 4) + 4
  if nlen > 286 or ndist > 30 then error("inflate: intestazione dinamica non valida", 0) end
  local lc = {}
  for k = 0, 18 do lc[k] = 0 end
  for k = 1, ncode do lc[ORDINE[k]] = bits(L, 3) end
  local hc = costruisci(lc, 19)
  local lunghezze, k = {}, 0
  while k < nlen + ndist do
    local s = decodifica(L, hc)
    if s < 16 then
      lunghezze[k] = s
      k = k + 1
    else
      local val, rip = 0, 0
      if s == 16 then
        if k == 0 then error("inflate: ripetizione senza valore", 0) end
        val = lunghezze[k - 1]
        rip = 3 + bits(L, 2)
      elseif s == 17 then
        rip = 3 + bits(L, 3)
      else
        rip = 11 + bits(L, 7)
      end
      if k + rip > nlen + ndist then error("inflate: troppe lunghezze", 0) end
      for _ = 1, rip do
        lunghezze[k] = val
        k = k + 1
      end
    end
  end
  local ll, dl = {}, {}
  for s = 0, nlen - 1 do ll[s] = lunghezze[s] end
  for s = 0, ndist - 1 do dl[s] = lunghezze[nlen + s] end
  blocco_codificato(L, out, costruisci(ll, nlen), costruisci(dl, ndist))
end

function M.inflate(dati, inizio)
  local L = nuovo_lettore(dati, inizio)
  local out = { n = 0 }
  repeat
    local finale = bits(L, 1)
    local tipo = bits(L, 2)
    if tipo == 0 then
      L.buf, L.cnt = 0, 0                       -- allineamento al byte
      local a, b, c, d = byte(L.s, L.pos, L.pos + 3)
      if not d then error("inflate: blocco non compresso troncato", 0) end
      local lung = a + b * 256
      if lung ~= 65535 - (c + d * 256) then error("inflate: lunghezza blocco non valida", 0) end
      L.pos = L.pos + 4
      for k = 0, lung - 1 do
        local v = byte(L.s, L.pos + k)
        if not v then error("inflate: blocco non compresso troncato", 0) end
        out[out.n + k + 1] = v
      end
      out.n = out.n + lung
      L.pos = L.pos + lung
    elseif tipo == 1 then
      blocco_codificato(L, out, FISSA_L, FISSA_D)
    elseif tipo == 2 then
      blocco_dinamico(L, out)
    else
      error("inflate: tipo di blocco non valido", 0)
    end
  until finale == 1
  local parti = {}
  for k = 1, out.n, 4096 do
    parti[#parti + 1] = char(unpack(out, k, math.min(k + 4095, out.n)))
  end
  return table.concat(parti)
end

-- ------------------------------------------------------------------ zip
local function u16(s, i) local a, b = byte(s, i, i + 1); return a + b * 256 end
local function u32(s, i) local a, b, c, d = byte(s, i, i + 3); return a + b * 256 + c * 65536 + d * 16777216 end

-- ritorna { {nome=..., dati=...}, ... } per tutti i file del zip
function M.estrai(zip)
  local fine
  for i = #zip - 21, math.max(1, #zip - 65557), -1 do
    if zip:sub(i, i + 3) == "PK\5\6" then fine = i; break end
  end
  if not fine then error("zip: archivio non valido (manca la directory centrale)", 0) end
  local n = u16(zip, fine + 10)
  local p = u32(zip, fine + 16) + 1
  local file = {}
  for _ = 1, n do
    if zip:sub(p, p + 3) ~= "PK\1\2" then error("zip: directory centrale non valida", 0) end
    local metodo = u16(zip, p + 10)
    local compresso = u32(zip, p + 20)
    local originale = u32(zip, p + 24)
    local ln, le, lc = u16(zip, p + 28), u16(zip, p + 30), u16(zip, p + 32)
    local loc = u32(zip, p + 42) + 1
    local nome = zip:sub(p + 46, p + 45 + ln)
    p = p + 46 + ln + le + lc
    if zip:sub(loc, loc + 3) ~= "PK\3\4" then error("zip: intestazione locale non valida", 0) end
    local inizio = loc + 30 + u16(zip, loc + 26) + u16(zip, loc + 28)
    local dati
    if metodo == 0 then
      dati = zip:sub(inizio, inizio + compresso - 1)
    elseif metodo == 8 then
      dati = M.inflate(zip, inizio)
    else
      error("zip: metodo di compressione non gestito " .. metodo, 0)
    end
    if #dati ~= originale then error("zip: dimensione estratta errata per " .. nome, 0) end
    file[#file + 1] = { nome = nome, dati = dati }
  end
  return file
end

return M
