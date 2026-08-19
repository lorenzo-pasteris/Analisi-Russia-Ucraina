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
TODAY = pd.Timestamp.today().date()

st.set_page_config(page_title="Russia Tracker", page_icon="📊", layout="wide")
st.title("📊 Russia Tracker — economia, energia e guerra")
st.caption(
    "Riserve e dati CBR: aggiornamento settimanale (giovedì) · "
    "Perdite dichiarate: aggiornamento giornaliero · tutto automatico via GitHub Actions"
)


@st.cache_data(ttl=3600)
def load(name: str, required: tuple[str, ...] = ()) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        raise ValueError(f"{name}: file mancante o vuoto")
    df = pd.read_csv(path)
    missing = {"date", *required} - set(df.columns)
    if df.empty or missing:
        raise ValueError(f"{name}: dati vuoti o colonne mancanti ({', '.join(sorted(missing))})")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if df.date.isna().any():
        raise ValueError(f"{name}: contiene date non valide")
    return df.sort_values("date")


def filter_dates(df: pd.DataFrame, dates) -> pd.DataFrame:
    if isinstance(dates, dict):
        if dates["mode"] == "Confronto anni":
            return df[df.date.dt.year.isin(dates["years"])]
        dates = dates["dates"]
    if len(dates) != 2:
        return df
    start, end = pd.Timestamp(dates[0]), pd.Timestamp(dates[1])
    return df[df.date.between(start, end)]


def date_range(min_date, max_date, key: str):
    mode = st.radio("Filtro temporale", ["Da / A", "Periodo rapido", "Confronto anni"],
                    horizontal=True, key=f"{key}-mode")
    if mode == "Da / A":
        start_col, end_col = st.columns(2)
        start = start_col.date_input("Da", min_date, min_value=min_date, max_value=TODAY,
                                     key=f"{key}-start")
        end = end_col.date_input("A", max_date, min_value=min_date, max_value=TODAY,
                                 key=f"{key}-end")
        return {"mode": mode, "dates": (min(start, end), max(start, end))}
    if mode == "Periodo rapido":
        preset = st.selectbox("Periodo", ["Ultima settimana", "Ultimo mese",
                                           "Ultimo anno", "Tutto"], key=f"{key}-preset")
        days = {"Ultima settimana": 6, "Ultimo mese": 29, "Ultimo anno": 364}
        start = min_date if preset == "Tutto" else max(
            min_date, max_date - pd.Timedelta(days=days[preset]))
        return {"mode": mode, "dates": (start, max_date)}
    available_years = list(range(min_date.year, max_date.year + 1))
    selected_years = st.multiselect("Anni da confrontare", available_years,
                                    default=available_years[-2:], key=f"{key}-years")
    return {"mode": mode, "years": selected_years}


def comparison_frame(df: pd.DataFrame, selection: dict, frequency: str):
    if selection.get("mode") != "Confronto anni":
        return df, "date", None
    compared = df.copy()
    compared["anno"] = compared.date.dt.year.astype(str)
    compared["periodo"] = pd.to_datetime({
        "year": 2000, "month": compared.date.dt.month, "day": compared.date.dt.day
    })
    return compared, "periodo", "anno"


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


try:
    weekly = load("reserves_weekly.csv", ("reserves_bln_usd",))
    monthly = load("reserves_monthly.csv", ("total_mln_usd", "fx_mln_usd", "gold_mln_usd"))
    key_rate = load("key_rate.csv", ("key_rate_pct",))
    fx = load("fx_rates.csv", ("currency", "rub_per_unit"))
    war = load("war_losses.csv", ("personnel", "drones", "cruise_missiles"))
    crea_monthly = load("crea_monthly.csv", ("destination_region", "total_eur_per_day"))
    crea_ports = load("crea_ports_daily.csv", ("port", "area", "trade_count", "value_tonne"))
    crea_counter = pd.read_csv(os.path.join(DATA_DIR, "crea_counter.csv"))
    if crea_counter.empty or "destination_region" not in crea_counter:
        raise ValueError("crea_counter.csv: dati vuoti o incompleti")
except (OSError, ValueError, pd.errors.ParserError) as error:
    st.error(f"Impossibile caricare i dati: {error}")
    st.stop()

# ================== ANALISI INTRODUTTIVA ==================
with st.expander("‼️ Come leggere questi dati — metodologia e avvertenze", expanded=False):
    st.markdown("""
**Cosa traccia questa dashboard.** Due facce dello stesso conflitto: la tenuta
*economico-finanziaria* della Russia (riserve, tasso di interesse, rublo) e il
costo *militare* della guerra (perdite di uomini e mezzi, missili e UAV).
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
- *Energia:* stime del [Russia Fossil Tracker di CREA](https://www.russiafossiltracker.com/),
  basate su flussi commerciali e modelli di prezzo. I valori mensili rappresentano
  la **media giornaliera stimata** del mese e possono essere rivisti retroattivamente.

**Limiti dei dati economici.** I cambi CBR sono tassi ufficiali e non misurano
necessariamente tutta la pressione di mercato sul rublo. Il totale delle riserve
include ~300 mld $ di asset **congelati** dalle sanzioni occidentali dal
febbraio 2022; il grafico aggrega valuta estera e oro, senza separare yuan
utilizzabili, asset occidentali congelati e altre componenti. L'idea che la
liquidità disponibile sia soprattutto oro e yuan è un'interpretazione plausibile,
ma non è dimostrata direttamente da queste serie.

**Limiti dei dati militari.** La categoria sorgente `drone` è mostrata come
**UAV russi dichiarati persi/distrutti**: non equivale necessariamente agli
attacchi con droni intercettati. Eventuali delta negativi sono revisioni al
ribasso della fonte e restano visibili, non vengono trasformati in zero.

**Perché il tasso chiave conta.** È il termometro dello stress: la CBR lo alza
per difendere il rublo e frenare l'inflazione da spesa bellica. Livelli
sopra il 15-20% segnalano un'economia in surriscaldamento da economia di guerra.

**In sintesi.** Il tracker mostra bene che cosa dichiarano le fonti nel tempo;
non misura direttamente la reale capacità economica russa, le perdite verificate
o l'andamento strategico complessivo della guerra.
""")

st.divider()
war_tab, economy_tab, crea_tab, maritime_tab, data_tab = st.tabs(
    ["⚔️ Guerra", "🏦 Economia", "⛽ Energia CREA", "🚢 Flussi marittimi",
     "📋 Dati e fonti"]
)

with war_tab:
    st.header("Perdite russe dichiarate da Kyiv")
    last_war = war.iloc[-1]
    w1, w2, w3, w4 = st.columns(4)
    for box, label, total, daily in [
        (w1, "Personale (cumulativo)", "personnel", "daily_personnel"),
        (w2, "UAV dichiarati persi/distrutti", "drones", "daily_drones"),
        (w3, "Missili da crociera", "cruise_missiles", "daily_cruise_missiles"),
        (w4, "Carri armati", "tanks", "daily_tanks"),
    ]:
        box.metric(label, f"{int(last_war[total]):,}".replace(",", " "),
                   f"{int(last_war[daily]):+} nell'ultimo giorno")

    war_weekly = war.assign(
        date=war.date + pd.to_timedelta(6 - war.date.dt.weekday, unit="D")
    ).groupby("date", as_index=False).agg(
        personnel=("daily_personnel", "sum"), drones=("daily_drones", "sum"),
        cruise_missiles=("daily_cruise_missiles", "sum")
    )
    war_weekly = war_weekly[war_weekly.date <= war.date.max()]

    st.subheader("Perdite di personale dichiarate — totali settimanali")
    personnel_date_col, personnel_window_col, personnel_raw_col = st.columns([2, 1, 1])
    with personnel_date_col:
        personnel_dates = date_range(war_weekly.date.min().date(),
                                     war_weekly.date.max().date(), "personnel-dates")
    with personnel_window_col:
        personnel_window = st.selectbox("Media mobile", [1, 4, 8, 13], index=1,
                                        format_func=lambda n: "Nessuna" if n == 1 else f"{n} settimane",
                                        key="personnel-window")
    with personnel_raw_col:
        personnel_raw = st.checkbox("Mostra totale settimanale", True, key="personnel-raw")
    personnel_all = war_weekly.copy()
    personnel_all["media_mobile"] = personnel_all.personnel.rolling(personnel_window).mean()
    personnel_view = filter_dates(personnel_all, personnel_dates)
    personnel_view, personnel_x, personnel_facet = comparison_frame(
        personnel_view, personnel_dates, "settimanale")
    if personnel_facet:
        personnel_comparison = px.line(
            personnel_view, x=personnel_x, y="personnel", color=personnel_facet,
            labels={"periodo": "mese", "personnel": "persone/settimana",
                    "anno": "Anno"})
        personnel_comparison.update_xaxes(tickformat="%b")
        st.plotly_chart(personnel_comparison, width="stretch")
    else:
        personnel_fig = go.Figure()
        if personnel_raw:
            personnel_fig.add_bar(x=personnel_view.date, y=personnel_view.personnel,
                                  name="Totale settimanale", opacity=.45)
        personnel_fig.add_scatter(x=personnel_view.date, y=personnel_view.media_mobile,
                                  name="Media mobile", line_width=3)
        personnel_fig.update_layout(yaxis_title="persone/settimana", legend_orientation="h")
        st.plotly_chart(personnel_fig, width="stretch")
    data_tools(personnel_view,
               "dataset open-source dei report ucraini",
               "https://github.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset",
               "perdite-personale")

    st.subheader("UAV e missili da crociera dichiarati persi/distrutti — totali settimanali")
    air_date_col, air_series_col, air_window_col = st.columns([2, 1, 1])
    air_weapons = {"drones": "UAV", "cruise_missiles": "Missili da crociera"}
    with air_date_col:
        missile_dates = date_range(war_weekly.date.min().date(),
                                   war_weekly.date.max().date(), "missile-dates")
    with air_series_col:
        selected_air_weapons = st.multiselect("Serie", air_weapons, default=list(air_weapons),
                                              format_func=air_weapons.get, key="air-weapons")
    with air_window_col:
        air_window = st.selectbox("Media mobile", [1, 4, 8, 13], index=1,
                                  format_func=lambda n: "Nessuna" if n == 1 else f"{n} settimane",
                                  key="air-window")
    missile_all = war_weekly.copy()
    for column in air_weapons:
        missile_all[f"{column}_media"] = missile_all[column].rolling(air_window).mean()
    missile_view = filter_dates(missile_all, missile_dates)
    missile_view, missile_x, missile_facet = comparison_frame(
        missile_view, missile_dates, "settimanale")
    if missile_facet:
        air_comparison = missile_view.melt(
            ["date", "periodo", "anno"], value_vars=selected_air_weapons,
            var_name="serie", value_name="unità")
        air_comparison["serie"] = air_comparison.serie.map(air_weapons)
        st.plotly_chart(px.line(
            air_comparison, x=missile_x, y="unità", color=missile_facet, line_dash="serie",
            labels={"periodo": "mese", "unità": "unità/settimana",
                    "serie": "", "anno": "Anno"}), width="stretch")
    else:
        air_fig = go.Figure()
        for column in selected_air_weapons:
            air_fig.add_scatter(x=missile_view.date,
                                y=missile_view[f"{column}_media"],
                                name=air_weapons[column])
        air_fig.update_layout(yaxis_title="unità/settimana", legend_orientation="h")
        st.plotly_chart(air_fig, width="stretch")
    data_tools(missile_view[["date"] + selected_air_weapons], "dataset open-source dei report ucraini",
               "https://github.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset",
               "droni-missili")

    equipment = {"tanks": "Carri armati", "apc": "Blindati (APC)",
                 "artillery": "Artiglieria"}
    st.subheader("Mezzi terrestri — perdite cumulative")
    equipment_dates = date_range(war.date.min().date(), war.date.max().date(), "equipment-dates")
    equipment_view = filter_dates(war, equipment_dates)
    selected_equipment = st.multiselect("Mezzi da visualizzare", equipment,
                                        default=list(equipment), format_func=equipment.get)
    equipment_view, equipment_x, equipment_facet = comparison_frame(
        equipment_view, equipment_dates, "giornaliera")
    if equipment_facet:
        for column in [*selected_equipment, "aircraft", "helicopters"]:
            equipment_view[column] = equipment_view.groupby("anno")[column].transform(
                lambda values: values - values.iloc[0])
        equipment_chart = equipment_view.melt(
            ["date", "periodo", "anno"], value_vars=selected_equipment,
            var_name="mezzo", value_name="incremento_annuo")
        equipment_chart["mezzo"] = equipment_chart.mezzo.map(equipment)
        equipment_comparison = px.line(
            equipment_chart, x=equipment_x, y="incremento_annuo", color=equipment_facet,
            line_dash="mezzo", labels={"periodo": "mese", "mezzo": "",
                                        "incremento_annuo": "incremento dall'inizio dell'anno",
                                        "anno": "Anno"})
        equipment_comparison.update_xaxes(tickformat="%b")
        st.plotly_chart(equipment_comparison, width="stretch")
    else:
        figw3 = go.Figure()
        for col in selected_equipment:
            figw3.add_trace(go.Scatter(x=equipment_view.date, y=equipment_view[col],
                                       name=equipment[col]))
        figw3.update_layout(yaxis_title="unità (cumulativo)", legend_orientation="h")
        st.plotly_chart(figw3, width="stretch")
    data_tools(equipment_view[["date"] + selected_equipment], "dataset open-source dei report ucraini",
               "https://github.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset",
               "mezzi-pesanti")

    st.subheader("Aviazione — perdite cumulative")
    aviation_columns = ["date", "aircraft", "helicopters"] + (
        ["periodo", "anno"] if equipment_facet else [])
    aviation = equipment_view[aviation_columns].rename(
        columns={"aircraft": "Aerei", "helicopters": "Elicotteri"})
    aviation_ids = ["date"] + (["periodo", "anno"] if equipment_facet else [])
    aviation_chart = aviation.melt(aviation_ids, value_vars=["Aerei", "Elicotteri"],
                                    var_name="mezzo", value_name="unità")
    aviation_figure = px.line(
        aviation_chart, x=equipment_x, y="unità",
        color=equipment_facet or "mezzo", line_dash="mezzo" if equipment_facet else None,
        labels={"date": "", "periodo": "mese", "mezzo": "", "anno": "Anno"})
    if equipment_facet:
        aviation_figure.update_xaxes(tickformat="%b")
    st.plotly_chart(aviation_figure, width="stretch")
    data_tools(aviation, "dataset open-source dei report ucraini",
               "https://github.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset",
               "perdite-aviazione")

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

    st.subheader("Riserve internazionali* — livello e variazioni")
    reserve_date_col, reserve_mode_col, reserve_window_col = st.columns([2, 1, 1])
    with reserve_date_col:
        reserve_dates = date_range(weekly.date.min().date(), weekly.date.max().date(),
                                   "reserve-dates")
    with reserve_mode_col:
        reserve_mode = st.radio("Visualizzazione", ["Livello", "Variazione settimanale"],
                                key="reserve-mode")
    with reserve_window_col:
        reserve_window = st.selectbox("Media mobile", [1, 4, 13], index=1,
                                      format_func=lambda n: "Nessuna" if n == 1 else f"{n} settimane",
                                      key="reserve-window")
    reserve_all = weekly.copy()
    reserve_all["variazione_mld"] = reserve_all.reserves_bln_usd.diff()
    reserve_all["media_livello"] = reserve_all.reserves_bln_usd.rolling(reserve_window).mean()
    reserve_all["media_variazione"] = reserve_all.variazione_mld.rolling(reserve_window).mean()
    weekly_view = filter_dates(reserve_all, reserve_dates)
    weekly_view, reserve_x, reserve_facet = comparison_frame(
        weekly_view, reserve_dates, "settimanale")
    if reserve_facet:
        reserve_y = "reserves_bln_usd" if reserve_mode == "Livello" else "variazione_mld"
        fig = px.line(weekly_view, x=reserve_x, y=reserve_y, color=reserve_facet,
                           labels={"periodo": "mese", reserve_y: reserve_mode,
                                   "anno": "Anno"})
        fig.update_xaxes(tickformat="%b")
    elif reserve_mode == "Livello":
        fig = go.Figure()
        fig.add_scatter(x=weekly_view.date, y=weekly_view.reserves_bln_usd,
                        name="Riserve", line_width=1)
        fig.add_scatter(x=weekly_view.date, y=weekly_view.media_livello,
                        name="Media mobile", line_width=3)
        fig.update_yaxes(title="mld USD")
    else:
        fig = go.Figure()
        fig.add_bar(x=weekly_view.date, y=weekly_view.variazione_mld,
                    name="Variazione", marker_color=weekly_view.variazione_mld.apply(
                        lambda value: "#2ca02c" if value >= 0 else "#d62728"))
        fig.add_scatter(x=weekly_view.date, y=weekly_view.media_variazione,
                        name="Media mobile", line_width=3)
        fig.update_yaxes(title="variazione settimanale, mld USD")
    if not reserve_facet:
        fig.add_vline(x="2022-02-24", line_dash="dash", line_color="red")
    fig.update_layout(legend_orientation="h")
    st.plotly_chart(fig, width="stretch")
    data_tools(weekly_view, "Banca Centrale Russa", "https://www.cbr.ru/development/DWS/",
               "riserve-settimanali")

    st.subheader("Struttura delle riserve: valuta estera vs oro")
    st.caption("La voce valuta estera non separa yuan utilizzabili, asset occidentali congelati e altre componenti.")
    structure_dates = date_range(monthly.date.min().date(), monthly.date.max().date(),
                                 "structure-dates")
    monthly_view = filter_dates(monthly, structure_dates)
    monthly_view, structure_x, structure_facet = comparison_frame(
        monthly_view, structure_dates, "mensile")
    if structure_facet:
        structure_chart = monthly_view.melt(
            ["date", "periodo", "anno"], value_vars=["fx_mln_usd", "gold_mln_usd"],
            var_name="componente", value_name="mln_usd")
        structure_chart["componente"] = structure_chart.componente.map(
            {"fx_mln_usd": "Valuta estera", "gold_mln_usd": "Oro monetario"})
        fig2 = px.line(structure_chart, x=structure_x, y="mln_usd", color=structure_facet,
                       line_dash="componente",
                       labels={"periodo": "mese", "componente": "", "anno": "Anno"})
        fig2.update_xaxes(tickformat="%b")
    else:
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
    rate_dates = date_range(key_rate.date.min().date(), key_rate.date.max().date(), "rate-dates")
    key_view = filter_dates(key_rate, rate_dates)
    key_view, rate_x, rate_facet = comparison_frame(key_view, rate_dates, "giornaliera")
    fig3 = px.line(key_view, x=rate_x, y="key_rate_pct", color=rate_facet,
                   labels={"date": "", "periodo": "mese",
                           "key_rate_pct": "%", "anno": "Anno"})
    if rate_facet:
        fig3.update_xaxes(tickformat="%b")
    fig3.update_traces(line_shape="hv")
    st.plotly_chart(fig3, width="stretch")
    data_tools(key_view, "Banca Centrale Russa", "https://www.cbr.ru/development/DWS/", "tasso-chiave")

    st.subheader("Cambi ufficiali (₽ per unità)")
    st.caption("Tassi ufficiali CBR: non rappresentano necessariamente tutta la pressione di mercato sul rublo.")
    fx_date_col, fx_currency_col, fx_mode_col = st.columns([2, 1, 1])
    with fx_date_col:
        fx_dates = date_range(fx.date.min().date(), fx.date.max().date(), "fx-dates")
    with fx_currency_col:
        currencies = st.multiselect("Valute", sorted(fx.currency.unique()),
                                    default=sorted(fx.currency.unique()), key="currencies")
    with fx_mode_col:
        fx_mode = st.selectbox("Visualizzazione",
                               ["Cambio ufficiale", "Indice 100", "Variazione giornaliera %",
                                "Volatilità mobile 20 giorni"], key="fx-mode")
    fx_analysis = fx.copy()
    fx_analysis["variazione_pct"] = fx_analysis.groupby("currency").rub_per_unit.pct_change() * 100
    fx_analysis["volatilita_20"] = fx_analysis.groupby("currency").variazione_pct.transform(
        lambda values: values.rolling(20).std())
    fx_view = filter_dates(fx_analysis, fx_dates).copy()
    fx_view = fx_view[fx_view.currency.isin(currencies)]
    fx_view, fx_x, fx_facet = comparison_frame(fx_view, fx_dates, "giornaliera")
    fx_groups = ["currency", "anno"] if fx_facet else ["currency"]
    fx_view["indice_100"] = fx_view.groupby(fx_groups).rub_per_unit.transform(
        lambda values: values / values.iloc[0] * 100)
    fx_columns = {
        "Cambio ufficiale": ("rub_per_unit", "₽ per unità"),
        "Indice 100": ("indice_100", "indice (inizio intervallo = 100)"),
        "Variazione giornaliera %": ("variazione_pct", "% giornaliera"),
        "Volatilità mobile 20 giorni": ("volatilita_20", "deviazione standard, %"),
    }
    fx_column, fx_label = fx_columns[fx_mode]
    fx_figure = px.line(fx_view, x=fx_x, y=fx_column,
                        color=fx_facet or "currency",
                        line_dash="currency" if fx_facet else None,
                        labels={"date": "", fx_column: fx_label,
                                "periodo": "mese", "currency": "Valuta",
                                "anno": "Anno"})
    if fx_facet:
        fx_figure.update_xaxes(tickformat="%b")
    st.plotly_chart(fx_figure, width="stretch")
    data_tools(fx_view, "Banca Centrale Russa", "https://www.cbr.ru/development/DWS/", "cambi")

with crea_tab:
    st.header("Ricavi russi dalle esportazioni di combustibili fossili")
    st.caption("Stime CREA · aggiornamento giornaliero · valori soggetti a revisioni metodologiche")
    counter_total = crea_counter[crea_counter.destination_region == "Total"].iloc[-1]
    counter_eu = crea_counter[crea_counter.destination_region == "EU"].iloc[-1]
    counter_china = crea_counter[crea_counter.destination_region == "China"].iloc[-1]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ricavi totali dal 24.02.2022", f"€{counter_total.total_eur / 1e9:,.0f} mld")
    m2.metric("Acquisti UE", f"€{counter_eu.total_eur / 1e9:,.0f} mld")
    m3.metric("Acquisti Cina", f"€{counter_china.total_eur / 1e9:,.0f} mld")
    m4.metric("Ricavi stimati al giorno", f"€{counter_total.eur_per_day / 1e6:,.0f} mln")

    st.subheader("Ricavi per combustibile — media giornaliera mensile")
    total_monthly = crea_monthly[crea_monthly.destination_region == "Total"]
    fuels = {"oil_eur_per_day": "Petrolio", "gas_eur_per_day": "Gas",
             "coal_eur_per_day": "Carbone"}
    fuel_date_col, fuel_series_col, fuel_mode_col = st.columns([2, 1, 1])
    with fuel_date_col:
        fuel_dates = date_range(total_monthly.date.min().date(),
                                total_monthly.date.max().date(), "crea-fuel-dates")
    with fuel_series_col:
        selected_fuels = st.multiselect("Combustibili", fuels, default=list(fuels),
                                        format_func=fuels.get, key="crea-fuels")
    with fuel_mode_col:
        fuel_mode = st.selectbox("Visualizzazione",
                                 ["Valore mensile", "Media mobile 3 mesi", "Variazione annua %"],
                                 key="crea-fuel-mode")
    fuel_analysis = total_monthly.copy()
    suffix = {"Valore mensile": "", "Media mobile 3 mesi": "_ma3",
              "Variazione annua %": "_yoy"}[fuel_mode]
    for column in fuels:
        fuel_analysis[f"{column}_ma3"] = fuel_analysis[column].rolling(3).mean()
        fuel_analysis[f"{column}_yoy"] = fuel_analysis[column].pct_change(12) * 100
    fuel_view = filter_dates(fuel_analysis, fuel_dates)
    fuel_view, fuel_x, fuel_facet = comparison_frame(fuel_view, fuel_dates, "mensile")
    value_columns = [f"{column}{suffix}" for column in selected_fuels]
    fuel_ids = ["date"] + (["periodo", "anno"] if fuel_facet else [])
    fuel_chart = fuel_view.melt(fuel_ids, value_vars=value_columns,
                                var_name="combustibile", value_name="valore")
    fuel_chart["combustibile"] = fuel_chart.combustibile.str.replace(
        suffix + "$", "", regex=True).map(fuels) if suffix else fuel_chart.combustibile.map(fuels)
    if fuel_mode != "Variazione annua %":
        fuel_chart["valore"] /= 1e6
    fuel_label = "% rispetto allo stesso mese dell'anno precedente" if suffix == "_yoy" else "mln EUR/giorno"
    fuel_figure = px.area if fuel_mode == "Valore mensile" else px.line
    fuel_constructor = px.line if fuel_facet else fuel_figure
    fuel_style = {"line_dash": "combustibile"} if fuel_facet else {}
    fuel_plot = fuel_constructor(
        fuel_chart, x=fuel_x, y="valore", color=fuel_facet or "combustibile",
        labels={"date": "", "periodo": "mese", "valore": fuel_label,
                "combustibile": "Combustibile", "anno": "Anno"}, **fuel_style)
    if fuel_facet:
        fuel_plot.update_xaxes(tickformat="%b")
    st.plotly_chart(fuel_plot, width="stretch")
    data_tools(fuel_view[["date"] + value_columns], "Russia Fossil Tracker — CREA",
               "https://www.russiafossiltracker.com/", "crea-ricavi-combustibile")

    st.subheader("Ricavi per destinazione — media giornaliera mensile")
    regions_monthly = crea_monthly[crea_monthly.destination_region != "Total"]
    region_dates = date_range(regions_monthly.date.min().date(),
                              regions_monthly.date.max().date(), "crea-region-dates")
    available_regions = sorted(regions_monthly.destination_region.unique())
    selected_regions = st.multiselect("Destinazioni", available_regions,
                                      default=["China", "EU", "India", "Türkiye"],
                                      key="crea-regions")
    region_view = filter_dates(regions_monthly, region_dates)
    region_view = region_view[region_view.destination_region.isin(selected_regions)]
    region_chart = region_view.assign(mln_eur_giorno=region_view.total_eur_per_day / 1e6)
    region_chart, region_x, region_facet = comparison_frame(
        region_chart, region_dates, "mensile")
    region_figure = px.line(region_chart, x=region_x, y="mln_eur_giorno",
                           color=region_facet or "destination_region",
                           line_dash="destination_region" if region_facet else None,
                           labels={"date": "", "periodo": "mese",
                                   "mln_eur_giorno": "mln EUR/giorno",
                                   "destination_region": "Destinazione",
                                   "anno": "Anno"})
    if region_facet:
        region_figure.update_xaxes(tickformat="%b")
    st.plotly_chart(region_figure, width="stretch")
    data_tools(region_view, "Russia Fossil Tracker — CREA",
               "https://www.russiafossiltracker.com/", "crea-ricavi-destinazione")

    st.subheader("Ricavi cumulativi per destinazione")
    current_regions = crea_counter[crea_counter.destination_region != "Total"].copy()
    selected_current = st.multiselect("Destinazioni", sorted(current_regions.destination_region),
                                      default=sorted(current_regions.destination_region),
                                      key="crea-current-regions")
    current_view = current_regions[current_regions.destination_region.isin(selected_current)].copy()
    current_view["mld_eur"] = current_view.total_eur / 1e9
    current_view = current_view.sort_values("mld_eur", ascending=False)
    st.plotly_chart(px.bar(current_view, x="destination_region", y="mld_eur",
                          labels={"destination_region": "", "mld_eur": "mld EUR"}),
                    width="stretch")
    data_tools(current_view.drop(columns="mld_eur"), "Russia Fossil Tracker — CREA",
               "https://www.russiafossiltracker.com/", "crea-ricavi-cumulativi")

    st.info("CREA combina dati Kpler, Eurostat, ENTSOG, UN Comtrade e modelli di prezzo. "
            "Le serie sono stime, non contabilità ufficiale russa, e possono essere riviste.")

with maritime_tab:
    st.header("Esportazioni marittime russe di greggio")
    st.caption("Dati CREA/Kpler · settimane concluse la domenica · `trade_count` indica "
               "operazioni commerciali, non necessariamente navi uniche")
    ports_daily = crea_ports.copy()
    ports_daily["week_ending"] = (
        ports_daily.date + pd.to_timedelta(6 - ports_daily.date.dt.weekday, unit="D")
    )
    weekly_ports = ports_daily.groupby(["week_ending", "port", "area"], as_index=False).agg(
        trade_count=("trade_count", "sum"), value_tonne=("value_tonne", "sum"),
        value_m3=("value_m3", "sum"), value_eur=("value_eur", "sum"),
    )
    weekly_ports = weekly_ports[weekly_ports.week_ending <= ports_daily.date.max()]
    weekly_total = weekly_ports.groupby("week_ending", as_index=False).agg(
        trade_count=("trade_count", "sum"), value_tonne=("value_tonne", "sum")
    ).sort_values("week_ending")
    weekly_total["tonnes_per_operation"] = weekly_total.value_tonne / weekly_total.trade_count
    latest, previous = weekly_total.iloc[-1], weekly_total.iloc[-2]
    four_week = weekly_total.tail(4).value_tonne.mean()
    previous_four = weekly_total.iloc[-8:-4].value_tonne.mean()
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Carichi nell'ultima settimana", f"{int(latest.trade_count)}",
              f"{latest.trade_count - previous.trade_count:+.0f} vs precedente")
    s2.metric("Volume settimanale", f"{latest.value_tonne / 1e6:.2f} mln t",
              f"{(latest.value_tonne / previous.value_tonne - 1) * 100:+.1f}%")
    s3.metric("Media mobile 4 settimane", f"{four_week / 1e6:.2f} mln t")
    s4.metric("4 settimane vs 4 precedenti", f"{(four_week / previous_four - 1) * 100:+.1f}%")
    s5.metric("Tonnellate per operazione", f"{latest.tonnes_per_operation / 1e3:.0f} mila")
    st.caption(f"Ultima settimana completa: {latest.week_ending:%d/%m/%Y}")

    main_ports = ["Primorsk", "Ust Luga", "Novorossiysk", "Murmansk", "Kozmino",
                  "De Kastri", "Varandey"]
    available_ports = sorted(weekly_ports.port.unique())
    default_ports = [port for port in main_ports if port in available_ports]
    st.subheader("Carichi settimanali per terminale")
    load_dates = date_range(weekly_ports.week_ending.min().date(),
                            weekly_ports.week_ending.max().date(), "port-load-dates")
    load_ports = st.multiselect("Terminali", available_ports, default=default_ports,
                                key="port-load-ports")
    load_view = filter_dates(weekly_ports.rename(columns={"week_ending": "date"}), load_dates)
    load_view = load_view[load_view.port.isin(load_ports)]
    load_view, load_x, load_facet = comparison_frame(load_view, load_dates, "settimanale")
    if load_facet:
        load_figure = px.line(
            load_view, x=load_x, y="trade_count", color=load_facet, line_dash="port",
            labels={"periodo": "mese", "trade_count": "operazioni di carico",
                    "port": "Terminale", "anno": "Anno"})
        load_figure.update_xaxes(tickformat="%b")
    else:
        load_figure = px.bar(load_view, x=load_x, y="trade_count", color="port",
                             labels={"date": "", "trade_count": "operazioni di carico",
                                     "port": "Terminale"})
    st.plotly_chart(load_figure, width="stretch")
    data_tools(load_view, "Russia Fossil Tracker — CREA",
               "https://api.russiafossiltracker.com/", "crea-carichi-porti")

    st.subheader("Volume settimanale e media mobile a quattro settimane")
    available_areas = sorted(weekly_ports.area.dropna().unique())
    volume_date_col, volume_area_col, volume_mode_col = st.columns([2, 1, 1])
    with volume_date_col:
        volume_dates = date_range(weekly_ports.week_ending.min().date(),
                                  weekly_ports.week_ending.max().date(), "port-volume-dates")
    with volume_area_col:
        volume_areas = st.multiselect("Aree", available_areas, default=available_areas,
                                      key="port-volume-areas")
    with volume_mode_col:
        maritime_mode = st.selectbox("Indicatore", ["Volume", "Tonnellate per operazione"],
                                     key="maritime-mode")
    volume_all = weekly_ports[weekly_ports.area.isin(volume_areas)].groupby(
        "week_ending", as_index=False).agg(value_tonne=("value_tonne", "sum"),
                                            trade_count=("trade_count", "sum")).sort_values("week_ending")
    volume_all["volume_mln_t"] = volume_all.value_tonne / 1e6
    volume_all["tonnellate_operazione"] = volume_all.value_tonne / volume_all.trade_count
    base_column = "volume_mln_t" if maritime_mode == "Volume" else "tonnellate_operazione"
    volume_all["media_4_settimane"] = volume_all[base_column].rolling(4).mean()
    volume_view = filter_dates(volume_all.rename(columns={"week_ending": "date"}), volume_dates)
    volume_view, volume_x, volume_facet = comparison_frame(
        volume_view, volume_dates, "settimanale")
    volume_ids = ["date"] + (["periodo", "anno"] if volume_facet else [])
    volume_chart = volume_view.melt(volume_ids,
                                    value_vars=[base_column, "media_4_settimane"],
                                    var_name="serie", value_name="valore")
    volume_chart["serie"] = volume_chart.serie.map(
        {base_column: maritime_mode, "media_4_settimane": "Media mobile 4 settimane"}
    )
    maritime_label = "milioni di tonnellate" if maritime_mode == "Volume" else "tonnellate per operazione"
    volume_figure = px.line(
        volume_chart, x=volume_x, y="valore", color=volume_facet or "serie",
        line_dash="serie" if volume_facet else None,
        labels={"date": "", "periodo": "mese", "valore": maritime_label,
                "serie": "", "anno": "Anno"})
    if volume_facet:
        volume_figure.update_xaxes(tickformat="%b")
    st.plotly_chart(volume_figure, width="stretch")
    data_tools(volume_view, "Russia Fossil Tracker — CREA",
               "https://api.russiafossiltracker.com/", "crea-volumi-marittimi")

    st.subheader("Mappa temporale dell'attività dei terminali")
    heat_dates = date_range(weekly_ports.week_ending.min().date(),
                            weekly_ports.week_ending.max().date(), "port-heat-dates")
    heat_ports = st.multiselect("Terminali", available_ports, default=default_ports,
                                key="port-heat-ports")
    heat_view = filter_dates(weekly_ports.rename(columns={"week_ending": "date"}), heat_dates)
    heat_view = heat_view[heat_view.port.isin(heat_ports)]
    heat_view, heat_x, heat_facet = comparison_frame(heat_view, heat_dates, "settimanale")
    if heat_facet:
        heatmap = px.line(
            heat_view, x=heat_x, y="trade_count", color=heat_facet, line_dash="port",
            labels={"periodo": "mese", "port": "Terminale",
                    "trade_count": "carichi", "anno": "Anno"})
        heatmap.update_xaxes(tickformat="%b")
    else:
        heat_table = heat_view.pivot_table(index="port", columns="date", values="trade_count",
                                           aggfunc="sum", fill_value=0)
        heatmap = go.Figure(go.Heatmap(x=heat_table.columns, y=heat_table.index,
                                       z=heat_table.values, colorscale="Blues",
                                       colorbar_title="carichi"))
        heatmap.update_layout(xaxis_title="", yaxis_title="")
    st.plotly_chart(heatmap, width="stretch")
    data_tools(heat_view, "Russia Fossil Tracker — CREA",
               "https://api.russiafossiltracker.com/", "crea-heatmap-porti")
    st.caption("Confronto editoriale: [ultimo aggiornamento settimanale di Julian Lee su Bloomberg]"
               "(https://www.bloomberg.com/news/articles/2026-08-18/"
               "russia-s-oil-exports-extend-their-slump-amid-ukrainian-drone-strikes). "
               "Le metodologie Bloomberg e CREA non sono direttamente equivalenti.")

with data_tab:
    st.header("Tutti i dati")
    st.markdown("- [Banca Centrale Russa](https://www.cbr.ru/development/DWS/)\n"
                "- [Dataset dei report dello Stato Maggiore ucraino]"
                "(https://github.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset)\n"
                "- [Russia Fossil Tracker — CREA](https://www.russiafossiltracker.com/)")
    all_data = io.BytesIO()
    with pd.ExcelWriter(all_data, engine="openpyxl") as writer:
        for name, df in {"Guerra": war, "Riserve settimanali": weekly,
                         "Riserve mensili": monthly, "Tasso chiave": key_rate,
                         "Cambi": fx, "CREA mensile": crea_monthly,
                         "CREA cumulativo": crea_counter, "CREA porti": crea_ports}.items():
            df.to_excel(writer, sheet_name=name, index=False)
    st.download_button("⬇️ Scarica tutti i dati in Excel", all_data.getvalue(),
                       "russia-tracker-dati.xlsx", key="xlsx-all")

st.divider()
st.caption(f"Ultimo dato riserve: {weekly.iloc[-1].date.date()} · "
           f"ultimo dato guerra: {war.iloc[-1].date.date()} · "
           f"ultimo dato CREA: {crea_counter.updated_on.iloc[-1][:10]} · Progetto a scopo informativo.")
