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


def dns_sistema(nome):
    try:
        return sorted({x[4][0] for x in socket.getaddrinfo(nome, 443, socket.AF_INET, socket.SOCK_STREAM)}), ""
    except Exception as e:
        return [], str(e)


def dns_diretto(nome, server):
    """domanda DNS di tipo A via UDP; segue i CNAME restituiti nella stessa risposta"""
    try:
        ident = random.randint(0, 65535)
        q = struct.pack(">HHHHHH", ident, 0x0100, 1, 0, 0, 0)
        q += b"".join(bytes([len(p)]) + p.encode() for p in nome.split(".")) + b"\x00" + struct.pack(">HH", 1, 1)
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
        ip = []
        for _ in range(an):
            if r[i] & 0xC0 == 0xC0:
                i += 2
            else:
                while r[i] != 0:
                    i += r[i] + 1
                i += 1
            tipo, _, _, lung = struct.unpack(">HHIH", r[i:i + 10])
            i += 10
            if tipo == 1 and lung == 4:
                ip.append(socket.inet_ntoa(r[i:i + 4]))
            i += lung
        nomi_rcode = {0: "", 2: "SERVFAIL", 3: "NXDOMAIN (nome inesistente)", 5: "REFUSED"}
        return sorted(set(ip)), nomi_rcode.get(rcode, f"rcode {rcode}") if not ip else ""
    except Exception as e:
        return [], str(e)


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
    nuovo = not os.path.isfile(file_csv)
    with open(file_csv, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        if nuovo:
            w.writerow(["quando", "indirizzo", "dns_github", "dns_google", "dns_cloudflare", "dns_https", "https_dns_github", "https_ip_pubblico"])
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
            righe.append(f"  HTTPS con DNS di GitHub: {h_sis}")
            righe.append(f"  HTTPS con IP pubblico {pubblico or '-'}: {h_pub}")
            w.writerow([ora.isoformat(timespec="seconds"), nome, " ".join(sis) or "NO", " ".join(goo) or "NO",
                        " ".join(clo) or "NO", " ".join(doh) or "NO", h_sis, h_pub])
    testo = "\n".join(righe) + "\n"
    with open(os.path.join(OUT, "diagnosi_rete.txt"), "w", encoding="utf-8") as fh:
        fh.write(testo)
    print(testo)


if __name__ == "__main__":
    main()
