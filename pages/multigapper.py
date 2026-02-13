import streamlit as st
import pandas as pd
import numpy as np
from dateutil import parser
import yfinance as yf

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="Statistiche multi gapper",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 Statistiche multi gapper")

# Carica il CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("theme.css")


# -------------------------------------------------
# region LOAD DATA
# -------------------------------------------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/15ev2l8av7iil_-HsXMZihKxV-B5MgTVO-LnK1y_f2-o/export?format=csv"
df = pd.read_csv(SHEET_URL)
df.columns = df.columns.str.strip()

# --- PULIZIA DATI ----
# Rimuovo eventuali spazi nei nomi colonne
df.columns = df.columns.str.strip()

# Funzione robusta per parse date con dayfirst
def parse_date(x):
    try:
        return parser.parse(str(x).strip(), dayfirst=True)
    except:
        return pd.NaT

df["Date"] = df["Date"].apply(parse_date)
df["Date"] = df["Date"].apply(lambda x: x.date() if pd.notna(x) else pd.NaT)

df["Chiusura"] = df["Chiusura"].str.upper().str.strip()

# Funzione per convertire percentuali da stringhe con virgola e %
def parse_percent(x):
    try:
        if pd.isna(x):
            return np.nan
        x = str(x).replace('%', '').replace(',', '.')
        return float(x)
    except:
        return np.nan

# Pulizia colonne percentuali
percent_cols = ["GAP", "%Open_PMH", "%OH", "%OL"]
for col in percent_cols:
    if col in df.columns:
        df[col] = df[col].apply(parse_percent)

# Pulizia colonne numeriche con virgola e separatore migliaia
num_cols = ["OPEN", "Float", "break", "Close"]
for col in num_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(
            df[col].astype(str)
            .str.replace('.', '', regex=False)   # rimuove punti migliaia
            .str.replace(',', '.', regex=False), # converte virgole decimali
            errors="coerce"
        )

# Sostituisco NaN con valori neutri per non perdere righe
for col in ["GAP", "Float", "%Open_PMH", "OPEN", "%OH", "%OL", "break"]:
    if col in df.columns:
        df[col] = df[col].fillna(0)

# --- PULIZIA COLONNE TIMEFRAME (Close / High / Low) ---
tf_cols = [
    c for c in df.columns
    if c.startswith(("%Close_", "Close_", "High_", "Low_"))
]

for col in tf_cols:
    df[col] = pd.to_numeric(
        df[col].astype(str)
        .str.replace(",", ".", regex=False).str.strip(),
        errors="coerce"
    )

# endregion


# -----------------------------------------------
# region CONTROLLO DATI 
# -----------------------------------------------

problemi_dati = False  # flag per sapere se ci sono problemi

# Mostra il titolo solo se ci sono problemi
if problemi_dati:
    st.markdown('<h3 style="font-size:16px; color:#FFFFFF;">🛠️ Controllo dati</h3>', unsafe_allow_html=True)

# Date non valide
invalid_dates = df[df["Date"].isna()]
if not invalid_dates.empty:
    st.warning(f"⚠️ Attenzione: {len(invalid_dates)} righe con date non valide")
    st.dataframe(invalid_dates[["Ticker", "Date"]])

# Numeri non validi nelle colonne numeriche principali
for col in ["GAP", "Float", "%Open_PMH", "OPEN", "%OH", "%OL", "break"]:
    if col in df.columns:
        invalid_nums = df[df[col].isna()]
        if not invalid_nums.empty:
            st.warning(f"⚠️ Attenzione: {len(invalid_nums)} righe con valori non numerici in '{col}'")
            st.dataframe(invalid_nums[["Ticker", col]])

# endregion

# ---------------------------------------
# region COLONNE CALCOLATE
# ---------------------------------------

# Calcolo day_close_pct
if "Close" in df.columns and "OPEN" in df.columns:
    df["day_close_pct"] = (df["Close"] - df["OPEN"]) / df["OPEN"] * 100

# endregion

# -------------------------------------------------
# region SIDEBAR FILTRI
# -------------------------------------------------
st.sidebar.header("🔍 Filtri")

date_range = st.sidebar.date_input("Intervallo date", [])
min_gap = st.sidebar.number_input("GAP minimo (%)", 0, 1000, 40)

col_mc1, col_mc2 = st.sidebar.columns(2)
mc_min = col_mc1.number_input("MC Min ($M)", 0, 2000, 0, step=10)
mc_max = col_mc2.number_input("MC Max ($M)", 0, 2000, 2000, step=10)

col_f1, col_f2 = st.sidebar.columns(2)
float_min = col_f1.number_input("Float MIN", 0, 1_000_000_000, 0, step=100_000)
float_max = col_f2.number_input("Float MAX", 0, 1_000_000_000, 50_000_000, step=100_000)

min_open_pmh = st.sidebar.number_input("%Open_PMH minimo", -100, 100, -100)

col_o1, col_o2 = st.sidebar.columns(2)
open_min = col_o1.number_input("Open MIN", 0.0, 100.0, 1.0, step=0.1)
open_max = col_o2.number_input("Open MAX", 0.0, 100.0, 100.0, step=0.1)

st.sidebar.subheader("📊 Multi-gapper day")

col_g1, col_g2 = st.sidebar.columns(2)

min_gapper_day = col_g1.number_input(
    "Gapper MIN",
    min_value=1,
    max_value=20,
    value=3,
    step=1,
    help= "numero minimo di gapper in giornata"
)

max_gapper_day = col_g2.number_input(
    "Gapper MAX",
    min_value=min_gapper_day,
    max_value=50,
    value=10,
    step=1,
    help= "numero massimo di gapper in giornata"
)

# -------------------------------------------------
# APPLY FILTERS
# -------------------------------------------------
filtered = df.copy()

filtered = filtered[
    (filtered["GAP"] >= min_gap) &
    (filtered["%Open_PMH"] >= min_open_pmh) &
    (filtered["Float"] >= float_min) &
    (filtered["Float"] <= float_max) &
    (filtered["OPEN"] >= open_min) &
    (filtered["OPEN"] <= open_max)
]

if len(date_range) == 2:
    start, end = date_range
    filtered = filtered[(filtered["Date"] >= start) & (filtered["Date"] <= end)]

filtered = filtered[
    (filtered["Market Cap"] >= mc_min * 1_000_000) &
    (filtered["Market Cap"] <= mc_max * 1_000_000)
]

filtered["is_red"] = filtered["Chiusura"] == "RED"
filtered["is_green"] = filtered["Chiusura"] == "GREEN"

# -------------------------------------------------
# FILTRO MULTI-GAPPER
# creazione dataset gapper
# -------------------------------------------------

# Conteggio gapper per ogni giornata
gapper_per_day = (
    filtered
    .groupby("Date")["Ticker"]
    .count()
    .reset_index(name="n_gapper_day")
)

# Teniamo solo le giornate con almeno N gapper
multi_gapper_days = gapper_per_day[
    (gapper_per_day["n_gapper_day"] >= min_gapper_day) &
    (gapper_per_day["n_gapper_day"] <= max_gapper_day)
]

filtered = filtered[
    filtered["Date"].isin(multi_gapper_days["Date"])
].copy()


# endregion


# -------------------------------------------------
# region KPI
# creazione dei kpi
# -------------------------------------------------

total = len(filtered)
gap_mean = filtered["GAP"].mean() if total else 0
gap_median = filtered["GAP"].median() if total else 0
red_close = (filtered["Chiusura"] == "RED").mean() * 100 if total else 0
num_days_mg = filtered["Date"].nunique()

# -------------------------------------------------
# Numero medio gapper per giornata multi-gap
# -------------------------------------------------

gapper_per_day_mg = (
    filtered
    .groupby("Date")
    .size()          # numero gapper in quel giorno
)

avg_gapper_per_day = (
    gapper_per_day_mg.mean()
    if not gapper_per_day_mg.empty else 0
)

# Medie delle percentuali già presenti nel dataset
gap_red       = filtered.loc[filtered["is_red"], "GAP"].mean()
gap_green     = filtered.loc[filtered["is_green"], "GAP"].mean()

open_pmh_red  = filtered.loc[filtered["is_red"], "%Open_PMH"].mean()
open_pmh_green= filtered.loc[filtered["is_green"], "%Open_PMH"].mean()

spinta_red    = filtered.loc[filtered["is_red"], "%OH"].mean()
spinta_green  = filtered.loc[filtered["is_green"], "%OH"].mean()

low_red       = filtered.loc[filtered["is_red"], "%OL"].mean()
low_green     = filtered.loc[filtered["is_green"], "%OL"].mean()

# Medie break PM (già in percentuale, senza moltiplicare per 100)
pmbreak_red   = filtered.loc[filtered["is_red"], "break"].mean()
pmbreak_green = filtered.loc[filtered["is_green"], "break"].mean()


# ---- ORARIO HIGH: MEDIA, MEDIANA, FILTRI RED/GREEN ----

def orario_to_minuti(ora_str):
    """Converte '9:31' -> minuti totali (es. 571)"""
    try:
        h, m = map(int, ora_str.split(":"))
        return h * 60 + m
    except:
        return np.nan

def minuti_to_orario(minuti):
    """Converte minuti -> stringa 'HH:MM'"""
    if np.isnan(minuti):
        return "-"
    h = int(minuti // 60)
    m = int(round(minuti % 60))
    return f"{h:02d}:{m:02d}"

# Filtra solo valori validi
orari_validi = df["Orario High"].dropna().apply(orario_to_minuti).dropna()

# Media e mediana globali
media_minuti = orari_validi.mean() if not orari_validi.empty else np.nan
mediana_minuti = orari_validi.median() if not orari_validi.empty else np.nan

media_orario_high = minuti_to_orario(media_minuti)
mediana_orario_high = minuti_to_orario(mediana_minuti)

# --- Filtri per chiusure RED / GREEN ---
red = df[df["Chiusura"] == "RED"]["Orario High"].dropna().apply(orario_to_minuti)
green = df[df["Chiusura"] == "GREEN"]["Orario High"].dropna().apply(orario_to_minuti)

mediaorario_red = minuti_to_orario(red.mean()) if not red.empty else "-"
mediaorario_green = minuti_to_orario(green.mean()) if not green.empty else "-"

# endregion


# -------------------------------
# region KPI CARD 
# crea il layout per le card kpi
# -------------------------------

def kpi_card_textual(title, total, red, green, suffix, show_delta=True):
    # delta solo se numerico e show_delta=True
    try:
        delta = float(red) - float(green) if show_delta else 0
        delta_sign = "+" if delta > 0 else ""
        # usa solo le classi CSS già presenti
        delta_cls = "green" if delta < 0 else "red"
    except (ValueError, TypeError):
        delta_html = '<div class="kpi-delta">&nbsp;</div>'
        delta = None
        delta_cls = "red"

    # formattazione valori
    def fmt(x):
        try:
            return f"{x:.0f}"
        except (ValueError, TypeError):
            return str(x)

    delta_html = f'<div class="kpi-delta {delta_cls}">Δ {delta_sign}{fmt(delta)}{suffix}</div>' if show_delta and delta is not None else '<div class="kpi-delta">&nbsp;</div>'

    html = f"""
    <div class="kpi-card">
        <div class="kpi-header">
            <div class="kpi-title">{title}</div>
            <div class="kpi-total">{fmt(total)}{suffix}</div>
        </div>
        <div class="kpi-split">
            <div class="red">Red: {fmt(red)}{suffix}</div>
            <div class="green">Green: {fmt(green)}{suffix}</div>
        </div>
        {delta_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def kpi_box_statual(kpi, invert_negative=False, show_bar=True):
    """KPI box layout verticale con Media/Mediana e confronto Red vs Green"""

    def fmt(x):
        try:
            return f"{x:.0f}"
        except (ValueError, TypeError):
            return str(x)

    title = kpi["title"]
    total = kpi["total"]
    red = kpi["red"]
    green = kpi["green"]
    suffix = kpi.get("suffix", "")

    total_med = kpi.get("total_med", total)
    red_med = kpi.get("red_med", red)
    green_med = kpi.get("green_med", green)

    # =========================
    # Calcolo barra
    # =========================
    red_pct = 50
    green_pct = 50

    if show_bar:
        if red_med == green_med:
            red_pct = 50
            green_pct = 50
        else:
            delta = red_med - green_med
            if invert_negative:
                delta = -delta

            total_abs = abs(red_med) + abs(green_med)
            if total_abs != 0:
                red_pct = max(min(50 + (delta / total_abs) * 50, 100), 0)
                green_pct = 100 - red_pct
            else:
                red_pct = 50
                green_pct = 50


    # =========================
    # COSTRUZIONE BARRA HTML
    # =========================

    if show_bar:
        bar_html = (
            f'<div style="width:100%; height:8px; background:#eee; border-radius:4px; display:flex; overflow:hidden;">'
            f'<div style="width:{red_pct}%; background:#E74C3C;"></div>'
            f'<div style="width:{green_pct}%; background:#2ECC71;"></div>'
            f'</div>'
        )
    else:
        bar_html = '<div style="height:8px;"></div>'

    # ===========
    #    HTML
    # ===========

    html = f"""
    <div class="kpi-card">
        <div style="text-align:center; font-weight:600; margin-bottom:10px;">
            {title}
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="text-align:left;">
                <div style="font-size:20px; font-weight:600; font-variant-numeric: tabular-nums;">
                    {fmt(total)}{suffix}
                </div>
                <div style="font-size:13px; opacity:0.7; font-variant-numeric: tabular-nums;">
                    {fmt(total_med)}{suffix}
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:16px; font-weight:600; color:#E74C3C;">
                    {fmt(red)}{suffix}
                    <span style="font-size:12px; opacity:0.7; font-variant-numeric: tabular-nums;">
                        / {fmt(red_med)}{suffix}
                    </span>
                </div>
                <div style="font-size:16px; font-weight:600; color:#2ECC71;">
                    {fmt(green)}{suffix}
                    <span style="font-size:12px; opacity:0.7; font-variant-numeric: tabular-nums;">
                        / {fmt(green_med)}{suffix}
                    </span>
                </div>
            </div>
        </div>
        <div style="width:100%; margin-top:10px;">
            {bar_html}
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)



# endregion


# -------------------------------------------------
# region TABELLA GIORNALIERA MULTI-GAP
# -------------------------------------------------

daily_mg = (
    filtered
    .assign(is_red = filtered["Chiusura"] == "RED")
    .groupby("Date")
    .agg(
        num_gapper = ("Ticker", "count"),
        num_red    = ("is_red", "sum"),
        pct_red    = ("is_red", "mean")
    )
    .reset_index()
)

daily_mg["pct_red"] *= 100


# -------------------------------------------------
# KPI GIORNALIERI 
# -------------------------------------------------

avg_pct_red_day = daily_mg["pct_red"].mean() if not daily_mg.empty else 0
median_pct_red_day = daily_mg["pct_red"].median() if not daily_mg.empty else 0

pct_days_red_50 = (
    (daily_mg["pct_red"] >= 50).mean() * 100
    if not daily_mg.empty else 0
)

pct_days_red_75 = (
    (daily_mg["pct_red"] >= 75).mean() * 100
    if not daily_mg.empty else 0
)

# calcolo Close %

filtered["day_close_pct"] = (
    (filtered["Close"] - filtered["OPEN"]) / filtered["OPEN"] * 100
)

# Suddivisione dataset
total_df = filtered.copy()
green_df = filtered[filtered["Chiusura"] == "GREEN"]
red_df   = filtered[filtered["Chiusura"] == "RED"]

def structure_stats(df):
    if df.empty:
        return None
    
    return {
        "High_mean": df["%OH"].mean(),
        "High_median": df["%OH"].median(),
        "Low_mean": df["%OL"].mean(),
        "Low_median": df["%OL"].median(),
        "Close_mean": df["day_close_pct"].mean(),
        "Open_vs_PMH": df["%Open_PMH"].mean()
    }

stats_total = structure_stats(total_df)
stats_green = structure_stats(green_df)
stats_red   = structure_stats(red_df)



# endregion


# -----------------------------------------------
# region TOP BOX
# ----------------------------------------------------------------

box_left = f"""
<div class='kpi-top-box'>
  <div class='kpi-top'>
    <div class='top-kpi'>
      <div class='top-kpi-value'>{total}</div>
      <div class='top-kpi-label'>Totale record</div>
    </div>
    <div class='top-kpi'>
      <div class='top-kpi-value'>{red_close:.0f}%</div>
      <div class='top-kpi-label'>Chiusure RED</div>
    </div>
    <div class='top-kpi'>
      <div class='top-kpi-value'>{gap_median:.0f}%</div>
      <div class='top-kpi-label'>GAP mediana</div>
    </div>
  </div>
</div>
"""

box_right = f"""
<div class='kpi-top-box'>
  <div class='kpi-top'>
    <div class='top-kpi'>
      <div class='top-kpi-value'>{num_days_mg}</div>
      <div class='top-kpi-label'>Numero giornate</div>
    </div>
    <div class='top-kpi'>
      <div class='top-kpi-value'>{avg_gapper_per_day:.1f}</div>
      <div class='top-kpi-label'>Numero gapper per day</div>
    </div>
    <div class='top-kpi'>
      <div class='top-kpi-value'>{avg_pct_red_day:.0f}%</div>
      <div class='top-kpi-label'>Chiusure RED per day</div>
    </div>
  </div>
</div>
"""


st.subheader("📊 KPI principali")

col1, col2 = st.columns(2)

with col1:
    st.markdown(box_left, unsafe_allow_html=True)

with col2:
    st.markdown(box_right, unsafe_allow_html=True)


# endregion


# -------------------------------------
# region KPI LISTA
# ------------------------------------

# 1️⃣ Lista KPI
kpi_list = [
    {"title": "GAP Medio", "total": gap_mean, "red": gap_red, "green": gap_green, "suffix": "%"},
    {"title": "Open / PMH medio", "total": filtered['%Open_PMH'].mean(), "red": open_pmh_red, "green": open_pmh_green, "suffix": "%"},
    {"title": "Break medio", "total": filtered['break'].mean()*100, "red": pmbreak_red, "green": pmbreak_green, "suffix": "%"},
    {"title": "Spinta media", "total": filtered['%OH'].mean(), "red": spinta_red, "green": spinta_green, "suffix": "%"},
    {"title": "Minimo medio", "total": filtered['%OL'].mean(), "red": low_red, "green": low_green, "suffix": "%"},
    #{"title": "Orario High medio", "total": media_orario_high, "red": mediaorario_red, "green": mediaorario_green, "suffix": "", "show_delta": False}
]

# 2️⃣ Creo 2 colonne
col1, col2, col3 = st.columns(3)
columns = [col1, col2, col3]  # mettiamo le colonne in una lista per ciclarle facilmente

# 3️⃣ Ciclo e metto le card nelle colonne
for i, kpi in enumerate(kpi_list):
    col = columns[i % 3]  # ora alterna tra col1, col2, col3
    with col:
        kpi_card_textual(
            title=kpi["title"],
            total=kpi["total"],
            red=kpi["red"],
            green=kpi["green"],
            suffix=kpi.get("suffix"),
            show_delta=kpi.get("show_delta", True)  # <- importante
        )


# ----------

col1, col2, col3 = st.columns(3)
columns = [col1, col2, col3]

for i, kpi in enumerate(kpi_list):
    col = columns[i % 3]
    with col:
        kpi_box_statual(kpi)



# endregion


#---------------------------------
# region GRAFICO CONFRONTO
# -------------------------------

import plotly.graph_objects as go

st.subheader("📊 Struttura Giornaliera – Totale vs Green vs Red")

metrics = [
    "High_mean",
    "High_median",
    "Low_mean",
    "Low_median",
    "Close_mean",
    "Open_vs_PMH"
]

labels = [
    "High Medio",
    "High Mediana",
    "Low Medio",
    "Low Mediana",
    "%Close Medio",
    "%Open vs PMH"
]

fig = go.Figure()

fig.add_bar(
    name="Totale",
    x=labels,
    y=[stats_total[m] for m in metrics],
)

fig.add_bar(
    name="Green",
    x=labels,
    y=[stats_green[m] for m in metrics],
)

fig.add_bar(
    name="Red",
    x=labels,
    y=[stats_red[m] for m in metrics],
)

fig.update_layout(
    barmode="group",
    height=400,
    xaxis_title="Metriche",
    yaxis_title="Percentuale (%)",
    margin=dict(l=20, r=20, t=20, b=20),
)

st.plotly_chart(fig, use_container_width=True)

# endregion


# --------------------------------------------
# region GRAFICO INTRADAY
# --------------------------------------------

# Converzione campi testo in numeri

# Timeframe highs
for tf in [15, 30, 60]:
    col = f"High_{tf}m"
    if col in filtered.columns:
        filtered[col] = pd.to_numeric(
            filtered[col]
            .astype(str)
            .str.replace(",", ".")
            .str.strip(),
            errors="coerce"
        )

# PM High
if "PM_high" in filtered.columns:
    filtered["PM_high"] = pd.to_numeric(
        filtered["PM_high"]
        .astype(str)
        .str.replace(",", ".")
        .str.strip(),
        errors="coerce"
    )

# Creazione calcoli per grafici intraday

for tf in [15, 30, 60]:
    # %H/L rispetto all'open
    filtered[f"oh_{tf}m"] = (filtered[f"High_{tf}m"] - filtered["OPEN"]) / filtered["OPEN"] * 100
    filtered[f"ol_{tf}m"] = (filtered[f"Low_{tf}m"] - filtered["OPEN"]) / filtered["OPEN"] * 100

    # Break PMH
    filtered[f"break_pmh_{tf}m"] = (filtered[f"High_{tf}m"] >= filtered["PM_high"]).astype(int)

# Medie per i grafici intraday
oh_red = filtered.loc[filtered["Chiusura"] == "RED", ["oh_15m","oh_30m","oh_60m"]].mean()
oh_green = filtered.loc[filtered["Chiusura"] == "GREEN", ["oh_15m","oh_30m","oh_60m"]].mean()

ol_red = filtered.loc[filtered["Chiusura"] == "RED", ["ol_15m","ol_30m","ol_60m"]].mean()
ol_green = filtered.loc[filtered["Chiusura"] == "GREEN", ["ol_15m","ol_30m","ol_60m"]].mean()



import plotly.graph_objects as go

def ci_box_single(df):
    if df.empty:
        st.write("Nessun dato disponibile")
        return

    timeframes = ["15", "30", "60"]
    labels = [f"H{tf}" for tf in timeframes] + [f"L{tf}" for tf in timeframes]

    # Calcolo medie
    total_means = [df[f"oh_{tf}m"].mean() for tf in timeframes] + [df[f"ol_{tf}m"].mean() for tf in timeframes]
    red_means   = [df[df["Chiusura"]=="RED"][f"oh_{tf}m"].mean() for tf in timeframes] + [df[df["Chiusura"]=="RED"][f"ol_{tf}m"].mean() for tf in timeframes]
    green_means = [df[df["Chiusura"]=="GREEN"][f"oh_{tf}m"].mean() for tf in timeframes] + [df[df["Chiusura"]=="GREEN"][f"ol_{tf}m"].mean() for tf in timeframes]

    # Grafico
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=total_means,
        y=labels,
        name="Totale",
        orientation='h',
        marker_color="#3498DB",  # azzurrino
        text=[f"{v:.1f}%" for v in total_means],
        textposition="outside"
    ))

    fig.add_trace(go.Bar(
        x=red_means,
        y=labels,
        name="RED",
        orientation='h',
        marker_color="#E74C3C",
        text=[f"{v:.1f}%" for v in red_means],
        textposition="outside"
    ))

    fig.add_trace(go.Bar(
        x=green_means,
        y=labels,
        name="GREEN",
        orientation='h',
        marker_color="#2ECC71",
        text=[f"{v:.1f}%" for v in green_means],
        textposition="outside"
    ))

    fig.update_layout(
        barmode='group',  # le barre affiancate
        margin=dict(l=20, r=20, t=20, b=20),
        height=400,
        xaxis_title="Media (%)",
        yaxis=dict(autorange="reversed")
    )

    st.plotly_chart(fig, use_container_width=True)


ci_box_single(filtered)



# endregion


# -------------------------------------------------
# region DISTRIBUZIONE % RED GIORNALIERA
# -------------------------------------------------

bins = [0, 25, 50, 75, 100]
labels = ["0–25%", "25–50%", "50–75%", "75–100%"]

daily_mg["red_bucket"] = pd.cut(
    daily_mg["pct_red"],
    bins=bins,
    labels=labels,
    include_lowest=True
)

bucket_dist = (
    daily_mg["red_bucket"]
    .value_counts()
    .sort_index()
)

import plotly.express as px

st.subheader("📊 Distribuzione e andamento giornaliero")

# Creo le colonne
col1, col2 = st.columns(2)

with col1:
    fig_bucket = px.bar(
        x=bucket_dist.index,
        y=bucket_dist.values,
        labels={
            "x": "% RED nella giornata",
            "y": "Numero giornate"
        },
        title="Distribuzione giornaliera delle chiusure RED (Multi-Gap Days)"
    )
    st.plotly_chart(fig_bucket, use_container_width=True)

with col2:
    daily_mg["color"] = np.where(
        daily_mg["pct_red"] >= 75, "#8B0000",
        np.where(daily_mg["pct_red"] >= 50, "#E74C3C", "#2ECC71")
    )

    daily_mg["Date_str"] = daily_mg["Date"].astype(str)

    fig_time = px.bar(
        daily_mg,
        x="Date_str",
        y="pct_red",
        title="% RED per giornata (Multi-Gap)",
        labels={"pct_red": "% RED", "Date_str": "Data"}
    )

    fig_time.update_traces(
        marker_color=daily_mg["color"],
        width=0.95
    )

    fig_time.update_layout(
        bargap=0.05
    )

    fig_time.update_xaxes(type="category")

    st.plotly_chart(fig_time, use_container_width=True)

# endregion


# -------------------------------------------------
# region TABELLA
# -------------------------------------------------

st.markdown('<h3 style="font-size:16px; color:#FFFFFF;">📋 Tabella di dettaglio</h3>', unsafe_allow_html=True)

display_columns = [
    "Date",
    "Ticker",
    "Float",
    "Market Cap",
    "Shares Outstanding",
    "Volume",
    "Volume PM",
    "Chiusura",
    "%Open_PMH",
    "%OH",
    "%OL",
    "Orario High",
    "break"
]

filtered_sorted = filtered.sort_values("Date", ascending=False).reset_index(drop=True)

filtered_sorted = filtered_sorted[
    [c for c in display_columns if c in filtered_sorted.columns]
]


column_rename = {
    "%Open_PMH": "O_PMH %",
    "%OH": "O_High %",
    "%OL": "O_Low %",
    "Shares Outstanding": "Shares Out.",
}

filtered_sorted = filtered_sorted.rename(columns=column_rename)



if "Chiusura" in filtered_sorted.columns:
    filtered_sorted["Chiusura"] = filtered_sorted["Chiusura"].replace({
        "RED": "🔴 RED",
        "GREEN": "🟢 GREEN"
    })

if "break" in filtered_sorted.columns:
    filtered_sorted["break"] = pd.to_numeric(
        filtered_sorted["break"], errors="coerce"
    ).apply(lambda x: "✅" if x == 1 else "")

def to_millions(x):
    try:
        x = str(x).replace(".", "").replace(",", ".")
        x = float(x)
        return f"{x/1_000_000:.1f} M"
    except:
        return "-"

if "Shares Out." in filtered_sorted.columns:
    filtered_sorted["Shares Out."] = filtered_sorted["Shares Out."].apply(to_millions)

if "Market Cap" in filtered_sorted.columns:
    filtered_sorted["Market Cap"] = filtered_sorted["Market Cap"].apply(to_millions)

if "Float" in filtered_sorted.columns:
    filtered_sorted["Float"] = filtered_sorted["Float"].apply(to_millions)

if "Volume" in filtered_sorted.columns:
    filtered_sorted["Volume"] = filtered_sorted["Volume"].apply(to_millions)

if "Volume PM" in filtered_sorted.columns:
    filtered_sorted["Volume PM"] = filtered_sorted["Volume PM"].apply(to_millions)


# --- RIMOZIONE SIMBOLO % NELLA TABELLA PER LE COLONNE PERCENTUALI ---
percent_cols_display = [
    "O_PMH %", "O_High %", "O_Low %",
    "%OH_30m", "%OL_30m",
    "%OH_1h", "%OL_1h"]

for col in percent_cols_display:
    if col in filtered_sorted.columns:
        filtered_sorted[col] = (
            pd.to_numeric(
                filtered_sorted[col]
                    .astype(str)
                    .str.replace("%", "")
                    .str.replace(",", ".")
                    .str.strip(),
                errors="coerce"
            )
            .round(0)
            .astype("Int64")
        )


display_df = filtered_sorted.copy()

for col in display_df.columns:
    display_df[col] = display_df[col].astype(str)

st.dataframe(display_df, use_container_width=True)


#st.dataframe(filtered_sorted, use_container_width=True)
st.caption(f"Sto mostrando {len(filtered_sorted)} record filtrati su {len(df)} totali.")



# endregion