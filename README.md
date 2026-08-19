# Russia Tracker

Dashboard pubblica: https://tracker-conflitto-ucraina.streamlit.app/

Tracker automatico di indicatori economici, energetici e militari relativi
alla guerra Russia-Ucraina.

## Fonti e aggiornamenti

- **Banca Centrale Russa (settimanale, giovedì):** riserve internazionali,
  struttura aggregata valuta/oro, tasso chiave e cambi ufficiali USD/EUR/CNY.
- **Stato Maggiore ucraino (giornaliero):** perdite russe dichiarate di
  personale, mezzi, missili da crociera e UAV.
- **CREA Russia Fossil Tracker (giornaliero):** ricavi stimati dalle esportazioni
  fossili e flussi marittimi di greggio.

I workflow in `.github/workflows/` aggiornano i CSV in `data/`. Streamlit
ridistribuisce automaticamente la dashboard dopo ogni commit.

## Limiti metodologici

- Le perdite militari sono dichiarate da una parte in guerra e non sono conteggi
  verificati indipendentemente. La categoria sorgente `drone` indica UAV russi
  dichiarati persi/distrutti, non necessariamente attacchi intercettati.
- Le revisioni negative dei valori cumulativi restano visibili nei delta giornalieri.
- I cambi CBR sono ufficiali e non necessariamente descrivono tutta la pressione
  di mercato sul rublo.
- Le riserve includono asset congelati; la serie valuta/oro non separa yuan
  utilizzabili, asset occidentali congelati e altre componenti.
- I dati CREA sono stime basate su flussi commerciali e modelli di prezzo e
  possono essere rivisti.

La dashboard descrive ciò che le fonti dichiarano nel tempo e serve a osservare
tendenze: non misura direttamente capacità economica reale, perdite verificate
o andamento strategico complessivo della guerra.

## Uso locale

```bash
pip install -r requirements.txt
python fetch_cbr.py
python fetch_war.py
python fetch_crea.py
streamlit run dashboard.py
```

## Test

```bash
python -m unittest discover
python -m py_compile dashboard.py fetch_cbr.py fetch_war.py fetch_crea.py
```
