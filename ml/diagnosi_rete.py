# -*- coding: utf-8 -*-
"""
diagnosi_rete.py - controllo di rete a ogni giro di GitHub (solo diagnosi, nessuna chiamata alle API Huawei).
Per ogni indirizzo prova a trovarlo (DNS) in 4 modi e, se lo trova, prova ad aprire la connessione HTTPS:
  - DNS di GitHub (quello di sistema)
  - DNS pubblico Google 8.8.8.8 e Cloudflare 1.1.1.1 (domanda diretta, porta 53)
  - DNS su HTTPS di Google (dns.google)
Risultato: pannello/diagnosi_rete.txt (ultimo giro) e pannello/diagnosi_rete.csv (una riga per indirizzo e giro).
"""
import csv
import datetime as dt
import json
import os
import random
import socket
import struct
import subprocess
import urllib.request

INDIRIZZI = ["oauth2.fusionsolar.huawei.com", "eu5.fusionsolar.huawei.com", "api.mercatoelettrico.org"]
PROVA_HTTPS = {"oauth2.fusionsolar.huawei.com": "/rest/dp/uidm/oauth2/v1/token",
               "eu5.fusionsolar.huawei.com": "/", "api.mercatoelettrico.org": "/"}
OUT = "pannello"


def dns_sistema(nome, famiglia=socket.AF_INET):
    try:
        return sorted({x[4][0] for x in socket.getaddrinfo(nome, 443, famiglia, socket.SOCK_STREAM)}), ""
    except Exception as e:
        return [], str(e)


def curl_come_simulazione(nome):
    """stessa strada del programma della simulazione (curl, risoluzione del sistema): codice HTTP e indirizzo usato"""
    try:
        r = subprocess.run(["curl", "-sS", "-o", "/dev/null", "-m", "20", "-w", "%{http_code} %{remote_ip}",
                            f"https://{nome}{PROVA_HTTPS.get(nome, '/')}"], capture_output=True, text=True, timeout=25)
        return (r.stdout.strip() or "000") + ((" " + r.stderr.strip()[:120]) if r.stderr.strip() else "")
    except Exception as e:
        return f"000 {e}"


def dns_diretto(nome, server, qtipo=1):
    """domanda DNS via UDP (1 = A, IPv4; 28 = AAAA, IPv6); segue i CNAME restituiti nella stessa risposta"""
    try:
        ident = random.randint(0, 65535)
        q = struct.pack(">HHHHHH", ident, 0x0100, 1, 0, 0, 0)
        q += b"".join(bytes([len(p)]) + p.encode() for p in nome.split(".")) + b"\x00" + struct.pack(">HH", qtipo, 1)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(5)
        s.sendto(q, (server, 53))
        r, _ = s.recvfrom(4096)
        s.close()
        rid, flags, qd, an, _, _ = struct.unpack(">HHHHHH", r[:12])
        rcode = flags & 0x0F
        i = 12
        for _ in range(qd):                       # salta la domanda
            while r[i] != 0:
                i += r[i] + 1
            i += 5
        ip, cname = [], []
        for _ in range(an):
            if r[i] & 0xC0 == 0xC0:
                i += 2
            else:
                while r[i] != 0:
                    i += r[i] + 1
                i += 1
            tipo, _, _, lung = struct.unpack(">HHIH", r[i:i + 10])
            i += 10
            if tipo == 1 and lung == 4 and qtipo == 1:
                ip.append(socket.inet_ntoa(r[i:i + 4]))
            elif tipo == 28 and lung == 16 and qtipo == 28:
                ip.append(socket.inet_ntop(socket.AF_INET6, r[i:i + 16]))
            elif tipo == 5:
                cname.append(nome_dns(r, i))
            i += lung
        nomi_rcode = {0: "", 2: "SERVFAIL", 3: "NXDOMAIN (nome inesistente)", 5: "REFUSED"}
        nota = nomi_rcode.get(rcode, f"rcode {rcode}") if not ip else ""
        if cname and not ip:
            nota = (nota + " " if nota else "") + "alias " + ", ".join(cname)
        return sorted(set(ip)), nota
    except Exception as e:
        return [], str(e)


def nome_dns(r, i, salti=0):
    """legge un nome DNS (con compressione) a partire dalla posizione i"""
    parti = []
    while salti < 20:
        n = r[i]
        if n == 0:
            break
        if n & 0xC0 == 0xC0:
            return ".".join(parti + [nome_dns(r, ((n & 0x3F) << 8) | r[i + 1], salti + 1)]).strip(".")
        parti.append(r[i + 1:i + 1 + n].decode(errors="replace"))
        i += n + 1
    return ".".join(parti)


def dns_https(nome):
    try:
        with urllib.request.urlopen(f"https://dns.google/resolve?name={nome}&type=A", timeout=10) as r:
            d = json.loads(r.read())
        ip = sorted({a["data"] for a in d.get("Answer", []) if a.get("type") == 1})
        return ip, "" if ip else f"Status {d.get('Status')}"
    except Exception as e:
        return [], str(e)


def prova_https(nome, ip):
    """apre la connessione HTTPS (GET senza credenziali): qualsiasi codice HTTP vuol dire raggiungibile"""
    cmd = ["curl", "-sS", "-o", "/dev/null", "-m", "15", "-w", "%{http_code}", f"https://{nome}{PROVA_HTTPS.get(nome, '/')}"]
    if ip:
        cmd[1:1] = ["--resolve", f"{nome}:443:{ip}"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return (r.stdout.strip() or "000") + ((" " + r.stderr.strip()[:120]) if r.stderr.strip() else "")
    except Exception as e:
        return f"000 {e}"


def main():
    os.makedirs(OUT, exist_ok=True)
    ora = dt.datetime.now(dt.timezone.utc).astimezone()
    righe = [f"Controllo di rete del giro su GitHub - {ora:%d/%m/%Y %H:%M:%S %Z}"]
    file_csv = os.path.join(OUT, "diagnosi_rete.csv")
    if os.path.isfile(file_csv):                  # file con le colonne della versione precedente: si mette da parte
        with open(file_csv, encoding="utf-8") as fh:
            if "curl_come_simulazione" not in fh.readline():
                fh.close()
                os.replace(file_csv, os.path.join(OUT, "diagnosi_rete_v1.csv"))
    nuovo = not os.path.isfile(file_csv)
    with open(file_csv, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        if nuovo:
            w.writerow(["quando", "indirizzo", "dns_github", "dns_google", "dns_cloudflare", "dns_https", "https_dns_github",
                        "https_ip_pubblico", "ipv6_dns_github", "curl_come_simulazione"])
        for nome in INDIRIZZI:
            sis, e_sis = dns_sistema(nome)
            goo, e_goo = dns_diretto(nome, "8.8.8.8")
            clo, e_clo = dns_diretto(nome, "1.1.1.1")
            doh, e_doh = dns_https(nome)
            h_sis = prova_https(nome, None) if sis else "-"
            pubblico = (goo or clo or doh or [None])[0]
            h_pub = prova_https(nome, pubblico) if pubblico else "-"
            righe.append(f"{nome}")
            righe.append(f"  DNS di GitHub:    {', '.join(sis) or 'NON TROVATO ' + e_sis}")
            righe.append(f"  DNS Google:       {', '.join(goo) or 'NON TROVATO ' + e_goo}")
            righe.append(f"  DNS Cloudflare:   {', '.join(clo) or 'NON TROVATO ' + e_clo}")
            righe.append(f"  DNS su HTTPS:     {', '.join(doh) or 'NON TROVATO ' + e_doh}")
            sis6, e_sis6 = dns_sistema(nome, socket.AF_INET6)
            goo6, e_goo6 = dns_diretto(nome, "8.8.8.8", 28)
            cs = curl_come_simulazione(nome)
            righe.append(f"  IPv6 DNS di GitHub: {', '.join(sis6) or 'NON TROVATO ' + e_sis6}")
            righe.append(f"  IPv6 DNS Google:    {', '.join(goo6) or 'NON TROVATO ' + e_goo6}")
            righe.append(f"  curl come la simulazione (codice, indirizzo usato): {cs}")
            righe.append(f"  HTTPS con DNS di GitHub: {h_sis}")
            righe.append(f"  HTTPS con IP pubblico {pubblico or '-'}: {h_pub}")
            w.writerow([ora.isoformat(timespec="seconds"), nome, " ".join(sis) or "NO", " ".join(goo) or "NO",
                        " ".join(clo) or "NO", " ".join(doh) or "NO", h_sis, h_pub, " ".join(sis6) or "NO", cs])
    testo = "\n".join(righe) + "\n"
    with open(os.path.join(OUT, "diagnosi_rete.txt"), "w", encoding="utf-8") as fh:
        fh.write(testo)
    print(testo)


if __name__ == "__main__":
    main()
