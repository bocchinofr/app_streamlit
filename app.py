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
st.markdown("### 🛠️ Controllo dati")

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


# ---- KPI BOX STILIZZATI ----
st.markdown(
    """
    <style>
    .kpi-box {
        background-color: #184F5F;
        color: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
        margin-bottom: 10px;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: bold;
    }
    .kpi-label {
        font-size: 16px;
        opacity: 0.9;
    }
    </style>
    """,
    unsafe_allow_html=True
)

def kpi_box(label, value, subvalue=None):
    html = f"""
    <div class="kpi-box">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
    """
    if subvalue:
        html += f"<div style='font-size:13px;opacity:0.8;'>{subvalue}</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    kpi_box("Totale titoli", total)
with col2:
    kpi_box("Chiusura RED", f"{red_close:.0f}%")
with col3:
    kpi_box("GAP medio", f"{gap_mean:.0f}%", f"mediana {gap_median:.0f}%")
with col4:
    kpi_box("%Open_PMH medio", f"{open_pmh_mean:.1f}%")
with col5:
    kpi_box("PMbreak medio", f"{pmbreak:.1f}")

# ---- TAB E TABELLA ----
st.markdown("### 📋 Tabella di dettaglio")

# Rimuovo eventuali colonne inutili
cols_to_drop = [c for c in filtered.columns if "high_v1" in c.lower()]
if cols_to_drop:
    filtered = filtered.drop(columns=cols_to_drop)

# Applico colorazione condizionale alla colonna Chiusura
def color_chiusura(val):
    if val == "RED":
        return 'background-color: #FF6B6B; color: white; font-weight: bold;'
    elif val == "GREEN":
        return 'background-color: #4CAF50; color: white; font-weight: bold;'
    return ''

if "Chiusura" in filtered.columns:
    styled_df = filtered.style.applymap(color_chiusura, subset=["Chiusura"])
else:
    styled_df = filtered

# Mostro la tabella senza indice extra
st.dataframe(styled_df.sort_values("Date", ascending=False).reset_index(drop=True), use_container_width=True)
st.caption(f"Mostrando {len(filtered)} record filtrati su {len(df)} totali.")



# ---- TAB E TABELLA ----
st.markdown("### 📋 Tabella di dettaglio")

# Rimuovo qualsiasi colonna che contiene "high_v1" nel nome
cols_to_drop = [c for c in filtered.columns if "high_v1" in c.lower()]
if cols_to_drop:
    filtered = filtered.drop(columns=cols_to_drop)

# Mostro la tabella senza indice extra
st.dataframe(filtered.sort_values("Date", ascending=False).reset_index(drop=True), use_container_width=True)
st.caption(f"Mostrando {len(filtered)} record filtrati su {len(df)} totali.")
