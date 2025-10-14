import streamlit as st
import pandas as pd
import numpy as np

# ---- CONFIGURAZIONE ----
st.set_page_config(page_title="Dashboard Analisi", layout="wide")
st.title("📈 Dashboard Analisi Small Cap")

# ---- CARICAMENTO DATI ----
SHEET_URL = "https://docs.google.com/spreadsheets/d/15ev2l8av7iil_-HsXMZihKxV-B5MgTVO-LnK1y_f2-o/export?format=csv"
df = pd.read_csv(SHEET_URL)
st.write("📊 Anteprima dati", df.head())


# ---- PULIZIA DATI ----
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["GAP"] = pd.to_numeric(df["GAP"], errors="coerce")
df["Float"] = pd.to_numeric(df["Float"], errors="coerce")
df["OPEN"] = pd.to_numeric(df["OPEN"], errors="coerce")
df["%Open_PMH"] = pd.to_numeric(df["%Open_PMH"], errors="coerce")
df["%OH"] = pd.to_numeric(df["%OH"], errors="coerce")
df["%OL"] = pd.to_numeric(df["%OL"], errors="coerce")
df["break"] = pd.to_numeric(df["break"], errors="coerce")

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
    filtered = filtered[(filtered["Date"] >= pd.to_datetime(start)) & (filtered["Date"] <= pd.to_datetime(end))]

# ---- KPI BOX ----
total = len(filtered)
red_close = np.mean(filtered["Chiusura"].str.upper() == "RED") * 100 if total > 0 else 0
gap_mean = filtered["GAP"].mean()
gap_median = filtered["GAP"].median()
open_pmh_mean = filtered["%Open_PMH"].mean()
spinta = filtered["%OH"].mean() - filtered["%OL"].mean()
pmbreak = filtered["break"].mean()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Totale titoli", total)
col2.metric("Chiusura RED", f"{red_close:.0f}%")
col3.metric("GAP medio", f"{gap_mean:.0f}%", delta=f"mediana {gap_median:.0f}%")
col4.metric("%Open_PMH medio", f"{open_pmh_mean:.0f}%")
col5.metric("PMbreak medio", f"{pmbreak:.0f}")

# ---- KPI secondari ----
col6, col7, col8 = st.columns(3)
col6.metric("Spinta", f"{spinta:.0f}%")
if "Orario High(timeH)" in filtered.columns:
    def parse_hour(x):
        try:
            h, m = str(x).split(":")
            return int(h) + int(m)/60
        except:
            return np.nan
    filtered["z_ora_num"] = filtered["Orario High(timeH)"].apply(parse_hour)
    col7.metric("z_ora_num medio", f"{filtered['z_ora_num'].mean():.1f}")
    col8.metric("z_ora_num mediana", f"{filtered['z_ora_num'].median():.1f}")

# ---- TAB E TABELLA ----
st.markdown("### 📋 Tabella di dettaglio")
st.dataframe(filtered.sort_values("Date", ascending=False), use_container_width=True)

st.caption(f"Mostrando {len(filtered)} record filtrati su {len(df)} totali.")
