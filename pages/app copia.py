import streamlit as st
import pandas as pd
import numpy as np
from dateutil import parser
import yfinance as yf

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="Dashboard Analisi Small Cap",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 Dashboard Analisi Small Cap")

# Carica il CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("theme.css")

# -------------------------------------------------
# INPUT TICKER
# -------------------------------------------------
ticker_input = st.text_input(
    "Inserisci un ticker (es. MARA, TSLA, AAPL)",
    placeholder="Lascia vuoto per usare solo i dati intraday"
).upper().strip()

# -------------------------------------------------
# LOAD DATA
# -------------------------------------------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/15ev2l8av7iil_-HsXMZihKxV-B5MgTVO-LnK1y_f2-o/export?format=csv"
df = pd.read_csv(SHEET_URL)
df.columns = df.columns.str.strip()

def parse_date(x):
    try:
        return parser.parse(str(x), dayfirst=True).date()
    except:
        return pd.NaT

df["Date"] = df["Date"].apply(parse_date)
df["Chiusura"] = df["Chiusura"].astype(str).str.upper().str.strip()

def parse_percent(x):
    try:
        return float(str(x).replace("%", "").replace(",", "."))
    except:
        return np.nan

for col in ["GAP", "%Open_PMH", "%OH", "%OL"]:
    if col in df.columns:
        df[col] = df[col].apply(parse_percent).fillna(0)

for col in ["OPEN", "Float", "break"]:
    if col in df.columns:
        df[col] = pd.to_numeric(
            df[col].astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False),
            errors="coerce"
        ).fillna(0)

# -------------------------------------------------
# SIDEBAR FILTRI
# -------------------------------------------------
st.sidebar.header("🔍 Filtri")

date_range = st.sidebar.date_input("Intervallo date", [])
min_gap = st.sidebar.number_input("GAP minimo (%)", 0, 1000, 0)

col_mc1, col_mc2 = st.sidebar.columns(2)
mc_min = col_mc1.number_input("MC Min ($M)", 0, 2000, 0, step=10)
mc_max = col_mc2.number_input("MC Max ($M)", 0, 2000, 2000, step=10)

col_f1, col_f2 = st.sidebar.columns(2)
float_min = col_f1.number_input("Float MIN", 0, 1_000_000_000, 0, step=100_000)
float_max = col_f2.number_input("Float MAX", 0, 1_000_000_000, 5_000_000, step=100_000)

min_open_pmh = st.sidebar.number_input("%Open_PMH minimo", -100, 100, -100)

col_o1, col_o2 = st.sidebar.columns(2)
open_min = col_o1.number_input("Open MIN", 0.0, 100.0, 1.0, step=0.1)
open_max = col_o2.number_input("Open MAX", 0.0, 100.0, 100.0, step=0.1)

# -------------------------------------------------
# APPLY FILTERS
# -------------------------------------------------
filtered = df.copy()

if ticker_input:
    filtered = filtered[filtered["Ticker"] == ticker_input]

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

# -------------------------------------------------
# KPI
# -------------------------------------------------
st.subheader("📊 KPI principali")

total = len(filtered)
gap_mean = filtered["GAP"].mean() if total else 0
gap_median = filtered["GAP"].median() if total else 0
red_close = (filtered["Chiusura"] == "RED").mean() * 100 if total else 0

# --- Medie per red e green per GAP (aggiunte) ---
gap_red = (
    filtered.loc[filtered["Chiusura"] == "RED", "GAP"].mean()
    if not filtered.loc[filtered["Chiusura"] == "RED"].empty
    else 0
)
gap_green = (
    filtered.loc[filtered["Chiusura"] == "GREEN", "GAP"].mean()
    if not filtered.loc[filtered["Chiusura"] == "GREEN"].empty
    else 0
)
# Medie per red e green per OPENvsPMH
open_pmh_red = (
    filtered.loc[filtered["Chiusura"] == "RED", "%Open_PMH"].mean()
    if not filtered.loc[filtered["Chiusura"] == "RED"].empty
    else 0
)
open_pmh_green = (
    filtered.loc[filtered["Chiusura"] == "GREEN", "%Open_PMH"].mean()
    if not filtered.loc[filtered["Chiusura"] == "GREEN"].empty
    else 0
)

# Medie per red e green per PMbreak
pmbreak_red = (
    filtered.loc[filtered["Chiusura"] == "RED", "break"].mean()*100
    if not filtered.loc[filtered["Chiusura"] == "RED"].empty
    else 0
)
pmbreak_green = (
    filtered.loc[filtered["Chiusura"] == "GREEN", "break"].mean()*100
    if not filtered.loc[filtered["Chiusura"] == "GREEN"].empty
    else 0
)

# Medie per red e green per Spinta
spinta_red = (
    filtered.loc[filtered["Chiusura"] == "RED", "%OH"].mean()
    if not filtered.loc[filtered["Chiusura"] == "RED"].empty
    else 0
)
spinta_green = (
    filtered.loc[filtered["Chiusura"] == "GREEN", "%OH"].mean()
    if not filtered.loc[filtered["Chiusura"] == "GREEN"].empty
    else 0
)

# Medie per red e green per minimo 

low_red = (
    filtered.loc[filtered["Chiusura"] == "RED", "%OL"].mean()
    if not filtered.loc[filtered["Chiusura"] == "RED"].empty
    else 0
)
low_green = (
    filtered.loc[filtered["Chiusura"] == "GREEN", "%OL"].mean()
    if not filtered.loc[filtered["Chiusura"] == "GREEN"].empty
    else 0
)

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

# --- Top box: I 3 KPI principali in un unico box giustificato ---
top_html = f"""
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
      <div class='top-kpi-value'>{gap_mean:.0f}%</div>
      <div class='top-kpi-label'>GAP medio</div>
    </div>
  </div>
</div>
"""
st.markdown(top_html, unsafe_allow_html=True)

# Lista dei KPI (label, value, optional color)
kpi_rows = [
    ("GAP - massimo", f"{filtered['GAP'].max():.0f}%", "green"),
    ("GAP - mediana", f"{gap_median:.0f}%", None),
    ("GAP medio", (f"{gap_red:.0f}%", f"{gap_green:.0f}%", f"{gap_mean:.0f}%"), "multi"),
    ("Open / PMH medio", (f"{filtered['%Open_PMH'].mean():.0f}%", f"{open_pmh_green:.0f}%", f"{open_pmh_red:.0f}%"), "multi"),
    ("Open / PMH mediana", f"{filtered['%Open_PMH'].median():.0f}%", None),
    ("Float medio", f"{filtered['Float'].mean():,.0f}", None),
    ("Market Cap medio ($M)", f"{filtered['Market Cap'].mean() / 1_000_000:.0f}", None),
    ("Spinta media",(f"{filtered['%OH'].mean():.0f}%", f"{spinta_green:.0f}%", f"{spinta_red:.0f}%"), "multi"),
    ("Minimo medio",(f"{filtered['%OL'].mean():.0f}%", f"{low_green:.0f}%", f"{low_red:.0f}%"), "multi"),
    ("Break medio", (f"{filtered['break'].mean() * 100:.0f}%",f"{pmbreak_green:.0f}%", f"{pmbreak_red:.0f}%"), "multi"),
    ("Orario High medio",(f"{media_orario_high:.0f}", f"{mediaorario_green:.0f}", f"{mediaorario_red:.0f}"), "multi"),
]


# Divido i KPI in due colonne/box
n = len(kpi_rows)
mid = (n + 1) // 2
left_rows = kpi_rows[:mid]
right_rows = kpi_rows[mid:]

# Funzione render che supporta anche valori multipli (tuple/list) e riusa le classi value-highlight-*
def render_rows_html(rows):
    html = ""
    for label, value, color in rows:
        if isinstance(value, (list, tuple)):
            # ordina: (red, green, totale)
            red_val, green_val, total_val = value
            # testi dei tooltip (personalizzali a piacere)
            red_title = "Valore sui record con chiusura RED"
            green_title = "Valore sui record con chiusura GREEN"
            total_title = "Valoer su tutti i record filtrati"
            value_html = (
                "<div class='kpi-multi'>"
                f"<span class='value-highlight-red' title='{red_title}'>{red_val}</span>"
                f"<span class='value-highlight-green' title='{green_title}'>{green_val}</span>"
                f"<span class='value-highlight' title='{total_title}'>{total_val}</span>"
                "</div>"
            )
        else:
            highlight_cls = "value-highlight-green" if color == "green" else ("value-highlight-red" if color == "red" else "")
            if highlight_cls:
                value_html = f"<span class='{highlight_cls}'>{value}</span>"
            else:
                value_html = f"{value}"
        html += f"<div class='kpi-row'><div class='kpi-label'>{label}</div><div class='kpi-value'>{value_html}</div></div>"
    return html

left_html = render_rows_html(left_rows)
right_html = render_rows_html(right_rows)

container_html = f"""
<div class='kpi-container'>
  <div class='kpi-box left'>
    {left_html}
  </div>
  <div class='kpi-box right'>
    {right_html}
  </div>
</div>
"""

st.markdown(container_html, unsafe_allow_html=True)

# -------------------------------------------------
# TABELLA
# -------------------------------------------------
st.subheader("📋 Tabella di dettaglio")

filtered_sorted = filtered.sort_values("Date", ascending=False)

st.dataframe(
    filtered_sorted,
    use_container_width=True
)

st.caption(f"Record mostrati: {len(filtered_sorted)} su {len(df)}")