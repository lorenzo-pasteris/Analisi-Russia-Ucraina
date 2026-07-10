"""
CBR Tracker — scarica dati dalla Banca Centrale Russa (cbr.ru) via SOAP API.

Serie tracciate:
  - Riserve internazionali settimanali (mrrf7DXML), mld USD
  - Riserve internazionali mensili con struttura oro/valuta (mrrfXML), mln USD
  - Tasso chiave (KeyRateXML), %
  - Cambi ufficiali USD/EUR/CNY vs RUB (GetCursDynamicXML)

Ogni serie viene salvata in data/*.csv. Lo script è idempotente:
riscarica l'intera finestra e deduplica, quindi può girare ogni giorno
senza creare doppioni.
"""

import os
import sys
import xml.etree.ElementTree as ET
from datetime import date, timedelta

import pandas as pd
import requests

SOAP_URL = "https://www.cbr.ru/DailyInfoWebServ/DailyInfo.asmx"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Data di inizio dello storico (prima esecuzione)
HISTORY_START = date(2021, 1, 1)
# Nelle esecuzioni successive riscarica solo gli ultimi N giorni
INCREMENTAL_DAYS = 60

CURRENCIES = {
    "USD": "R01235",
    "EUR": "R01239",
    "CNY": "R01375",
}


def soap_call(method: str, params: dict) -> ET.Element:
    """Chiama un metodo SOAP della CBR e restituisce la radice del payload XML."""
    body = "".join(f"<{k}>{v}</{k}>" for k, v in params.items())
    envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema"
               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <{method} xmlns="http://web.cbr.ru/">{body}</{method}>
  </soap:Body>
</soap:Envelope>"""
    resp = requests.post(
        SOAP_URL,
        data=envelope.encode("utf-8"),
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f"http://web.cbr.ru/{method}",
            "User-Agent": "cbr-tracker/1.0 (open data project)",
        },
        timeout=60,
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    # Il payload utile è dentro <MethodResult>
    result = root.find(f".//{{http://web.cbr.ru/}}{method}Result")
    if result is None:
        raise RuntimeError(f"{method}: nessun risultato nella risposta SOAP")
    return result


def parse_dt(s: str) -> str:
    """'2026-07-10T00:00:00+03:00' -> '2026-07-10'"""
    return s.split("T")[0]


def fetch_weekly_reserves(start: date, end: date) -> pd.DataFrame:
    res = soap_call("mrrf7DXML", {"fromDate": start.isoformat(), "ToDate": end.isoformat()})
    rows = [
        {"date": parse_dt(mr.findtext("D0")), "reserves_bln_usd": float(mr.findtext("val"))}
        for mr in res.iter("mr")
    ]
    return pd.DataFrame(rows)


def fetch_monthly_reserves(start: date, end: date) -> pd.DataFrame:
    res = soap_call("mrrfXML", {"fromDate": start.isoformat(), "ToDate": end.isoformat()})
    rows = []
    for mr in res.iter("mr"):
        rows.append({
            "date": parse_dt(mr.findtext("D0")),
            "total_mln_usd": float(mr.findtext("p1") or 0),
            "fx_mln_usd": float(mr.findtext("p2") or 0),       # valuta estera
            "gold_mln_usd": float(mr.findtext("p6") or 0),     # oro monetario
        })
    return pd.DataFrame(rows)


def fetch_key_rate(start: date, end: date) -> pd.DataFrame:
    res = soap_call("KeyRateXML", {"fromDate": start.isoformat(), "ToDate": end.isoformat()})
    rows = [
        {"date": parse_dt(kr.findtext("DT")), "key_rate_pct": float(kr.findtext("Rate"))}
        for kr in res.iter("KR")
    ]
    return pd.DataFrame(rows)


def fetch_fx(start: date, end: date) -> pd.DataFrame:
    frames = []
    for code, vid in CURRENCIES.items():
        res = soap_call("GetCursDynamicXML", {
            "FromDate": start.isoformat(),
            "ToDate": end.isoformat(),
            "ValutaCode": vid,
        })
        rows = []
        for vc in res.iter("ValuteCursDynamic"):
            nominal = float(vc.findtext("Vnom") or 1)
            value = float(vc.findtext("Vcurs"))
            rows.append({
                "date": parse_dt(vc.findtext("CursDate")),
                "currency": code,
                "rub_per_unit": round(value / nominal, 4),
            })
        frames.append(pd.DataFrame(rows))
    return pd.concat(frames, ignore_index=True)


def merge_save(df_new: pd.DataFrame, filename: str, keys: list[str]) -> int:
    """Unisce i nuovi dati al CSV esistente, deduplica per chiave, salva ordinato."""
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        df_old = pd.read_csv(path, dtype=str)
        df_new = df_new.astype(str)
        df = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df = df_new.astype(str)
    df = df.drop_duplicates(subset=keys, keep="last").sort_values(keys)
    df.to_csv(path, index=False)
    return len(df)


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    today = date.today()

    # Prima esecuzione: storico completo. Poi: solo finestra recente.
    first_run = not os.path.exists(os.path.join(DATA_DIR, "reserves_weekly.csv"))
    start = HISTORY_START if first_run else today - timedelta(days=INCREMENTAL_DAYS)
    mode = "storico completo" if first_run else f"ultimi {INCREMENTAL_DAYS} giorni"
    print(f"[cbr-tracker] {today} — modalità: {mode} (da {start})")

    ok, failed = [], []

    tasks = [
        ("riserve settimanali", lambda: merge_save(
            fetch_weekly_reserves(start, today), "reserves_weekly.csv", ["date"])),
        ("riserve mensili (oro/valuta)", lambda: merge_save(
            fetch_monthly_reserves(start, today), "reserves_monthly.csv", ["date"])),
        ("tasso chiave", lambda: merge_save(
            fetch_key_rate(start, today), "key_rate.csv", ["date"])),
        ("cambi USD/EUR/CNY", lambda: merge_save(
            fetch_fx(start, today), "fx_rates.csv", ["date", "currency"])),
    ]

    for name, task in tasks:
        try:
            n = task()
            ok.append(name)
            print(f"  OK  {name}: {n} righe totali")
        except Exception as e:  # noqa: BLE001 — una serie che fallisce non blocca le altre
            failed.append(name)
            print(f"  ERR {name}: {e}", file=sys.stderr)

    print(f"[cbr-tracker] completato — ok: {len(ok)}, falliti: {len(failed)}")
    # Esce con errore solo se TUTTO è fallito (es. sito irraggiungibile)
    if ok == []:
        sys.exit(1)


if __name__ == "__main__":
    main()
