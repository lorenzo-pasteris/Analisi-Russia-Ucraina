# Russia Tracker

Tracker automatico su due binari con frequenze diverse:

**Economia (aggiornamento SETTIMANALE, giovedì)** — Banca Centrale Russa via API SOAP:
- Riserve internazionali settimanali (mld USD) e mensili con struttura oro/valuta
- Tasso chiave e cambi ufficiali USD/EUR/CNY

**Guerra (aggiornamento GIORNALIERO)** — Stato Maggiore ucraino via dataset open:
- Perdite russe: personale, carri, blindati, artiglieria, aerei, elicotteri
- Missili da crociera e droni abbattuti (cumulativi + delta giornalieri)

Due workflow GitHub Actions separati (`update.yml` settimanale, `update_war.yml`
giornaliero) scaricano i dati, li salvano come CSV in `data/` e li committano.
La dashboard Streamlit include un'analisi introduttiva con le avvertenze
metodologiche e marca con \* i dati delle riserve (che includono gli asset congelati).

## Cosa devi fare tu (10 minuti)

### 1. Crea il repository su GitHub
1. Vai su github.com → **New repository** → nome es. `cbr-tracker`, pubblico
2. Carica tutti i file di questa cartella (anche la cartella nascosta
   `.github/workflows/` — se usi l'upload web, trascina l'intera cartella;
   in alternativa da terminale:
   ```bash
   cd cbr-tracker
   git init && git add -A && git commit -m "init"
   git remote add origin https://github.com/TUO_USERNAME/cbr-tracker.git
   git push -u origin main
   ```

### 2. Attiva le Actions
1. Nel repo → tab **Actions** → se richiesto, clicca "I understand… enable"
2. Settings → Actions → General → **Workflow permissions** →
   seleziona **Read and write permissions** → Save
3. Tab Actions → workflow "Aggiornamento dati CBR" → **Run workflow**
   per testarlo subito. Da lì in poi gira da solo ogni giorno alle 15:10 UTC.

### 3. Pubblica la dashboard (gratis)
1. Vai su [share.streamlit.io](https://share.streamlit.io) → login con GitHub
2. **New app** → scegli il repo `cbr-tracker`, branch `main`,
   file `dashboard.py` → Deploy
3. Fine: hai un URL pubblico che si aggiorna da solo quando la Action
   committa nuovi dati.

## Uso locale

```bash
pip install -r requirements.txt
python fetch_cbr.py        # dati economia (CBR)
python fetch_war.py        # dati guerra
streamlit run dashboard.py # apre la dashboard su localhost
```

## Note

- Lo script è **idempotente**: riscarica una finestra di 60 giorni e deduplica,
  quindi recupera da solo eventuali giorni saltati.
- Se una serie fallisce, le altre vengono comunque salvate; il job fallisce
  solo se l'intero sito è irraggiungibile.
- Le riserve CBR **includono gli asset congelati** dalle sanzioni (~300 mld $):
  il totale pubblicato non è tutto liquido/disponibile.
- Le perdite russe sono **cifre dichiarate da Kyiv**: limite superiore, utili
  soprattutto come trend (Oryx, che conta solo perdite fotografate, dà numeri
  più bassi per i mezzi).
- Prossimi step possibili: scraper Roskazna, attacchi missilistici per regione,
  confronto con stime Oryx.
