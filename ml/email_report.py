# -*- coding: utf-8 -*-
"""
email_report.py - invia ogni giorno, una volta sola, il resoconto dell'ultimo giorno chiuso (Gmail, SMTP SSL).
  mittente:     GMAIL_UTENTE (variabile d'ambiente, predefinito il primo destinatario)
  password:     GMAIL_APP_PASSWORD (segreto di GitHub: "password per le app" di Google)
  destinatari:  impostazioni/email_destinatari.txt (uno per riga, modificabile nel repository)
  memoria:      pannello/email_ultima.txt (ultimo giorno gia' inviato)
Senza password non fa nulla. Errori di invio: scritti nel registro, il giro di GitHub non si ferma.
"""
import csv
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage

PAGINA = "https://paolofontanacn-code.github.io/ems-dati/"
NOMI = {"F0": "senza carica da rete", "F0R": "con carica da rete"}


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def e(v, d=2):
    return "-" if v is None else f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main():
    password = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
    if not password:
        print("Email: password per le app non impostata (segreto GMAIL_APP_PASSWORD): niente invio")
        return
    try:
        with open("impostazioni/email_destinatari.txt", encoding="utf-8") as fh:
            dest = [x.strip() for x in fh if x.strip() and not x.startswith("#")]
    except FileNotFoundError:
        dest = []
    if not dest:
        print("Email: nessun destinatario in impostazioni/email_destinatari.txt")
        return
    mitt = os.environ.get("GMAIL_UTENTE") or dest[0]
    if not os.path.isfile("riepilogo.csv"):
        print("Email: riepilogo.csv non ancora presente")
        return
    with open("riepilogo.csv", encoding="utf-8") as fh:
        righe = [r for r in csv.DictReader(fh) if len(r.get("giorno") or "") == 8]
    if not righe:
        return
    r = max(righe, key=lambda x: x["giorno"])
    g = r["giorno"]
    stato = "pannello/email_ultima.txt"
    if os.path.isfile(stato) and open(stato, encoding="utf-8").read().strip() >= g:
        print(f"Email: resoconto del {g} gia' inviato")
        return
    data = f"{g[6:]}/{g[4:6]}/{g[:4]}"
    iso = f"{g[:4]}-{g[4:6]}-{g[6:]}"
    profili = [k[:-len("_beneficio_eur")] for k in r if k.endswith("_beneficio_eur") and not k.endswith("_vs_zero_eur")]
    zc, zr = num(r.get("zero_costo_eur")), num(r.get("zero_ricavo_eur"))
    zero = None if zc is None else zc - (zr or 0)
    L = [f"EMS Cismondi - resoconto di {r.get('tipo_giorno') or ''} {data} (SOLO SIMULAZIONE)", "",
         f"Produzione FV {e(num(r.get('fv_kwh')), 1)} kWh, consumo casa {e(num(r.get('carico_kwh')), 1)} kWh.",
         f"Reale: prelievo {e(num(r.get('reale_prel_kwh')), 1)} kWh, immissione {e(num(r.get('reale_imm_kwh')), 1)} kWh.", "",
         "Costo netto del giorno (acquisti - cessioni, + usura batteria e costo dei cambiamenti negli scenari):",
         f"  senza batteria:        {e(zero)} EUR"]
    p0 = profili[0] if profili else None
    if p0:
        rc, rr = num(r.get(f"{p0}_reale_costo_eur")), num(r.get(f"{p0}_reale_ricavo_eur"))
        ac, ar, au = (num(r.get(f"{p0}_{k}")) for k in ("auto_costo_eur", "auto_ricavo_eur", "auto_usura_eur"))
        L.append(f"  reale (impianto oggi): {e(None if rc is None else rc - (rr or 0))} EUR")
        L.append(f"  automatico simulato:   {e(None if ac is None else ac - (ar or 0) + (au or 0))} EUR")
    for p in profili:
        sc, sr, su, si = (num(r.get(f"{p}_{k}")) for k in ("costo_eur", "ricavo_eur", "usura_eur", "costo_interventi_eur"))
        netto = None if sc is None else sc - (sr or 0) + (su or 0) + (si or 0)
        L.append(f"  {NOMI.get(p, p) + ':':22} {e(netto)} EUR  (beneficio sull'automatico {e(num(r.get(p + '_beneficio_eur')))} EUR, "
                 f"su senza batteria {e(num(r.get(p + '_beneficio_vs_zero_eur')))} EUR, cambiamenti {r.get(p + '_comandi') or 0})")
    L += ["", f"Pagina con i grafici del giorno: {PAGINA}?giorno={iso}",
          "Per cambiare i destinatari: file impostazioni/email_destinatari.txt nel repository ems-dati."]
    msg = EmailMessage()
    msg["Subject"] = f"EMS Cismondi - resoconto del {data}"
    msg["From"] = mitt
    msg["To"] = ", ".join(dest)
    msg.set_content("\n".join(L) + "\n")
    rep = f"dati/{iso}/report.md"
    if os.path.isfile(rep):
        with open(rep, "rb") as fh:
            msg.add_attachment(fh.read(), maintype="text", subtype="markdown", filename=f"report_{g}.md")
    try:
        with smtplib.SMTP_SSL(os.environ.get("EMS_PROVA_SMTP", "smtp.gmail.com"), int(os.environ.get("EMS_PROVA_SMTP_PORTA", "465")),
                              context=ssl.create_default_context(), timeout=30) as s:
            s.login(mitt, password)
            s.send_message(msg)
    except Exception as ex:
        print(f"Email: invio non riuscito: {ex}")
        return
    os.makedirs("pannello", exist_ok=True)
    with open(stato, "w", encoding="utf-8") as fh:
        fh.write(g + "\n")
    print(f"Email: resoconto del {g} inviato a {', '.join(dest)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:          # l'email non deve mai fermare il giro
        print(f"Email: errore {ex}")
        sys.exit(0)
