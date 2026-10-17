-- huawei.lua - FusionSolar Northbound API con OAuth: SOLA LETTURA (nessun comando all'inverter)
local J = require "lib_json"
local H = require "lib_http"
local F = require "lib_file"
local T = require "lib_tempo"
local M = {}

M.MODI = { [0] = "nessuno", [1] = "carica/scarica forzata", [2] = "prezzo a fasce", [3] = "carica/scarica fissa",
  [4] = "autonoma (massimo autoconsumo)", [5] = "immissione totale", [6] = "TOU", [7] = "remoto: massimo autoconsumo",
  [8] = "remoto: immissione totale", [9] = "remoto: TOU", [10] = "IA gestione energia", [11] = "remoto: IA gestione energia",
  [12] = "terze parti" }
M.STATI_BATTERIA = { [0] = "fuori linea", [1] = "standby", [2] = "in funzione", [3] = "guasto", [4] = "ibernazione", [5] = "riavvio" }

local function num(v)
  if type(v) == "number" then return v end
  if type(v) == "string" then return tonumber(v) end
  return nil
end

function M.nuovo(c, cartella, stato, log)
  local self = { file_token = cartella .. "/token_fusionsolar.json" }

  local function oggi_conta()
    stato.chiamate_huawei = (stato.chiamate_huawei or 0) + 1
  end

  function self.chiamate_disponibili(n)
    return (stato.chiamate_huawei or 0) + (n or 1) <= c.LIMITE_CHIAMATE_GIORNO
  end

  local function salva_token(t)
    t.ottenuto_il = os.time()
    F.scrivi(self.file_token, J.encode(t, "  "))
  end

  -- autorizzazione interattiva (una tantum, in SSH)
  function self.autorizza()
    local st = ""
    local f = io.open("/dev/urandom", "rb")
    local b = f and f:read(16) or tostring(os.time())
    if f then f:close() end
    for i = 1, #b do st = st .. string.format("%02x", b:byte(i)) end
    local link = c.URL_OAUTH .. "/rest/dp/uidm/oauth2/v1/authorize?" .. H.urlencode({
      response_type = "code", client_id = c.CLIENT_ID, redirect_uri = c.REDIRECT_URI, state = st, locale = "it-it" })
    print("\n======================================================================")
    print("AUTORIZZAZIONE HUAWEI (una tantum)")
    print("1. Apri questo link nel browser del PC (copialo tutto):\n")
    print(link .. "\n")
    print("2. Il PROPRIETARIO dell'impianto fa login e autorizza.")
    print("3. Nella pagina che si apre copia il codice e incollalo qui ENTRO 5 MINUTI.")
    print("======================================================================")
    io.write(">>> Codice (o indirizzo intero della pagina): ")
    io.flush()
    local testo = (io.read("*l") or ""):gsub("^%s+", ""):gsub("%s+$", "")
    local codice = testo
    if testo:find("code=") then
      local q = testo:match("%?(.*)$") or testo
      local par = {}
      for k, v in q:gmatch("([^&=]+)=([^&]*)") do par[k] = v:gsub("%%(%x%x)", function(x) return string.char(tonumber(x, 16)) end) end
      if par.state and par.state ~= st then error("controllo 'state' non corrispondente: ripetere l'autorizzazione", 0) end
      codice = par.code or ""
    end
    if codice == "" then error("nessun codice inserito", 0) end
    local t, cod = H.post_form(c.URL_OAUTH .. "/rest/dp/uidm/oauth2/v1/token", {
      grant_type = "authorization_code", code = codice, client_id = c.CLIENT_ID,
      client_secret = c.CLIENT_SECRET, redirect_uri = c.REDIRECT_URI })
    if not t.access_token then error("token non ottenuto (HTTP " .. tostring(cod) .. "): " .. J.encode(t), 0) end
    salva_token(t)
    log("Autorizzazione Huawei completata. Permessi: " .. tostring(t.scope))
    return t
  end

  function self.token()
    local testo = F.leggi(self.file_token)
    if not testo then error("manca il token Huawei: eseguire  lua ems_sim.lua autorizza", 0) end
    local t = J.decode(testo)
    if os.time() < (t.ottenuto_il or 0) + (tonumber(t.expires_in) or 0) - 120 then return t end
    local nuovo, codice = H.post_form(c.URL_OAUTH .. "/rest/dp/uidm/oauth2/v1/token", {
      grant_type = "refresh_token", refresh_token = t.refresh_token, client_id = c.CLIENT_ID, client_secret = c.CLIENT_SECRET })
    if not nuovo.access_token then
      error("rinnovo token Huawei non riuscito (HTTP " .. tostring(codice) .. "): rifare  lua ems_sim.lua autorizza", 0)
    end
    nuovo.refresh_token = nuovo.refresh_token or t.refresh_token
    salva_token(nuovo)
    log("Token Huawei rinnovato.")
    return nuovo
  end

  function self.api(percorso, corpo)
    if not self.chiamate_disponibili(1) then error("limite giornaliero di chiamate Huawei raggiunto", 0) end
    local t = self.token()
    oggi_conta()
    return H.post_json(c.URL_API_HUAWEI .. percorso, corpo, { "Authorization: Bearer " .. t.access_token })
  end

  -- impianto, coordinate e dispositivi (letti una volta, conservati nello stato)
  function self.impianto()
    if stato.impianto and stato.impianto.disp then return stato.impianto end
    local r = self.api("/thirdData/stations", { pageNo = 1 })
    if not r.success then error("elenco impianti non riuscito: failCode=" .. tostring(r.failCode), 0) end
    local imp
    for _, i in ipairs((r.data or {}).list or {}) do
      local nome = ((i.plantName or ""):lower():gsub("^%s+", ""):gsub("%s+$", ""))
      if nome == c.NOME_IMPIANTO:lower() then imp = i end
    end
    if not imp then error("impianto '" .. c.NOME_IMPIANTO .. "' non trovato tra quelli autorizzati", 0) end
    local d = self.api("/thirdData/getDevList", { stationCodes = imp.plantCode })
    if not d.success then error("elenco dispositivi non riuscito: failCode=" .. tostring(d.failCode), 0) end
    local disp = {}
    for _, x in ipairs(d.data or {}) do
      local tipo = tonumber(x.devTypeId)
      local nome = (tipo == 39 and "batteria") or (tipo == 47 and "contatore") or ((tipo == 1 or tipo == 38) and "inverter")
      if nome and not disp[nome] then
        disp[nome] = { tipo = tipo, id = string.format("%.0f", tonumber(x.id) or 0), dn = x.devDn }
      end
    end
    for _, n in ipairs({ "batteria", "contatore", "inverter" }) do
      if not disp[n] then error("dispositivo '" .. n .. "' non trovato nell'impianto", 0) end
    end
    stato.impianto = { codice = imp.plantCode, lat = num(imp.latitude), lon = num(imp.longitude),
                       potenza = num(imp.capacity), disp = disp }
    log(string.format("Impianto %s (%s): coordinate %s, %s", c.NOME_IMPIANTO, imp.plantCode,
      tostring(stato.impianto.lat), tostring(stato.impianto.lon)))
    return stato.impianto
  end

  -- lettura istantanea: 3 chiamate. Segni verificati sull'impianto:
  -- batteria + = carica, - = scarica; contatore + = immissione, - = prelievo
  -- MODALITA' GITHUB: le letture arrivano dallo storico a 5 minuti (self.sorgente[t]); si contano le chiamate
  -- che il Mango avrebbe fatto (3 per lettura) senza farle davvero
  function self.leggi()
    if self.sorgente then
      local x = self.sorgente[T.adesso()]
      stato.chiamate_equivalenti = (stato.chiamate_equivalenti or 0) + 3
      if not x then error("dato dello storico Huawei mancante per " .. T.testo(nil), 0) end
      local l = {}
      for k, v in pairs(x) do l[k] = v end
      return l
    end
    local imp = self.impianto()
    local mappe = {}
    for _, n in ipairs({ "batteria", "contatore", "inverter" }) do
      local dd = imp.disp[n]
      local r = self.api("/thirdData/getDevRealKpi", { devIds = dd.id, devTypeId = dd.tipo })
      if not r.success then error("lettura " .. n .. " non riuscita: failCode=" .. tostring(r.failCode) .. " " .. tostring(r.message), 0) end
      mappe[n] = ((r.data or {})[1] or {}).dataItemMap or {}
    end
    local b, m, i = mappe.batteria, mappe.contatore, mappe.inverter
    local l = {
      soc = num(b.battery_soc), batteria_w = num(b.ch_discharge_power),
      modo_cod = num(b.ch_discharge_model), stato_batt_cod = num(b.battery_status),
      contatore_w = num(m.active_power),
      inverter_w = num(i.active_power) and num(i.active_power) * 1000,
      fv_w = num(i.mppt_power) and num(i.mppt_power) * 1000,
    }
    for k, v in pairs({ soc = "battery_soc", batteria_w = "ch_discharge_power", contatore_w = "active_power contatore",
      inverter_w = "active_power inverter", fv_w = "mppt_power" }) do
      if l[k] == nil then error("dato mancante nella lettura Huawei: " .. v, 0) end
    end
    l.carico_w = math.max(0, l.inverter_w - l.contatore_w)
    l.fv_w = math.max(0, l.fv_w)
    l.modo = M.MODI[l.modo_cod or -1] or tostring(l.modo_cod)
    l.stato_batt = M.STATI_BATTERIA[l.stato_batt_cod or -1] or tostring(l.stato_batt_cod)
    return l
  end

  -- storico a 5 minuti di un intero giorno italiano (23, 24 o 25 ore): Huawei consente al massimo 24 ore per
  -- chiamata, quindi il giorno di 25 ore richiede 2 chiamate
  function self.storico_giorno(nome, giorno)
    local m0 = T.mezzanotte(giorno)
    local m1 = T.mezzanotte(T.giorno(m0 + 43200, 1))
    local out, n = {}, 0
    local t = m0
    while t < m1 do
      local durata = math.min(86400, m1 - t)
      local parte, k = self.storico(nome, t, durata)
      for tt, x in pairs(parte) do out[tt] = x end
      n = n + k
      t = t + durata
    end
    return out, n
  end

  -- storico a 5 minuti di un dispositivo per al massimo 24 ore (1 chiamata): { [epoca_s] = dataItems }
  function self.storico(nome, inizio_s, durata)
    local imp = self.impianto()
    local dd = imp.disp[nome]
    if not dd.dn then error("devDn del dispositivo " .. nome .. " non disponibile", 0) end
    local r = self.api("/rest/openapi/pvms/nbi/v1/device/history", {
      devDn = dd.dn, devTypeId = dd.tipo, startTime = inizio_s * 1000, endTime = (inizio_s + (durata or 86400)) * 1000 - 1 })
    if not r.success then
      error("storico " .. nome .. " non riuscito: failCode=" .. tostring(r.failCode) .. " " .. tostring(r.message), 0)
    end
    local out, n = {}, 0
    for _, x in ipairs(r.data or {}) do
      local t = num(x.collectTime)
      if t then out[math.floor(t / 1000)] = x.dataItems or {}; n = n + 1 end
    end
    return out, n
  end

  -- letture a 5 minuti tra da (escluso) e a (incluso) dallo storico Huawei: 3 chiamate per giorno coinvolto
  function self.finestra_storico(da, a)
    local per_t = {}
    local g = T.giorno(da + 1)
    local ultimo = T.giorno(a)
    local giorni = 0
    while true do
      local m0 = T.mezzanotte(g)
      local dati = {}
      for _, n in ipairs({ "contatore", "inverter", "batteria" }) do dati[n] = self.storico_giorno(n, g) end
      for t, xi in pairs(dati.inverter) do
        local xc, xb = dati.contatore[t], dati.batteria[t]
        if t > da and t <= a and xc and xb then
          local p_inv, p_c = num(xi.active_power), num(xc.active_power)
          local fv, pb, soc = num(xi.mppt_power), num(xb.ch_discharge_power), num(xb.battery_soc)
          if p_inv and p_c and fv and pb and soc then
            local l = { fv_w = math.max(0, fv * 1000), inverter_w = p_inv * 1000, contatore_w = p_c, batteria_w = pb, soc = soc,
                        modo_cod = num(xb.ch_discharge_model), stato_batt_cod = num(xb.battery_status) }
            l.carico_w = math.max(0, l.inverter_w - l.contatore_w)
            l.modo = M.MODI[l.modo_cod or -1] or (l.modo_cod and tostring(l.modo_cod)) or "non disponibile nello storico"
            l.stato_batt = M.STATI_BATTERIA[l.stato_batt_cod or -1] or (l.stato_batt_cod and tostring(l.stato_batt_cod)) or "-"
            per_t[t] = l
          end
        end
      end
      giorni = giorni + 1
      if g >= ultimo or giorni > 3 then break end
      g = T.giorno(m0 + 43200, 1)
    end
    return per_t
  end

  return self
end

return M
