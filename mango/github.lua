-- github.lua - invio e lettura file nel repository privato (API "contents" di GitHub)
-- Il token (fine-grained, solo Contents: Read and write sul repository) sta nel file github.token
local J = require "lib_json"
local H = require "lib_http"
local Z = require "lib_zip"
local F = require "lib_file"
local M = {}

function M.nuovo(c, cartella, stato, log)
  local self = {}
  local file_token = cartella .. "/github.token"

  local function token()
    local t = F.leggi(file_token)
    t = t and t:gsub("%s+", "")
    if not t or t == "" then return nil end
    return t
  end

  local function intest(t)
    return { "Authorization: Bearer " .. t, "Accept: application/vnd.github+json", "X-GitHub-Api-Version: 2022-11-28",
             "User-Agent: ems-mango-cismondi" }
  end

  local function url(percorso)
    return string.format("%s/repos/%s/%s/contents/%s", c.URL_GITHUB, c.GITHUB_OWNER, c.GITHUB_REPO, percorso)
  end

  -- modalita' GitHub: il programma gira dentro il repository, i file si leggono e scrivono direttamente
  local repo = os.getenv("EMS_REPO_DIR")
  if repo then
    function self.configurato() return true end
    function self.leggi(percorso)
      local t = F.leggi(repo .. "/" .. percorso)
      if not t then return nil, nil end
      local h = 5381
      for i = 1, #t do h = (h * 33 + t:byte(i)) % 4294967296 end
      return t, string.format("%d-%08x", #t, h)
    end
    function self.scrivi(percorso, contenuto)
      local dest = repo .. "/" .. percorso
      F.cartella((dest:match("^(.*)/[^/]*$")))
      F.scrivi(dest, contenuto)
      return true
    end
  end

  if not repo then function self.configurato() return token() ~= nil end end

  -- legge un file: ritorna contenuto, sha (nil, nil se non esiste)
  if not repo then function self.leggi(percorso)
    local t = token()
    if not t then error("token GitHub mancante (file github.token)", 0) end
    local codice, testo = H.get(url(percorso) .. "?ref=" .. c.GITHUB_BRANCH, intest(t), 60)
    if codice == 404 then return nil, nil end
    if codice ~= 200 then error("GitHub lettura " .. percorso .. ": HTTP " .. codice .. " " .. testo:sub(1, 200), 0) end
    local d = J.decode(testo)
    local cont = d.content and Z.base64_decode(d.content) or ""
    return cont, d.sha
  end end

  -- scrive (crea o sostituisce) un file
  if not repo then function self.scrivi(percorso, contenuto, messaggio)
    local t = token()
    if not t then error("token GitHub mancante (file github.token)", 0) end
    local _, sha = self.leggi(percorso)
    local corpo = { message = messaggio or ("EMS Mango: " .. percorso), content = Z.base64_encode(contenuto),
                    branch = c.GITHUB_BRANCH, sha = sha }
    local h = intest(t)
    h[#h + 1] = "Content-Type: application/json"
    local codice, testo = H.richiesta("PUT", url(percorso), J.encode(corpo), h, 120)
    if codice ~= 200 and codice ~= 201 then
      error("GitHub scrittura " .. percorso .. ": HTTP " .. codice .. " " .. testo:sub(1, 200), 0)
    end
    return true
  end end

  -- coda di invii: { locale = percorso file, remoto = percorso nel repository }
  -- elimina = true: il file locale viene cancellato dopo l'invio riuscito (es. storico in RAM)
  function self.accoda(locale, remoto, elimina)
    stato.github = stato.github or {}
    stato.github.coda = stato.github.coda or {}
    table.insert(stato.github.coda, { locale = locale, remoto = remoto, elimina = elimina or nil })
  end

  function self.invia_coda(massimo)
    if not self.configurato() then return 0 end
    local coda = (stato.github or {}).coda or {}
    local inviati, resto = 0, {}
    for _, x in ipairs(coda) do
      if inviati < (massimo or 20) then
        local cont = F.leggi(x.locale)
        if not cont then
          log("GitHub: file non trovato, salto " .. x.locale)
        else
          local ok, err = pcall(self.scrivi, x.remoto, cont)
          if repo then
            -- sul Mango ogni invio costa una lettura (sha) e una scrittura con il file in base64
            stato.github_equivalenti = stato.github_equivalenti or { n = 0, byte = 0 }
            stato.github_equivalenti.n = stato.github_equivalenti.n + 2
            stato.github_equivalenti.byte = stato.github_equivalenti.byte + math.floor(#cont * 4 / 3) + 300
          end
          if ok then
            inviati = inviati + 1
            if x.elimina then os.remove(x.locale) end
          else
            log("GitHub: invio non riuscito (" .. tostring(err) .. "), riprovo piu' tardi")
            resto[#resto + 1] = x
          end
        end
      else
        resto[#resto + 1] = x
      end
    end
    stato.github.coda = resto
    if inviati > 0 then log("GitHub: inviati " .. inviati .. " file") end
    return inviati
  end

  return self
end

return M
