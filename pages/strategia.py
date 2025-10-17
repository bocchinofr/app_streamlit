import streamlit as st
import pandas as pd
from dateutil import parser
import numpy as np

# ---- CONFIGURAZIONE ----
st.set_page_config(page_title="Strategia Intraday", layout="wide")
st.title("📊 Strategia Intraday")

# ---- CARICAMENTO DATI ----
SHEET_URL = "https://docs.google.com/spreadsheets/d/15ev2l8av7iil_-HsXMZihKxV-B5MgTVO-LnK1y_f2-o/export?format=xlsx"
df = pd.read_excel(SHEET_URL, sheet_name="scarico_intraday")

# ---- PULIZIA DATI ----
df.columns = df.columns.str.strip()

def parse_date(x):
    try:
        return parser.parse(str(x).strip(), dayfirst=True)
    except:
        return pd.NaT

df["Date"] = df["Date"].apply(parse_date)
df["Date"] = df["Date"].apply(lambda x: x.date() if pd.notna(x) else pd.NaT)

# Convertiamo colonne numeriche
percent_cols = ["Gap%", "%SL", "%TP", "%entry", "Open"]
for col in percent_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# ---- FILTRI ----
st.sidebar.header("🔍 Filtri e parametri")

# Date
date_range = st.sidebar.date_input("Intervallo date", [])
# Open minimo
min_open = st.sidebar.number_input("Open (maggiore di)", 0.0, 1000.0, 0.0)
# Gap%
min_gap = st.sidebar.number_input("Gap% (maggiore di)", 0.0, 1000.0, 0.0)
# Parametri input
sl = st.sidebar.number_input("%SL", -100.0, 100.0, 30.0)
tp = st.sidebar.number_input("%TP", -100.0, 100.0, -15.0)
entry = st.sidebar.number_input("%entry", -100.0, 100.0, 15.0)

filtered = df.copy()
if len(date_range) == 2:
    start, end = date_range
    filtered = filtered[(filtered["Date"] >= start) & (filtered["Date"] <= end)]

filtered = filtered[(filtered["Open"] >= min_open) & (filtered["Gap%"] >= min_gap)]

# ---- KPI ----
total = len(filtered)

st.markdown(
    f"""
    <div style='background-color:#184F5F; color:white; padding:20px; border-radius:15px; width:200px; text-align:center;'>
        <div style='font-size:16px; opacity:0.9;'>Totale record</div>
        <div style='font-size:28px; font-weight:bold;'>{total}</div>
    </div>
    """,
    unsafe_allow_html=True
)

# ---- TABELLA ----
st.markdown('<h3 style="font-size:16px; color:#FFFFFF;">📋 Tabella di dettaglio</h3>', unsafe_allow_html=True)

columns_to_show = [
    "Date", "Ticker", "Gap%", "Close_1030", "High_60m", "Low_60m",
    "High_90m", "Low_90m", "Close_1100"
]

filtered_sorted = filtered[columns_to_show].sort_values("Date", ascending=False).reset_index(drop=True)

st.dataframe(filtered_sorted, use_container_width=True)
st.caption(f"Mostrando {len(filtered_sorted)} record filtrati su {len(df)} totali.")
