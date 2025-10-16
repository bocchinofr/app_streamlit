import streamlit as st
import pandas as pd
import numpy as np
from dateutil import parser

# ---- CONFIGURAZIONE ----
st.set_page_config(page_title="Dashboard Analisi", layout="wide")
st.title("📈 Dashboard Analisi Small Cap")

# ---- CARICAMENTO DATI ----
SHEET_URL = "https://docs.google.com/spreadsheets/d/15ev2l8av7iil_-HsXMZihKxV-B5MgTVO-LnK1y_f2-o/export?format=csv"
df = pd.read_csv(SHEET_URL)

# ---- PULIZIA DATI ----
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
num_cols = ["OPEN", "Float", "break"]
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



# ---- CONTROLLO DATI ----

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



# ---- FILTRI ----
st.sidebar.header("🔍 Filtri")

tickers = st.sidebar.multiselect("Ticker", sorted(df["Ticker"].dropna().unique()))
min_gap = st.sidebar.number_input("GAP minimo (%)", 0, 1000, 0)
max_float = st.sidebar.number_input("Float massimo", 0, 1_000_000_000, 5_000_000)
min_open_pmh = st.sidebar.number_input("%Open_PMH minimo", -100, 100, -100)
min_open = st.sidebar.number_input("OPEN minimo", 0.0, 1000.0, 0.0)
date_range = st.sidebar.date_input("Intervallo date", [])

filtered = df.copy()
if tickers:
    filtered = filtered[filtered["Ticker"].isin(tickers)]
filtered = filtered[(filtered["GAP"] >= min_gap) & (filtered["Float"] <= max_float)]
filtered = filtered[(filtered["%Open_PMH"] >= min_open_pmh) & (filtered["OPEN"] >= min_open)]
if len(date_range) == 2:
    start, end = date_range
    filtered = filtered[(filtered["Date"] >= start) & (filtered["Date"] <= end)]


# ---- KPI BOX ----
total = len(filtered)
red_close = np.mean(filtered["Chiusura"].eq("RED")) * 100 if total > 0 else 0
gap_mean = filtered["GAP"].mean() if total > 0 else 0
gap_median = filtered["GAP"].median() if total > 0 else 0
open_pmh_mean = filtered["%Open_PMH"].mean() if total > 0 else 0
spinta = (filtered["%OH"].mean() - filtered["%OL"].mean()) if total > 0 else 0
pmbreak = filtered["break"].mean() *100 if total > 0 else 0

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
    filtered.loc[filtered["Chiusura"] == "RED", "break"].mean()
    if not filtered.loc[filtered["Chiusura"] == "RED"].empty
    else 0
)
pmbreak_green = (
    filtered.loc[filtered["Chiusura"] == "GREEN", "break"].mean()
    if not filtered.loc[filtered["Chiusura"] == "GREEN"].empty
    else 0
)


# ---- STILE GLOBALE ----
st.markdown(
    """
    <style>
    /* Sfondo generale pagina */
    .stApp {
        background-color: #03121A !important;
    }

    /* Contenitore scrollabile KPI */
    .kpi-container {
        display: flex;
        gap: 20px;
        overflow-x: auto;  /* scroll se pagina stretta */
        padding-bottom: 20px;
        margin-bottom: 40px;  /* spazio tra KPI e tabella */
    }

    /* Singolo box KPI */
    .kpi-box {
        flex: 0 0 auto;       /* larghezza fissa */
        min-width: 180px;
        min-height: 130px;
        background-color: #184F5F;
        color: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .kpi-label { font-size: 16px; opacity: 0.9; }
    .kpi-value { font-size: 28px; font-weight: bold; }
    .kpi-subvalue { font-size: 18px; font-weight: bold; opacity: 0.8; }

    .gap-subbox {
        display: flex;
        justify-content: center;
        align-items: flex-start;  /* centra verticalmente GAP e Mediana */
        gap: 20px;
        margin-top: 0;
    }

    .gap-subbox div {
        display: flex;
        flex-direction: column;
        justify-content: center;
        text-align: center;
    }

    /* Sub-box per chiusure red/green */
    .redgreen-subbox {
        display: flex;
        justify-content: center;
        gap: 25px;
        margin-top: 6px;
        border-top: 1px solid rgba(255,255,255,0.2);
        padding-top: 8px;
    }

    .redgreen-subbox div {
        text-align: center;
    }

    .redgreen-subbox .red {
        color: #FF4C4C;
    }

    .redgreen-subbox .green {
        color: #4CFF4C;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# ---- KPI BOX SCROLLABILI ----
html_kpis = f"""
<div class="kpi-container">
    <div class="kpi-box">
        <div class="kpi-label">Totale titoli</div>
        <div class="kpi-value">{total}</div>
    </div>
    <div class="kpi-box">
        <div class="kpi-label">Chiusura RED</div>
        <div class="kpi-value">{red_close:.0f}%</div>
    </div>
    <div class="kpi-box">
        <div class="gap-subbox">
            <div>
                <div class="kpi-label">GAP medio</div>
                <div class="kpi-value">{gap_mean:.0f}%</div>
            </div>
            <div>
                <div class="kpi-label">Mediana</div>
                <div class="kpi-subvalue">{gap_median:.0f}%</div>
            </div>
        </div>
    </div>
    <div class="kpi-box">
        <div class="kpi-label">%Open_PMH medio</div>
        <div class="kpi-value">{open_pmh_mean:.0f}%</div>
        <div class="redgreen-subbox">
            <div>
                <div style="font-size:10px;" class="red">chiusure red</div>
                <div style="font-size:20px; font-weight:bold;" class="red">{open_pmh_red:.0f}%</div>
            </div>
            <div>
                <div style="font-size:10px;" class="green">chiusure green</div>
                <div style="font-size:20px; font-weight:bold;" class="green">{open_pmh_green:.0f}%</div>
            </div>
        </div>
    </div>
    <div class="kpi-box">
        <div class="kpi-label">PMbreak medio</div>
        <div class="kpi-value">{pmbreak:.0f}%</div>
    </div>
</div>
"""
st.markdown(html_kpis, unsafe_allow_html=True)




# ---- TAB E TABELLA ----
st.markdown('<h3 style="font-size:16px; color:#FFFFFF;">📋 Tabella di dettaglio</h3>', unsafe_allow_html=True)

cols_to_drop = [c for c in filtered.columns if "high_v1" in c.lower()]
if cols_to_drop:
    filtered = filtered.drop(columns=cols_to_drop)

filtered_sorted = filtered.sort_values("Date", ascending=False).reset_index(drop=True)

if "Chiusura" in filtered_sorted.columns:
    filtered_sorted["Chiusura"] = filtered_sorted["Chiusura"].replace({
        "RED": "🔴 RED",
        "GREEN": "🟢 GREEN"
    })

st.dataframe(filtered_sorted, use_container_width=True)
st.caption(f"Sto mostrando {len(filtered_sorted)} record filtrati su {len(df)} totali.")
