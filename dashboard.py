"""
Dashboard Tracker Russia — Streamlit.
Sezione 1: economia (Banca Centrale Russa, dati settimanali)
Sezione 2: guerra (perdite russe secondo lo Stato Maggiore ucraino, giornaliere)
Avvio locale:  streamlit run dashboard.py
"""

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

st.set_page_config(page_title="Russia Tracker", page_icon="📊", layout="wide")
st.title("📊 Russia Tracker — economia e guerra")
st.caption(
    "Riserve e dati CBR: aggiornamento settimanale (giovedì) · "
    "Perdite/attacchi: aggiornamento giornaliero · tutto automatico via GitHub Actions"
)


@st.cache_data(ttl=3600)
def load(name: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(DATA_DIR, name), parse_dates=["date"])
    return df.sort_values("date")


weekly = load("reserves_weekly.csv")
monthly = load("reserves_monthly.csv")
key_rate = load("key_rate.csv")
fx = load("fx_rates.csv")
war = load("war_losses.csv")

# ================== ANALISI INTRODUTTIVA ==================
with st.expander("📖 Come leggere questi dati — metodologia e avvertenze", expanded=True):
    st.markdown("""
**Cosa traccia questa dashboard.** Due facce dello stesso conflitto: la tenuta
*economico-finanziaria* della Russia (riserve, tasso di interesse, rublo) e il
costo *militare* della guerra (perdite di uomini e mezzi, missili e droni abbattuti).
Nessuna singola serie racconta tutto: vanno lette insieme e come **tendenze**,
non come fotografie esatte.

**Fonti.**
- *Economia:* API SOAP ufficiale della [Banca Centrale Russa](https://www.cbr.ru/development/DWS/).
  Dati auto-dichiarati da Mosca, ma verificabili indirettamente dai mercati e
  generalmente considerati attendibili per riserve e cambi.
- *Guerra:* report giornalieri dello [Stato Maggiore ucraino](https://www.zsu.gov.ua/),
  via dataset open-source. Sono cifre dichiarate **da una parte in guerra**:
  gli osservatori indipendenti (es. Oryx, che conta solo perdite documentate
  fotograficamente) stimano valori più bassi per i mezzi. Vanno lette come
  limite superiore e, soprattutto, come indicatore di intensità nel tempo.

**Le riserve\\* non sono tutte spendibili.** Il totale pubblicato dalla CBR
include ~300 mld $ di asset **congelati** dalle sanzioni occidentali dal
febbraio 2022. La parte effettivamente liquida per Mosca è essenzialmente
oro fisico (custodito in Russia) + yuan. Per questo il grafico sulla
struttura oro/valuta è più informativo del totale.

**Perché il tasso chiave conta.** È il termometro dello stress: la CBR lo alza
per difendere il rublo e frenare l'inflazione da spesa bellica. Livelli
sopra il 15-20% segnalano un'economia in surriscaldamento da economia di guerra.
""")

st.divider()

# ================== SEZIONE GUERRA (giornaliera) ==================
st.header("⚔️ Guerra — perdite russe dichiarate da Kyiv")
st.caption("Aggiornamento giornaliero · fonte: Stato Maggiore ucraino (vedi avvertenze sopra)")

last_war = war.iloc[-1]
w1, w2, w3, w4 = st.columns(4)
w1.metric("Personale (cumulativo)", f"{int(last_war.personnel):,}".replace(",", " "),
          f"+{int(last_war.daily_personnel)} oggi")
w2.metric("Droni abbattuti (cum.)", f"{int(last_war.drones):,}".replace(",", " "),
          f"+{int(last_war.daily_drones)} oggi")
w3.metric("Missili da crociera (cum.)", f"{int(last_war.cruise_missiles):,}".replace(",", " "),
          f"+{int(last_war.daily_cruise_missiles)} oggi")
w4.metric("Carri armati (cum.)", f"{int(last_war.tanks):,}".replace(",", " "),
          f"+{int(last_war.daily_tanks)} oggi")

# medie mobili 7 giorni per leggere l'intensità
war_ma = war.copy()
for c in ["daily_personnel", "daily_drones", "daily_cruise_missiles"]:
    war_ma[c + "_ma7"] = war_ma[c].rolling(7).mean()

col_w1, col_w2 = st.columns(2)
with col_w1:
    st.subheader("Perdite giornaliere di personale (media mobile 7gg)")
    figw1 = px.line(war_ma, x="date", y="daily_personnel_ma7",
                    labels={"date": "", "daily_personnel_ma7": "uomini/giorno"})
    st.plotly_chart(figw1, use_container_width=True)
with col_w2:
    st.subheader("Droni e missili abbattuti al giorno (media 7gg)")
    figw2 = go.Figure()
    figw2.add_trace(go.Scatter(x=war_ma.date, y=war_ma.daily_drones_ma7,
                               name="Droni", mode="lines"))
    figw2.add_trace(go.Scatter(x=war_ma.date, y=war_ma.daily_cruise_missiles_ma7,
                               name="Missili da crociera", mode="lines"))
    figw2.update_layout(yaxis_title="unità/giorno", legend_orientation="h")
    st.plotly_chart(figw2, use_container_width=True)

st.subheader("Mezzi pesanti — perdite cumulative")
figw3 = go.Figure()
for col, name in [("tanks", "Carri armati"), ("apc", "Blindati (APC)"),
                  ("artillery", "Artiglieria"), ("aircraft", "Aerei"),
                  ("helicopters", "Elicotteri")]:
    figw3.add_trace(go.Scatter(x=war.date, y=war[col], name=name, mode="lines"))
figw3.update_layout(yaxis_title="unità (cumulativo)", legend_orientation="h")
st.plotly_chart(figw3, use_container_width=True)

st.divider()

# ================== SEZIONE ECONOMIA (settimanale) ==================
st.header("🏦 Economia — Banca Centrale Russa")
st.caption("Aggiornamento settimanale (giovedì) · fonte: cbr.ru")

last_w = weekly.iloc[-1]
prev_w = weekly.iloc[-2]
last_kr = key_rate.iloc[-1]
last_usd = fx[fx.currency == "USD"].iloc[-1]
gold_share = monthly.iloc[-1].gold_mln_usd / monthly.iloc[-1].total_mln_usd * 100

c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Riserve internazionali \\*",
    f"{last_w.reserves_bln_usd:,.1f} mld $",
    f"{last_w.reserves_bln_usd - prev_w.reserves_bln_usd:+.1f} vs sett. prec.",
)
c2.metric("Tasso chiave", f"{last_kr.key_rate_pct:.2f} %")
c3.metric("USD/RUB", f"{last_usd.rub_per_unit:.2f} ₽")
c4.metric("Quota oro nelle riserve", f"{gold_share:.1f} %")
st.caption(
    "\\* Il totale **include ~300 mld $ di asset congelati** dalle sanzioni: "
    "non rappresenta la liquidità effettivamente disponibile per Mosca."
)

st.subheader("Riserve internazionali\\* (settimanali, mld USD)")
fig = px.line(weekly, x="date", y="reserves_bln_usd",
              labels={"date": "", "reserves_bln_usd": "mld USD"})
fig.add_vline(x="2022-02-24", line_dash="dash", line_color="red",
              annotation_text="Invasione 24.02.2022")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Struttura delle riserve: valuta estera vs oro (mensile, mln USD)")
fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=monthly.date, y=monthly.fx_mln_usd,
                          stackgroup="one", name="Valuta estera (incl. congelata)"))
fig2.add_trace(go.Scatter(x=monthly.date, y=monthly.gold_mln_usd,
                          stackgroup="one", name="Oro monetario"))
fig2.update_layout(yaxis_title="mln USD", legend_orientation="h")
st.plotly_chart(fig2, use_container_width=True)

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Tasso chiave (%)")
    fig3 = px.line(key_rate, x="date", y="key_rate_pct",
                   labels={"date": "", "key_rate_pct": "%"})
    fig3.update_traces(line_shape="hv")
    st.plotly_chart(fig3, use_container_width=True)
with col_b:
    st.subheader("Cambi ufficiali (₽ per unità)")
    fig4 = px.line(fx, x="date", y="rub_per_unit", color="currency",
                   labels={"date": "", "rub_per_unit": "₽"})
    st.plotly_chart(fig4, use_container_width=True)

st.divider()
st.caption(
    f"Ultimo dato riserve: {last_w.date.date()} · ultimo dato guerra: {last_war.date.date()} · "
    "Fonti: Banca Centrale della Federazione Russa (cbr.ru, API SOAP) e "
    "Stato Maggiore delle Forze Armate ucraine (via dataset open-source). "
    "Progetto a scopo informativo; leggere le avvertenze metodologiche in alto."
)
