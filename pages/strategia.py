import streamlit as st
import pandas as pd
from dateutil import parser

# ---- CONFIGURAZIONE ----
st.set_page_config(page_title="Strategia Intraday", layout="wide")
st.title("📊 Strategia Intraday")

# ---- CARICAMENTO DATI CON CACHE ----
SHEET_URL = "https://docs.google.com/spreadsheets/d/15ev2l8av7iil_-HsXMZihKxV-B5MgTVO-LnK1y_f2-o/export?format=xlsx"

@st.cache_data
def load_data():
    usecols = [
        "Date", "Ticker", "Open", "Gap%",
        "Close_1030", "High_60m", "Low_60m", "High_90m", "Low_90m", "Close_1100"
    ]
    df = pd.read_excel(SHEET_URL, sheet_name="scarico_intraday", usecols=usecols)
    # Parse date
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d-%m-%Y")
    return df

df = load_data()

# ---- FILTRI LATERALI ----
st.sidebar.header("🔍 Filtri e parametri")
date_range = st.sidebar.date_input("Intervallo date", [])
min_open = st.sidebar.number_input("Open minimo", value=0.0)
min_gap = st.sidebar.number_input("Gap% minimo", value=0.0)
param_sl = st.sidebar.number_input("%SL", value=30.0)
param_tp = st.sidebar.number_input("%TP", value=-15.0)
param_entry = st.sidebar.number_input("%entry", value=15.0)

filtered = df.copy()
if len(date_range) == 2:
    start, end = date_range
    filtered = filtered[(filtered["Date"] >= start) & (filtered["Date"] <= end)]
filtered = filtered[(filtered["Open"] >= min_open) & (filtered["Gap%"] >= min_gap)]

# ---- CALCOLI ENTRY / SL / TP / ATTIVAZIONE ----
filtered["SL_price"] = filtered["Open"] * (1 + param_sl/100)
filtered["TP_price"] = filtered["Open"] * (1 + param_tp/100)
filtered["Entry_price"] = filtered["Open"] * (1 + param_entry/100)

filtered["attivazione"] = (filtered["High_60m"] >= filtered["Entry_price"]).astype(int)
filtered["SL"] = ((filtered["attivazione"] == 1) & (filtered["High_90m"] >= filtered["SL_price"])).astype(int)
filtered["TP"] = ((filtered["attivazione"] == 1) & (filtered["SL"] == 0) & (filtered["Low_90m"] <= filtered["TP_price"])).astype(int)

# ---- KPI BOX ----
total = len(filtered)
attivazioni = filtered["attivazione"].sum()
numero_SL = filtered["SL"].sum()
numero_TP = filtered["TP"].sum()

st.markdown(
    f"""
    <div style="display:flex; gap:20px; padding:15px; background-color:#184F5F; border-radius:15px; color:white;">
        <div style="text-align:center;">
            <div style="font-size:16px; opacity:0.9;">Totale record</div>
            <div style="font-size:28px; font-weight:bold;">{total}</div>
        </div>
        <div style="text-align:center;">
            <div style="font-size:16px; opacity:0.9;">Attivazioni</div>
            <div style="font-size:28px; font-weight:bold;">{attivazioni}</div>
        </div>
        <div style="text-align:center;">
            <div style="font-size:16px; opacity:0.9;">Numero SL</div>
            <div style="font-size:28px; font-weight:bold;">{numero_SL}</div>
        </div>
        <div style="text-align:center;">
            <div style="font-size:16px; opacity:0.9;">Numero TP</div>
            <div style="font-size:28px; font-weight:bold;">{numero_TP}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ---- TABELLA ----
cols_to_show = [
    "Date", "Ticker", "Gap%", "High_60m", "Low_60m", "Close_1030",
    "High_90m", "Low_90m", "Close_1100",
    "Entry_price", "SL_price", "TP_price", "attivazione", "SL", "TP"
]

st.markdown('<h3 style="font-size:16px; color:#FFFFFF;">📋 Tabella filtrata</h3>', unsafe_allow_html=True)
st.dataframe(filtered[cols_to_show], use_container_width=True)
st.caption(f"Mostrando {len(filtered)} record filtrati su {len(df)} totali.")
