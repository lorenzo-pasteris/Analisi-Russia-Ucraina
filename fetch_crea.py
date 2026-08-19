"""Scarica le stime del Russia Fossil Tracker dall'API pubblica CREA."""

import csv
import io
import os
import urllib.parse
import urllib.request
from collections import defaultdict

API = "https://api.russiafossiltracker.com"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def download(path: str, params: dict[str, str]) -> list[dict[str, str]]:
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "russia-tracker/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return list(csv.DictReader(io.StringIO(response.read().decode("utf-8"))))


def write_csv(filename: str, rows: list[dict], fields: list[str]) -> None:
    with open(os.path.join(DATA_DIR, filename), "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    monthly_raw = download("/v0/chart/monthly_payments", {
        "date_from": "2022-02-24",
        "aggregate_by": "destination_region,commodity_group,date",
        "add_total_region": "false",
        "format": "csv",
        "nest_in_data": "false",
        "version": "v2",
    })
    fields = ["date", "destination_region", "oil_eur_per_day", "gas_eur_per_day",
              "coal_eur_per_day", "total_eur_per_day"]
    monthly, totals = [], defaultdict(lambda: [0.0, 0.0, 0.0])
    for row in monthly_raw:
        values = [float(row[name] or 0) for name in ("Oil", "Gas", "Coal")]
        monthly.append(dict(zip(fields, [row["month"], row["destination_region"],
                                         *values, sum(values)])))
        for index, value in enumerate(values):
            totals[row["month"]][index] += value
    for date, values in totals.items():
        monthly.append(dict(zip(fields, [date, "Total", *values, sum(values)])))
    write_csv("crea_monthly.csv", sorted(monthly, key=lambda row: (row["date"], row["destination_region"])),
              fields)

    counter_raw = download("/v0/counter_last", {
        "date_from": "2022-02-24", "aggregate_by": "destination_region",
        "format": "csv", "version": "v2",
    })
    counter_fields = ["destination_region", "total_eur", "eur_per_day", "total_tonne",
                      "tonne_per_day", "updated_on"]
    counter = []
    for row in counter_raw:
        counter.append({field: ("Total" if field == "destination_region" and row[field] == "total"
                                else row[field]) for field in counter_fields})
    write_csv("crea_counter.csv", counter, counter_fields)

    ports_raw = download("/v0/chart/departure_by_port", {
        "departure_date_from": "2022-02-24", "commodity": "crude_oil",
        "format": "csv", "nest_in_data": "false",
    })
    port_fields = ["date", "port", "area", "value_tonne", "value_m3", "trade_count",
                   "value_eur"]
    ports = [{"date": row["departure_date"][:10], "port": row["origin_port_name"],
              "area": row["origin_area"], "value_tonne": row["value_tonne"],
              "value_m3": row["value_m3"], "trade_count": row["trade_count"],
              "value_eur": row["value_eur"]} for row in ports_raw]
    write_csv("crea_ports_daily.csv", ports, port_fields)
    print(f"[crea] OK: {len(monthly)} righe mensili, {len(counter)} destinazioni, "
          f"{len(ports)} righe portuali")


if __name__ == "__main__":
    main()
