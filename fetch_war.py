"""
War Tracker — perdite russe giornaliere secondo lo Stato Maggiore ucraino.

Fonte: dataset open-source aggiornato quotidianamente dai report ufficiali
del Ministero della Difesa ucraino:
https://github.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset

Nota metodologica: sono cifre DICHIARATE DA UNA PARTE in guerra (Kyiv).
Gli osservatori indipendenti (es. Oryx, che conta solo perdite fotografate)
stimano numeri più bassi per i mezzi. Vanno letti come limite superiore
e soprattutto come TREND, non come conteggio esatto.

Output: data/war_losses.csv — valori cumulativi + delta giornalieri.
"""

import os
import sys

import pandas as pd
import requests

BASE = ("https://raw.githubusercontent.com/PetroIvaniuk/"
        "2022-Ukraine-Russia-War-Dataset/main/data/")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# colonna nel dataset -> nome nel nostro CSV
EQUIPMENT_COLS = {
    "cruise missiles": "cruise_missiles",
    "drone": "drones",
    "tank": "tanks",
    "APC": "apc",
    "field artillery": "artillery",
    "aircraft": "aircraft",
    "helicopter": "helicopters",
}


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    try:
        eq = pd.DataFrame(requests.get(BASE + "russia_losses_equipment.json", timeout=60).json())
        pers = pd.DataFrame(requests.get(BASE + "russia_losses_personnel.json", timeout=60).json())
    except Exception as e:  # noqa: BLE001
        print(f"[war-tracker] ERRORE download: {e}", file=sys.stderr)
        sys.exit(1)

    eq = eq[["date"] + list(EQUIPMENT_COLS)].rename(columns=EQUIPMENT_COLS)
    pers = pers[["date", "personnel"]]

    df = pers.merge(eq, on="date", how="outer").sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # Delta giornalieri (i valori sorgente sono cumulativi)
    value_cols = ["personnel"] + list(EQUIPMENT_COLS.values())
    for c in value_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df[f"daily_{c}"] = df[c].diff().clip(lower=0)  # clip: correzioni al ribasso -> 0

    path = os.path.join(DATA_DIR, "war_losses.csv")
    df.to_csv(path, index=False)
    print(f"[war-tracker] OK — {len(df)} giorni, ultimo: {df['date'].iloc[-1]}, "
          f"personale cumulativo: {int(df['personnel'].iloc[-1]):,}")


if __name__ == "__main__":
    main()
