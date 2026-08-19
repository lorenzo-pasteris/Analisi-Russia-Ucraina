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

    war_ma = war.copy()
    for col in ["daily_personnel", "daily_drones", "daily_cruise_missiles"]:
        war_ma[f"{col}_ma7"] = war_ma[col].rolling(7).mean()
    st.subheader("Perdite giornaliere di personale (media mobile 7gg)")
    personnel_dates = st.date_input("Intervallo", (war.date.min().date(), war.date.max().date()),
                                    min_value=war.date.min().date(), max_value=TODAY,
                                    key="personnel-dates")
    personnel_view = filter_dates(war_ma, personnel_dates)
    st.plotly_chart(px.line(personnel_view, x="date", y="daily_personnel_ma7",
                           labels={"date": "", "daily_personnel_ma7": "uomini/giorno"}),
                    width="stretch")
    data_tools(personnel_view[["date", "personnel", "daily_personnel", "daily_personnel_ma7"]],
               "dataset open-source dei report ucraini",
               "https://github.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset",
               "perdite-personale")

    st.subheader("UAV e missili da crociera dichiarati persi/distrutti (media mobile 7gg)")
    missile_dates = st.date_input("Intervallo", (war.date.min().date(), war.date.max().date()),
                                  min_value=war.date.min().date(), max_value=TODAY,
                                  key="missile-dates")
    missile_view = filter_dates(war_ma, missile_dates)
    air_weapons = {"daily_drones_ma7": "UAV", "daily_cruise_missiles_ma7": "Missili da crociera"}
    selected_air_weapons = st.multiselect("Serie da visualizzare", air_weapons,
                                          default=list(air_weapons), format_func=air_weapons.get,
                                          key="air-weapons")
    figw2 = go.Figure()
    for column in selected_air_weapons:
        figw2.add_trace(go.Scatter(x=missile_view.date, y=missile_view[column],
                                   name=air_weapons[column]))
    figw2.update_layout(yaxis_title="unità/giorno", legend_orientation="h")
    st.plotly_chart(figw2, width="stretch")
    data_tools(missile_view[["date", "drones", "cruise_missiles", "daily_drones",
                       "daily_cruise_missiles"]], "dataset open-source dei report ucraini",
               "https://github.com/PetroIvaniuk/2022-Ukraine-Russia-War-Dataset",
               "droni-missili")

    equipment = {"tanks": "Carri armati", "apc": "Blindati (APC)",
                 "artillery": "Artiglieria"}
    st.subheader("Mezzi terrestri — perdite cumulative")
    equipment_dates = st.date_input("Intervallo", (war.date.min().date(), war.date.max().date()),
                                    min_value=war.date.min().date(), max_value=TODAY,
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

    st.subheader("Aviazione — perdite cumulative")
    aviation = equipment_view[["date", "aircraft", "helicopters"]].rename(
        columns={"aircraft": "Aerei", "helicopters": "Elicotteri"})
    aviation_chart = aviation.melt("date", var_name="mezzo", value_name="unità")
    st.plotly_chart(px.line(aviation_chart, x="date", y="unità", color="mezzo",
                           labels={"date": "", "mezzo": ""}), width="stretch")
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

    st.subheader("Riserve internazionali* (settimanali, mld USD)")
    reserve_dates = st.date_input("Intervallo", (weekly.date.min().date(), weekly.date.max().date()),
                                  min_value=weekly.date.min().date(), max_value=TODAY,
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
    st.caption("La voce valuta estera non separa yuan utilizzabili, asset occidentali congelati e altre componenti.")
    structure_dates = st.date_input("Intervallo", (monthly.date.min().date(), monthly.date.max().date()),
                                    min_value=monthly.date.min().date(), max_value=TODAY,
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
                               min_value=key_rate.date.min().date(), max_value=TODAY,
                               key="rate-dates")
    key_view = filter_dates(key_rate, rate_dates)
    fig3 = px.line(key_view, x="date", y="key_rate_pct", labels={"date": "", "key_rate_pct": "%"})
    fig3.update_traces(line_shape="hv")
    st.plotly_chart(fig3, width="stretch")
    data_tools(key_view, "Banca Centrale Russa", "https://www.cbr.ru/development/DWS/", "tasso-chiave")

    st.subheader("Cambi ufficiali (₽ per unità)")
    st.caption("Tassi ufficiali CBR: non rappresentano necessariamente tutta la pressione di mercato sul rublo.")
    fx_dates = st.date_input("Intervallo", (fx.date.min().date(), fx.date.max().date()),
                             min_value=fx.date.min().date(), max_value=TODAY,
                             key="fx-dates")
    fx_view = filter_dates(fx, fx_dates)
    currencies = st.multiselect("Valute da visualizzare", sorted(fx.currency.unique()),
                                default=sorted(fx.currency.unique()), key="currencies")
    fx_view = fx_view[fx_view.currency.isin(currencies)]
    st.plotly_chart(px.line(fx_view, x="date", y="rub_per_unit", color="currency",
                           labels={"date": "", "rub_per_unit": "₽"}), width="stretch")
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
    fuel_dates = st.date_input("Intervallo", (total_monthly.date.min().date(),
                                               total_monthly.date.max().date()),
                               min_value=total_monthly.date.min().date(),
                               max_value=TODAY, key="crea-fuel-dates")
    fuels = {"oil_eur_per_day": "Petrolio", "gas_eur_per_day": "Gas",
             "coal_eur_per_day": "Carbone"}
    selected_fuels = st.multiselect("Combustibili", fuels, default=list(fuels),
                                    format_func=fuels.get, key="crea-fuels")
    fuel_view = filter_dates(total_monthly, fuel_dates)
    fuel_chart = fuel_view.melt("date", value_vars=selected_fuels,
                                var_name="combustibile", value_name="eur_per_day")
    fuel_chart["combustibile"] = fuel_chart.combustibile.map(fuels)
    fuel_chart["mln_eur_giorno"] = fuel_chart.eur_per_day / 1e6
    st.plotly_chart(px.area(fuel_chart, x="date", y="mln_eur_giorno", color="combustibile",
                           labels={"date": "", "mln_eur_giorno": "mln EUR/giorno",
                                   "combustibile": "Combustibile"}), width="stretch")
    data_tools(fuel_view[["date"] + selected_fuels], "Russia Fossil Tracker — CREA",
               "https://www.russiafossiltracker.com/", "crea-ricavi-combustibile")

    st.subheader("Ricavi per destinazione — media giornaliera mensile")
    regions_monthly = crea_monthly[crea_monthly.destination_region != "Total"]
    region_dates = st.date_input("Intervallo", (regions_monthly.date.min().date(),
                                                 regions_monthly.date.max().date()),
                                 min_value=regions_monthly.date.min().date(),
                                 max_value=TODAY, key="crea-region-dates")
    available_regions = sorted(regions_monthly.destination_region.unique())
    selected_regions = st.multiselect("Destinazioni", available_regions,
                                      default=["China", "EU", "India", "Türkiye"],
                                      key="crea-regions")
    region_view = filter_dates(regions_monthly, region_dates)
    region_view = region_view[region_view.destination_region.isin(selected_regions)]
    region_chart = region_view.assign(mln_eur_giorno=region_view.total_eur_per_day / 1e6)
    st.plotly_chart(px.line(region_chart, x="date", y="mln_eur_giorno",
                           color="destination_region",
                           labels={"date": "", "mln_eur_giorno": "mln EUR/giorno",
                                   "destination_region": "Destinazione"}), width="stretch")
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
    latest, previous = weekly_total.iloc[-1], weekly_total.iloc[-2]
    four_week = weekly_total.tail(4).value_tonne.mean()
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Carichi nell'ultima settimana", f"{int(latest.trade_count)}",
              f"{latest.trade_count - previous.trade_count:+.0f} vs precedente")
    s2.metric("Volume settimanale", f"{latest.value_tonne / 1e6:.2f} mln t",
              f"{(latest.value_tonne / previous.value_tonne - 1) * 100:+.1f}%")
    s3.metric("Media mobile 4 settimane", f"{four_week / 1e6:.2f} mln t")
    s4.metric("Settimana conclusa", latest.week_ending.strftime("%d/%m/%Y"))

    main_ports = ["Primorsk", "Ust Luga", "Novorossiysk", "Murmansk", "Kozmino",
                  "De Kastri", "Varandey"]
    available_ports = sorted(weekly_ports.port.unique())
    default_ports = [port for port in main_ports if port in available_ports]
    st.subheader("Carichi settimanali per terminale")
    load_dates = st.date_input("Intervallo", (weekly_ports.week_ending.min().date(),
                                               weekly_ports.week_ending.max().date()),
                               min_value=weekly_ports.week_ending.min().date(),
                               max_value=TODAY, key="port-load-dates")
    load_ports = st.multiselect("Terminali", available_ports, default=default_ports,
                                key="port-load-ports")
    load_view = filter_dates(weekly_ports.rename(columns={"week_ending": "date"}), load_dates)
    load_view = load_view[load_view.port.isin(load_ports)]
    st.plotly_chart(px.bar(load_view, x="date", y="trade_count", color="port",
                          labels={"date": "", "trade_count": "operazioni di carico",
                                  "port": "Terminale"}), width="stretch")
    data_tools(load_view, "Russia Fossil Tracker — CREA",
               "https://api.russiafossiltracker.com/", "crea-carichi-porti")

    st.subheader("Volume settimanale e media mobile a quattro settimane")
    volume_dates = st.date_input("Intervallo", (weekly_ports.week_ending.min().date(),
                                                 weekly_ports.week_ending.max().date()),
                                 min_value=weekly_ports.week_ending.min().date(),
                                 max_value=TODAY, key="port-volume-dates")
    available_areas = sorted(weekly_ports.area.dropna().unique())
    volume_areas = st.multiselect("Aree", available_areas, default=available_areas,
                                  key="port-volume-areas")
    volume_all = weekly_ports[weekly_ports.area.isin(volume_areas)].groupby(
        "week_ending", as_index=False).value_tonne.sum().sort_values("week_ending")
    volume_all["volume_mln_t"] = volume_all.value_tonne / 1e6
    volume_all["media_4_settimane"] = volume_all.volume_mln_t.rolling(4).mean()
    volume_view = filter_dates(volume_all.rename(columns={"week_ending": "date"}), volume_dates)
    volume_chart = volume_view.melt("date", value_vars=["volume_mln_t", "media_4_settimane"],
                                    var_name="serie", value_name="milioni_tonnellate")
    volume_chart["serie"] = volume_chart.serie.map(
        {"volume_mln_t": "Volume settimanale", "media_4_settimane": "Media mobile 4 settimane"}
    )
    st.plotly_chart(px.line(volume_chart, x="date", y="milioni_tonnellate", color="serie",
                           labels={"date": "", "milioni_tonnellate": "milioni di tonnellate",
                                   "serie": ""}), width="stretch")
    data_tools(volume_view, "Russia Fossil Tracker — CREA",
               "https://api.russiafossiltracker.com/", "crea-volumi-marittimi")

    st.subheader("Mappa temporale dell'attività dei terminali")
    heat_dates = st.date_input("Intervallo", (weekly_ports.week_ending.min().date(),
                                               weekly_ports.week_ending.max().date()),
                               min_value=weekly_ports.week_ending.min().date(),
                               max_value=TODAY, key="port-heat-dates")
    heat_ports = st.multiselect("Terminali", available_ports, default=default_ports,
                                key="port-heat-ports")
    heat_view = filter_dates(weekly_ports.rename(columns={"week_ending": "date"}), heat_dates)
    heat_view = heat_view[heat_view.port.isin(heat_ports)]
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
