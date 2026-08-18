"""
Dashboard Tracker Russia — Streamlit.
Sezione 1: economia (Banca Centrale Russa, dati settimanali)
Sezione 2: guerra (perdite russe secondo lo Stato Maggiore ucraino, giornaliere)
Avvio locale:  streamlit run dashboard.py
"""

import io
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


def filter_dates(df: pd.DataFrame, dates) -> pd.DataFrame:
    if len(dates) != 2:
        return df
    start, end = pd.Timestamp(dates[0]), pd.Timestamp(dates[1])
    return df[df.date.between(start, end)]


def excel_bytes(df: pd.DataFrame, sheet_name: str = "Dati") -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()


def data_tools(df: pd.DataFrame, source_label: str, source_url: str, filename: str) -> None:
    st.caption(f"Fonte: [{source_label}]({source_url})")
    with st.expander("📋 Mostra tabella"):
        st.dataframe(df, width="stretch", hide_index=True)
    csv_col, excel_col = st.columns(2)
    csv_col.download_button("⬇️ Scarica CSV", df.to_csv(index=False).encode("utf-8"),
                            f"{filename}.csv", "text/csv", key=f"csv-{filename}")
    excel_col.download_button("⬇️ Scarica Excel", excel_bytes(df),
                              f"{filename}.xlsx", key=f"xlsx-{filename}")


weekly = load("reserves_weekly.csv")
monthly = load("reserves_monthly.csv")
key_rate = load("key_rate.csv")
fx = load("fx_rates.csv")
war = load("war_losses.csv")

# ================== ANALISI INTRODUTTIVA ==================
with st.expander("‼️ Come leggere questi dati — metodologia e avvertenze", expanded=False):
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
war_tab, economy_tab, data_tab = st.tabs(["⚔️ Guerra", "🏦 Economia", "📋 Dati e fonti"])

with war_tab:
    st.header("Perdite russe dichiarate da Kyiv")
    last_war = war.iloc[-1]
    w1, w2, w3, w4 = st.columns(4)
    for box, label, total, daily in [
        (w1, "Personale (cumulativo)", "personnel", "daily_personnel"),
        (w2, "Droni (cumulativo)", "drones", "daily_drones"),
        (w3, "Missili da crociera", "cruise_missiles", "daily_cruise_missiles"),
        (w4, "Carri armati", "tanks", "daily_tanks"),
    ]:
        box.metric(label, f"{int(last_war[total]):,}".replace(",", " "),
                   f"+{int(last_war[daily])} nell'ultimo giorno")

    war_ma = war.copy()
    for col in ["daily_personnel", "daily_drones", "daily_cruise_missiles"]:
        war_ma[f"{col}_ma7"] = war_ma[col].rolling(7).mean()
    st.subheader("Perdite giornaliere di personale (media mobile 7gg)")
    personnel_dates = st.date_input("Intervallo", (war.date.min().date(), war.date.max().date()),
                                    min_value=war.date.min().date(), max_value=war.date.max().date(),
                                    key="personnel-dates")
    personnel_view = filter_dates(war_ma, personnel_dates)
    st.plotly_chart(px.line(personnel_view, x="date", y="daily_personnel_ma7",
                           labels={"date": "", "daily_personnel_ma7": "uomini/giorno"}),
                    width="stretch")
    data_tools(personnel_view[["date", "personnel", "daily_personnel", "daily_personnel_ma7"]],
               "dataset open-source dei report ucraini",
               "https://github.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset",
               "perdite-personale")

    st.subheader("Droni e missili da crociera (media mobile 7gg)")
    missile_dates = st.date_input("Intervallo", (war.date.min().date(), war.date.max().date()),
                                  min_value=war.date.min().date(), max_value=war.date.max().date(),
                                  key="missile-dates")
    missile_view = filter_dates(war_ma, missile_dates)
    figw2 = go.Figure()
    figw2.add_trace(go.Scatter(x=missile_view.date, y=missile_view.daily_drones_ma7, name="Droni"))
    figw2.add_trace(go.Scatter(x=missile_view.date, y=missile_view.daily_cruise_missiles_ma7,
                               name="Missili da crociera"))
    figw2.update_layout(yaxis_title="unità/giorno", legend_orientation="h")
    st.plotly_chart(figw2, width="stretch")
    data_tools(missile_view[["date", "drones", "cruise_missiles", "daily_drones",
                       "daily_cruise_missiles"]], "dataset open-source dei report ucraini",
               "https://github.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset",
               "droni-missili")

    equipment = {"tanks": "Carri armati", "apc": "Blindati (APC)",
                 "artillery": "Artiglieria", "aircraft": "Aerei", "helicopters": "Elicotteri"}
    st.subheader("Mezzi pesanti — perdite cumulative")
    equipment_dates = st.date_input("Intervallo", (war.date.min().date(), war.date.max().date()),
                                    min_value=war.date.min().date(), max_value=war.date.max().date(),
                                    key="equipment-dates")
    equipment_view = filter_dates(war, equipment_dates)
    selected_equipment = st.multiselect("Mezzi da visualizzare", equipment,
                                        default=list(equipment), format_func=equipment.get)
    figw3 = go.Figure()
    for col in selected_equipment:
        figw3.add_trace(go.Scatter(x=equipment_view.date, y=equipment_view[col], name=equipment[col]))
    figw3.update_layout(yaxis_title="unità (cumulativo)", legend_orientation="h")
    st.plotly_chart(figw3, width="stretch")
    data_tools(equipment_view[["date"] + selected_equipment], "dataset open-source dei report ucraini",
               "https://github.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset",
               "mezzi-pesanti")

with economy_tab:
    st.header("Banca Centrale Russa")
    last_w, prev_w = weekly.iloc[-1], weekly.iloc[-2]
    last_kr = key_rate.iloc[-1]
    last_usd = fx[fx.currency == "USD"].iloc[-1]
    gold_share = monthly.iloc[-1].gold_mln_usd / monthly.iloc[-1].total_mln_usd * 100
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Riserve internazionali *", f"{last_w.reserves_bln_usd:,.1f} mld $",
              f"{last_w.reserves_bln_usd - prev_w.reserves_bln_usd:+.1f} vs precedente")
    c2.metric("Tasso chiave", f"{last_kr.key_rate_pct:.2f} %")
    c3.metric("USD/RUB", f"{last_usd.rub_per_unit:.2f} ₽")
    c4.metric("Quota oro nelle riserve", f"{gold_share:.1f} %")

    st.subheader("Riserve internazionali* (settimanali, mld USD)")
    reserve_dates = st.date_input("Intervallo", (weekly.date.min().date(), weekly.date.max().date()),
                                  min_value=weekly.date.min().date(), max_value=weekly.date.max().date(),
                                  key="reserve-dates")
    weekly_view = filter_dates(weekly, reserve_dates)
    fig = px.line(weekly_view, x="date", y="reserves_bln_usd",
                  labels={"date": "", "reserves_bln_usd": "mld USD"})
    fig.add_vline(x="2022-02-24", line_dash="dash", line_color="red",
                  annotation_text="Invasione 24.02.2022")
    st.plotly_chart(fig, width="stretch")
    data_tools(weekly_view, "Banca Centrale Russa", "https://www.cbr.ru/development/DWS/",
               "riserve-settimanali")

    st.subheader("Struttura delle riserve: valuta estera vs oro")
    structure_dates = st.date_input("Intervallo", (monthly.date.min().date(), monthly.date.max().date()),
                                    min_value=monthly.date.min().date(), max_value=monthly.date.max().date(),
                                    key="structure-dates")
    monthly_view = filter_dates(monthly, structure_dates)
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=monthly_view.date, y=monthly_view.fx_mln_usd,
                              stackgroup="one", name="Valuta estera (incl. congelata)"))
    fig2.add_trace(go.Scatter(x=monthly_view.date, y=monthly_view.gold_mln_usd,
                              stackgroup="one", name="Oro monetario"))
    fig2.update_layout(yaxis_title="mln USD", legend_orientation="h")
    st.plotly_chart(fig2, width="stretch")
    data_tools(monthly_view, "Banca Centrale Russa", "https://www.cbr.ru/development/DWS/",
               "struttura-riserve")

    st.subheader("Tasso chiave (%)")
    rate_dates = st.date_input("Intervallo", (key_rate.date.min().date(), key_rate.date.max().date()),
                               min_value=key_rate.date.min().date(), max_value=key_rate.date.max().date(),
                               key="rate-dates")
    key_view = filter_dates(key_rate, rate_dates)
    fig3 = px.line(key_view, x="date", y="key_rate_pct", labels={"date": "", "key_rate_pct": "%"})
    fig3.update_traces(line_shape="hv")
    st.plotly_chart(fig3, width="stretch")
    data_tools(key_view, "Banca Centrale Russa", "https://www.cbr.ru/development/DWS/", "tasso-chiave")

    st.subheader("Cambi ufficiali (₽ per unità)")
    fx_dates = st.date_input("Intervallo", (fx.date.min().date(), fx.date.max().date()),
                             min_value=fx.date.min().date(), max_value=fx.date.max().date(),
                             key="fx-dates")
    fx_view = filter_dates(fx, fx_dates)
    currencies = st.multiselect("Valute da visualizzare", sorted(fx.currency.unique()),
                                default=sorted(fx.currency.unique()), key="currencies")
    fx_view = fx_view[fx_view.currency.isin(currencies)]
    st.plotly_chart(px.line(fx_view, x="date", y="rub_per_unit", color="currency",
                           labels={"date": "", "rub_per_unit": "₽"}), width="stretch")
    data_tools(fx_view, "Banca Centrale Russa", "https://www.cbr.ru/development/DWS/", "cambi")

with data_tab:
    st.header("Tutti i dati")
    st.markdown("- [Banca Centrale Russa](https://www.cbr.ru/development/DWS/)\n"
                "- [Dataset dei report dello Stato Maggiore ucraino]"
                "(https://github.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset)")
    all_data = io.BytesIO()
    with pd.ExcelWriter(all_data, engine="openpyxl") as writer:
        for name, df in {"Guerra": war, "Riserve settimanali": weekly,
                         "Riserve mensili": monthly, "Tasso chiave": key_rate,
                         "Cambi": fx}.items():
            df.to_excel(writer, sheet_name=name, index=False)
    st.download_button("⬇️ Scarica tutti i dati in Excel", all_data.getvalue(),
                       "russia-tracker-dati.xlsx", key="xlsx-all")

st.divider()
st.caption(f"Ultimo dato riserve: {weekly.iloc[-1].date.date()} · "
           f"ultimo dato guerra: {war.iloc[-1].date.date()} · Progetto a scopo informativo.")
