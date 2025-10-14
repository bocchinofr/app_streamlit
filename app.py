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
st.write("📊 Anteprima dati", df.head())

# ---- PULIZIA DATI ----
# Funzione robusta per parse date con dayfirst
def parse_date(x):
    try:
        return parser.parse(str(x), dayfirst=True)
    except:
        return pd.NaT

# Converto in datetime e poi estraggo solo la data
df["Date"] = df["Date"].apply(parse_date)
df["Date"] = df["Date"].apply(lambda x: x.date() if pd.notna(x) else pd.NaT)

df["Chiusura"] = df["Chiusura"].str.upper()

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
    df[col] = df[col].apply(parse_percent)

# Pulizia colonne numeriche con virgola
num_cols = ["OPEN", "Float", "break"]
for col in num_cols:
    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors="coerce")

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
pmbreak = filtered["break"].mean() if total > 0 else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Totale titoli", total)
col2.metric("Chiusura RED", f"{red_close:.0f}%")
col3.metric("GAP medio", f"{gap_mean:.0f}%", delta=f"mediana {gap_median:.0f}%")
col4.metric("%Open_PMH medio", f"{open_pmh_mean:.1f}%")
col5.metric("PMbreak medio", f"{pmbreak:.1f}")

# ---- TAB E TABELLA ----
st.markdown("### 📋 Tabella di dettaglio")

# Rimuovo la colonna Orario High_v1 se presente
if "Orario High_v1" in filtered.columns:
    filtered = filtered.drop(columns=["Orario High_v1"])

# Mostro la tabella senza l'indice extra
st.dataframe(filtered.sort_values("Date", ascending=False).reset_index(drop=True), use_container_width=True)
st.caption(f"Mostrando {len(filtered)} record filtrati su {len(df)} totali.")
