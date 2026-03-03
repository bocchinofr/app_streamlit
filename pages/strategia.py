import streamlit as st
import pandas as pd
from dateutil import parser
import numpy as np
import matplotlib.pyplot as plt
from ui_kpi import kpi_box_statual
from ui_kpi import build_kpi, kpi_box_statual


# ---- CONFIGURAZIONE ----
st.set_page_config(page_title="Strategia Intraday", layout="wide")

# Carica il CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("theme.css")

# Titolo
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("<h1 style='margin-bottom:0px;'>Strategia Intraday</h1>", unsafe_allow_html=True)
    st.text("La strategia prevede un solo ingresso SHORT in base ai parametri definiti in sidebar. \nSolo una volta raggiunto il livello di entry sarà attivata l'operazione e saranno verificati TP e SL \n ⚠️ Attenzione ⚠️ in RED son segnati i trade finiti in SL")


with col2:
    mode = st.radio(
        "Modalità",
        ["Fino a chiusura", "90 minuti"],
        index=1,
        horizontal=True,
        label_visibility="visible"
    )

    # Valore di default
    param_entry_tf = 60  # puoi cambiare tramite box Streamlit

    # Esempio con Streamlit selectbox
    param_entry_tf = st.selectbox(
        "Seleziona timeframe per Entry",
        options=[15, 30, 45, 60],
        index=3  # default a 60 minuti
    )


# ---- CARICAMENTO DATI CON CACHE ----
SHEET_URL = "https://docs.google.com/spreadsheets/d/15ev2l8av7iil_-HsXMZihKxV-B5MgTVO-LnK1y_f2-o/export?format=xlsx"

@st.cache_data
def load_data():
    # Carica tutte le colonne automaticamente
    df = pd.read_excel(SHEET_URL, sheet_name="scarico_intraday")
    # Parse date
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d-%m-%Y")
    return df


df = load_data()


#================================
# region FILTRI LATERALI 
#================================

#st.sidebar.header("🔍 Filtri e parametri")
date_range = st.sidebar.date_input("Intervallo date", [])
tickers = sorted(df["Ticker"].dropna().unique())
selected_tickers = st.sidebar.multiselect(
    "Ticker",
    options=tickers,
    default=[],
    help="Seleziona uno o più ticker da analizzare (lascia vuoto per tutti)"
)

# ====== MARKET CAP: DUE BOX (IN MILIONI) ======
# Valori fissi di default in Milioni
default_mc_min_M = 0
default_mc_max_M = 2000

col_mc_min, col_mc_max = st.sidebar.columns(2)

marketcap_min_M = col_mc_min.number_input(
    "MC Min ($M)", 
    value=default_mc_min_M, 
    step=10,
    min_value=0,
    max_value=2000,
    help="Valore minimo di Market Cap in Milioni"
)

marketcap_max_M = col_mc_max.number_input(
    "MC Max ($M)", 
    value=default_mc_max_M, 
    step=10,
    min_value=0,
    max_value=2000,
    help="Valore massimo di Market Cap in Milioni"
)

# Converti in valori reali per il filtro
marketcap_min = marketcap_min_M * 1_000_000
marketcap_max = marketcap_max_M * 1_000_000

# ====== ALTRI FILTRI ======


col_min_open, col_max_open = st.sidebar.columns(2)

min_open = col_min_open.number_input(
    "Open min ($)",
    value=2.0,
    min_value=0.0,
    max_value=500.0,
    help="prezzo minimo di Open"
)

max_open = col_max_open.number_input(
    "Open max ($)",
    value=500.0,
    min_value=0.0,
    max_value=500.0,
    help="prezzo minimo di Open"
)

min_gap = st.sidebar.number_input(
    "Gap% minimo",
    value=50.0,
    min_value=0.0,
    max_value=500.0,
    step=5.0
)

# ====== SHARES FLOAT (IN MILIONI) ======

default_float_min_M = 0
default_float_max_M = 200  # 200M come default

col_float_min, col_float_max = st.sidebar.columns(2)

float_min_M = col_float_min.number_input(
    "Float Min (M)",
    value=default_float_min_M,
    step=50,
    min_value=0,
    max_value=1000,
    help="Valore minimo di Shares Float in Milioni"
)

float_max_M = col_float_max.number_input(
    "Float Max (M)",
    value=default_float_max_M,
    step=50,
    min_value=0,
    max_value=1000,
    help="Valore massimo di Shares Float in Milioni"
)

min_float = float_min_M * 1_000_000
max_float = float_max_M * 1_000_000

with st.sidebar.expander("parametri strategia"):

    param_sl = st.number_input("%SL", value=30.0)
    param_tp = st.number_input("%TP", value=-15.0)
    param_entry = st.number_input("%entry", value=15.0)



filtered = df.copy()

# Converti Gap% e Open in numerico
filtered["Gap%"] = pd.to_numeric(filtered["Gap%"], errors="coerce")
filtered["Open"] = pd.to_numeric(filtered["Open"], errors="coerce")
filtered["Market Cap"] = pd.to_numeric(filtered["Market Cap"], errors="coerce")

# Converti sempre Date in datetime
filtered["Date_dt"] = pd.to_datetime(filtered["Date"], format="%d-%m-%Y", errors="coerce")

# --- Filtro date solo se l’utente ha selezionato un intervallo ---
if len(date_range) == 2:
    start, end = date_range
    filtered = filtered[(filtered["Date_dt"] >= pd.to_datetime(start)) &
                        (filtered["Date_dt"] <= pd.to_datetime(end))]
    
    if filtered.empty:
        st.warning(
            f"⚠️ Nessun dato disponibile per l'intervallo selezionato ({start.strftime('%d-%m-%Y')} - {end.strftime('%d-%m-%Y')})."
        )

# --- Filtro Open minimo e Gap% minimo ---
filtered = filtered[
    (filtered["Open"] >= min_open) &
    (filtered["Open"] <= max_open)
]
filtered = filtered[filtered["Gap%"] >= min_gap]

# Assicura che la colonna sia numerica
filtered["Shs Float"] = pd.to_numeric(filtered["Shs Float"], errors="coerce")
filtered["Shares Outstanding"] = pd.to_numeric(filtered["Shares Outstanding"], errors="coerce")

# Sostituisci i valori null di Shs Float con Shares Outstanding
filtered["Shs Float"].fillna(filtered["Shares Outstanding"], inplace=True)

# Adesso puoi filtrare senza errori
filtered = filtered[
    (filtered["Shs Float"] >= min_float) &
    (filtered["Shs Float"] <= max_float)
]

filtered = filtered[
    (filtered["Market Cap"] >= marketcap_min) &
    (filtered["Market Cap"] <= marketcap_max)
]


# --- Filtro Ticker (se selezionato) ---
if selected_tickers:
    filtered = filtered[filtered["Ticker"].isin(selected_tickers)]
# ---- Dopo filtraggio ----
if filtered.empty:
    st.warning("⚠️ Nessun dato disponibile dopo l'applicazione dei filtri.")
    st.stop()

# ---- Dopo filtraggio ----
if not filtered.empty:
    min_date = filtered["Date_dt"].min()
    max_date = filtered["Date_dt"].max()
    if pd.notna(min_date) and pd.notna(max_date):
        # Solo le date colorate e in grassetto
        st.markdown(
            f"""
            <div style='font-size:16px; font-weight:600; margin-bottom:10px;'>
                Dati filtrati dal <span style='font-size:22px; color:#1E90FF; font-weight:bold;'>{min_date.strftime('%d-%m-%Y')}</span> 
                al <span style='font-size:22px; color:#1E90FF; font-weight:bold;'>{max_date.strftime('%d-%m-%Y')}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.info("⚠️ Nessun dato disponibile dopo i filtri.")

if selected_tickers:
    tickers_str = ", ".join(selected_tickers)
    st.markdown(
        f"""
        <div style='font-size:16px; font-weight:600; margin-bottom:10px;'>
            Ticker selezionati: <span style='font-size:22px; color:#FFD700; font-weight:bold;'>{tickers_str}</span>
        </div>
        """,
        unsafe_allow_html=True
    )



# endregion


# Ordina il dataframe filtrato per Date discendente
#filtered = filtered.sort_values(by="Date_dt", ascending=False)


# ================================================
# region CALCOLI ENTRY / SL / TP / ATTIVAZIONE 
# ================================================

filtered["SL_price"] = filtered["Open"] * (1 + param_sl/100)
filtered["TP_price"] = filtered["Open"] * (1 + param_tp/100)
filtered["Entry_price"] = filtered["Open"] * (1 + param_entry/100)

filtered["attivazione"] = (filtered[f"High_{param_entry_tf}m"] >= filtered["Entry_price"]).astype(int)

# ---- ENTRY BUCKET (minimo timeframe in cui l'entry viene raggiunta) ----
def get_entry_bucket(row):
    if row.get("High_1m", -np.inf) >= row["Entry_price"]:
        return 1
    elif row.get("High_5m", -np.inf) >= row["Entry_price"]:
        return 5
    elif row.get("High_15m", -np.inf) >= row["Entry_price"]:  # NUOVO
        return 15
    elif row.get("High_30m", -np.inf) >= row["Entry_price"]:
        return 30
    elif row.get("High_45m", -np.inf) >= row["Entry_price"]:  # NUOVO
        return 45
    elif row.get("High_60m", -np.inf) >= row["Entry_price"]:
        return 60
    elif row.get("High_90m", -np.inf) >= row["Entry_price"]:
        return 90
    elif row.get("High_120m", -np.inf) >= row["Entry_price"]:
        return 120
    elif row.get("High_240m", -np.inf) >= row["Entry_price"]:
        return 240
    else:
        return None


filtered["entry_bucket"] = filtered.apply(get_entry_bucket, axis=1)

filtered["TP_90m%"] = np.nan
filtered["TP"] = 0
filtered["SL"] = 0
filtered["Outcome"] = None

if mode == "90 minuti":
    timeframes_90m = [
        (1, "High_1m", "Low_1m"),
        (5, "High_5m", "Low_5m"),
        (15, "High_15m", "Low_15m"),
        (30, "High_30m", "Low_30m"),
        (45, "High_45m", "Low_45m"),
        (60, "High_60m", "Low_60m"),
        (90, "High_90m", "Low_90m")
    ]

    for idx, row in filtered.iterrows():
        if row["attivazione"] != 1 or row["entry_bucket"] is None:
            continue

        entry = row["Entry_price"]
        sl_price = row["SL_price"]
        tp_price = row["TP_price"]

        for tf, high_col, low_col in timeframes_90m:

            # ⛔ ignora bucket <= entry (no ordine temporale affidabile)
            if tf <= row["entry_bucket"]:
                continue

            high = row.get(high_col, np.nan)
            low = row.get(low_col, np.nan)

            # ❗ CASO PEGGIORATIVO: SL PRIORITARIO
            if pd.notna(high) and high >= sl_price:
                filtered.at[idx, "SL"] = 1
                filtered.at[idx, "Outcome"] = "SL"
                break

            if pd.notna(low) and low <= tp_price:
                filtered.at[idx, "TP"] = 1
                filtered.at[idx, "Outcome"] = "TP"
                break


        # calcolo performance % in base a chi ha colpito
        if filtered.at[idx, "TP"] == 1:
            exit_price = tp_price
        elif filtered.at[idx, "SL"] == 1:
            exit_price = sl_price
        else:
            exit_price = row["Close_90m"]

        filtered.at[idx, "TP_90m%"] = (exit_price - entry) / entry * 100

else:
    # modalità fino a chiusura: aggiungiamo anche 30 minuti al primo timeframe
    timeframes = [
        (1, "High_1m", "Low_1m"),
        (5, "High_5m", "Low_5m"),
        (15, "High_15m", "Low_15m"),
        (30, "High_30m", "Low_30m"),
        (45, "High_45m", "Low_45m"),
        (60, "High_60m", "Low_60m"),
        (90, "High_90m", "Low_90m"),
        (120, "High_120m", "Low_120m"),
        (240, "High_240m", "Low_240m"),
        ("close", "High", "Low")
    ]

    for idx, row in filtered.iterrows():
        if row["attivazione"] != 1 or row["entry_bucket"] is None:
            continue

        entry = row["Entry_price"]
        sl_price = row["SL_price"]
        tp_price = row["TP_price"]

        for tf, high_col, low_col in timeframes:

            if tf != "close" and tf <= row["entry_bucket"]:
                continue

            high = row.get(high_col, np.nan)
            low = row.get(low_col, np.nan)

            # ❗ CASO PEGGIORATIVO
            if pd.notna(high) and high >= sl_price:
                filtered.at[idx, "SL"] = 1
                filtered.at[idx, "Outcome"] = "SL"
                break

            if pd.notna(low) and low <= tp_price:
                filtered.at[idx, "TP"] = 1
                filtered.at[idx, "Outcome"] = "TP"
                break


        # calcolo performance % in base a chi ha colpito
        if filtered.at[idx, "TP"] == 1:
            exit_price = tp_price
        elif filtered.at[idx, "SL"] == 1:
            exit_price = sl_price
        else:
            exit_price = row["Close"]

        filtered.at[idx, "TP_90m%"] = (exit_price - entry) / entry * 100



# Coerenza finale
filtered.loc[filtered["SL"] == 1, "TP"] = 0

# ========================================
# CALCOLO PNL PER TRADE (CENTRALIZZATO)
# ========================================

def calculate_trade_pnl(df, initial_capital=10000, risk_pct=1):

    df = df.copy()
    df["PnL_$"] = 0.0
    df["R_multiple"] = 0.0

    for idx, row in df.iterrows():

        if row["attivazione"] != 1:
            continue

        risk_amount = initial_capital * (risk_pct / 100)
        stop_dist = abs(row["SL_price"] - row["Entry_price"])

        if stop_dist == 0:
            continue

        size = risk_amount / stop_dist

        if row["TP"] == 1:
            pnl = (row["Entry_price"] - row["TP_price"]) * size
        elif row["SL"] == 1:
            pnl = (row["Entry_price"] - row["SL_price"]) * size
        else:
            val = row["TP_90m%"]
            pnl = 0
            if pd.notna(val):
                pnl = (-val / 100) * row["Entry_price"] * size

        df.at[idx, "PnL_$"] = pnl
        df.at[idx, "R_multiple"] = pnl / risk_amount if risk_amount != 0 else 0

    return df

st.markdown("### ⚙️ Parametri Simulazione")

col1, col2 = st.columns(2)

initial_capital = col1.number_input(
    "💰 Capitale iniziale",
    value=3000.0,
    step=100.0
)

risk_pct = col2.number_input(
    "📉 % Rischio per trade",
    value=2.0,
    step=0.5
)

# CALCOLO PNL
filtered = calculate_trade_pnl(
    filtered,
    initial_capital=initial_capital,
    risk_pct=risk_pct
)

# Calcolo TP_90m
mask_green = (
    (filtered["attivazione"] == 1) & 
    (filtered["SL"] == 0) & 
    (filtered["TP"] == 0) & 
    (filtered["TP_90m%"] < 0)
)
mask_red = (
    (filtered["attivazione"] == 1) & 
    (filtered["SL"] == 0) & 
    (filtered["TP"] == 0) & 
    (filtered["TP_90m%"] >= 0)
)
tp_90m_green_avg = round(filtered.loc[mask_green, "TP_90m%"].mean(), 0)
tp_90m_red_avg   = round(filtered.loc[mask_red, "TP_90m%"].mean(), 0)
# Se è NaN → "-"
tp_90m_green_avg = "-" if np.isnan(tp_90m_green_avg) else int(tp_90m_green_avg)
tp_90m_red_avg   = "-" if np.isnan(tp_90m_red_avg) else int(tp_90m_red_avg)


# endregion

# =====================================
# region KPI BOX
# =====================================

total = len(filtered)
attivazioni = filtered["attivazione"].sum()
numero_SL = filtered["SL"].sum()
numero_TP = filtered["TP"].sum()
close_90m_red = ((filtered["attivazione"] == 1) & 
             (filtered["SL"] == 0) & 
             (filtered["TP"] == 0) & 
             (filtered["TP_90m%"] >= 0)
            ).sum()
close_90m_green = ((filtered["attivazione"] == 1) & 
             (filtered["SL"] == 0) & 
             (filtered["TP"] == 0) & 
             (filtered["TP_90m%"] < 0)
            ).sum()

# Solo trade attivati
trades = filtered[filtered["attivazione"] == 1]

wins = trades[trades["PnL_$"] > 0]["PnL_$"]
losses = trades[trades["PnL_$"] < 0]["PnL_$"]

avg_win = wins.mean() if len(wins) > 0 else 0
avg_loss = abs(losses.mean()) if len(losses) > 0 else 0

winrate = len(wins) / len(trades) if len(trades) > 0 else 0
lossrate = 1 - winrate

RR_real = avg_win / avg_loss if avg_loss > 0 else 0
expectancy = (winrate * avg_win) - (lossrate * avg_loss)

profit = trades["PnL_$"].sum()
trade_count = len(trades)

# Equity cumulata
equity = trades["PnL_$"].cumsum()

# Massimo progressivo
running_max = equity.cummax()

# Drawdown assoluto
drawdown = equity - running_max

# Max drawdown assoluto ($)
max_drawdown = drawdown.min()

drawdown_pct = (equity - running_max) / running_max * 100
max_drawdown_pct = drawdown_pct.min()

st.markdown(
    """
    <style>
    /* Sfondo generale pagina */
    .stApp {
        background-color: #03121A !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Stile base dei box
base_box_style = """
    flex:1; 
    background-color:#184F5F; 
    color:white; 
    padding:5px; 
    border-radius:12px; 
    text-align:center;
"""

# Stile del titolo e del valore
title_style = "font-size:18px; opacity:0.8;"
value_style = "font-size:30px; font-weight:bold;"
profit_color = "#00FF00" if profit >= 0 else "#FF6347"

st.markdown(f"""
<!-- PRIMA RIGA: 4 BOX -->
<div style="display:flex; gap:15px; margin-bottom:20px;">
    <div style="{base_box_style}">
        <div style="{title_style}">Totale record</div>
        <div style="{value_style}">{total}</div>
    </div>
    <div style="{base_box_style}">
        <div style="{title_style}">Attivazioni</div>
        <div style="{value_style}">{attivazioni}</div>
    </div>
    <div style="{base_box_style}">
        <div style="{title_style}">Winrate</div>
        <div style="{value_style}">{winrate*100:.1f}%</div>
    </div>
    <div style="{base_box_style}">
        <div style="{title_style}">RR Real</div>
        <div style="{value_style}">{RR_real:.2f}</div>
    </div>
    <div style="{base_box_style}">
        <div style="{title_style}">Expectancy</div>
        <div style="{value_style}">{expectancy:.2f}$</div>
    </div>
    <div style="{base_box_style} color:#EE4419;">
        <div style="{title_style}">Max Drawdown</div>
        <div style="{value_style}">{max_drawdown:.0f}$</div>
    </div>
    <div style="{base_box_style}">
        <div style="{title_style}">Profit</div>
        <div style="{value_style}; color:{profit_color};">{profit:.2f}$</div>
    </div>
</div>
<!-- SECONDA RIGA: 3 BOX -->
<div style="display:flex; gap:15px; margin-bottom:20px;">
    <div style="{base_box_style}">
        <div style="{title_style}">Numero SL</div>
        <div style="{value_style}">{numero_SL}</div>
    </div>
    <div style="{base_box_style}">
        <div style="{title_style}">Numero TP</div>
        <div style="{value_style}">{numero_TP}</div>
    </div>
    <!-- Box con colore testo personalizzato -->
    <div style="{base_box_style} color:#EE4419;">
        <div style="{title_style}">Close trade RED</div>
        <div style="{value_style}">{close_90m_red}</div>
    </div>
    <!-- Box con colore testo personalizzato -->
    <div style="{base_box_style} color:#2EDB2E;">
        <div style="{title_style}">Close trade GREEN</div>
        <div style="{value_style}">{close_90m_green}</div>
    </div>
    <div style="{base_box_style};">
        <div style="{title_style}">media prezzo 90m</div>
        <div style="{value_style}">{tp_90m_green_avg}%</div>
    </div>
</div>
""", unsafe_allow_html=True)


# endregion


#====================================================
# region NUOVI KPI PER STOP O PROFIT
#====================================================

df_all = filtered.copy()


if "TimeHigh" in df_all.columns:
    df_all["TimeHigh"] = pd.to_datetime(df_all["TimeHigh"], errors="coerce")
    df_all["TimeHigh_sec"] = df_all["TimeHigh"].apply(
        lambda x: x.hour*3600 + x.minute*60 if pd.notnull(x) else None
    )

if all(col in df_all.columns for col in ["Open", "HighPM"]):
    df_all["Open_vs_PMH_%"] = ((df_all["Open"] - df_all["HighPM"]) / df_all["HighPM"]) * 100

# funzione conversione orari
def seconds_to_hhmm(seconds):
    if pd.isna(seconds):
        return "-"
    seconds = int(seconds)
    return f"{seconds//3600:02d}:{(seconds%3600)//60:02d}"

df_all["Vol5_vs_PM_%"] = (df_all["Volume_5m"] / df_all["VolumePM"].replace(0, np.nan)) * 100
df_all["Vol30_vs_PM_%"] = (df_all["Volume_30m"] / df_all["VolumePM"].replace(0, np.nan)) * 100
df_all["Vol60_vs_PM_%"] = (df_all["Volume_60m"] / df_all["VolumePM"].replace(0, np.nan)) * 100
df_all["Vol5_vs_Total_%"] = (df_all["Volume_5m"] / df_all["Volume"].replace(0, np.nan)) * 100
df_all["Vol30_vs_Total_%"] = (df_all["Volume_30m"] / df_all["Volume"].replace(0, np.nan)) * 100

df_red = df_all[df_all["PnL_$"] < 0].copy()
df_green = df_all[df_all["PnL_$"] > 0].copy()


gap_mean_total = df_all["Gap%"].mean()
gap_median = df_all["Gap%"].median()
gap_red = df_red["Gap%"].mean()
gap_red_med = df_red["Gap%"].median()
gap_green = df_green["Gap%"].mean()
gap_green_med = df_green["Gap%"].median()

mc_mean = df_all["Market Cap"].mean()/1000000
mc_median = df_all["Market Cap"].median()/1000000
mc_red = df_red["Market Cap"].mean()/1000000
mc_red_med = df_red["Market Cap"].median()/1000000
mc_green = df_green["Market Cap"].mean()/1000000
mc_green_med = df_green["Market Cap"].median()/1000000

shs_mean = df_all["Shs Float"].mean()/1000
shs_median = df_all["Shs Float"].median()/1000
shs_red = df_red["Shs Float"].mean()/1000
shs_red_med = df_red["Shs Float"].median()/1000
shs_green = df_green["Shs Float"].mean()/1000
shs_green_med = df_green["Shs Float"].median()/1000

shout_mean = df_all["Shares Outstanding"].mean()/1000
shout_median = df_all["Shares Outstanding"].median()/1000
shout_red = df_red["Shares Outstanding"].mean()/1000
shout_red_med = df_red["Shares Outstanding"].median()/1000
shout_green = df_green["Shares Outstanding"].mean()/1000
shout_green_med = df_green["Shares Outstanding"].median()/1000

vol_mean = df_all["Volume"].mean()/1000000
vol_median = df_all["Volume"].median()/1000000
vol_red = df_red["Volume"].mean()/1000000
vol_red_med = df_red["Volume"].median()/1000000
vol_green = df_green["Volume"].mean()/1000000
vol_green_med = df_green["Volume"].median()/1000000

volpm_mean = df_all["VolumePM"].mean()/1000000
volpm_median = df_all["VolumePM"].median()/1000000
volpm_red = df_red["VolumePM"].mean()/1000000
volpm_red_med = df_red["VolumePM"].median()/1000000
volpm_green = df_green["VolumePM"].mean()/1000000
volpm_green_med = df_green["VolumePM"].median()/1000000

df_all["high%"] = ((df_all["High"] - df_all["Open"]) / df_all["Open"]) * 100
df_red["high%"] = ((df_red["High"] - df_red["Open"]) / df_red["Open"]) * 100
df_green["high%"] = ((df_green["High"] - df_green["Open"]) / df_green["Open"]) * 100

high_red = df_red["high%"].mean()
high_red_med = df_red["high%"].median()
high_green = df_green["high%"].mean()
high_green_med = df_green["high%"].median()
high_mean = df_all["high%"].mean()
high_median = df_all["high%"].median()

time_mean_total = df_all["TimeHigh_sec"].mean()
time_median_total = df_all["TimeHigh_sec"].median()
time_red = df_red["TimeHigh_sec"].mean()
time_red_med = df_red["TimeHigh_sec"].median()
time_green = df_green["TimeHigh_sec"].mean()
time_green_med = df_green["TimeHigh_sec"].median()

ovp_mean = df_all["Open_vs_PMH_%"].mean()
ovp_median = df_all["Open_vs_PMH_%"].median()
ovp_red = df_red["Open_vs_PMH_%"].mean()
ovp_red_med = df_red["Open_vs_PMH_%"].median()
ovp_green = df_green["Open_vs_PMH_%"].mean()
ovp_green_med = df_green["Open_vs_PMH_%"].median()


kpi_list = [
    build_kpi("GAP Medio", total=gap_mean_total, red=gap_red, green=gap_green, total_med=gap_median, red_med=gap_red_med, green_med=gap_green_med),
    build_kpi("Market Cap", total=mc_mean, red=mc_red, green=mc_green, total_med=mc_median, red_med=mc_red_med, green_med=mc_green_med, suffix=" M"),
    build_kpi("Shs Float", total=shs_mean, red=shs_red, green=shs_green, total_med=shs_median, red_med=shs_red_med, green_med=shs_green_med, suffix=" K"),
    build_kpi("Volume", total=vol_mean, red=vol_red, green=vol_green, total_med=vol_median, red_med=vol_red_med, green_med=vol_green_med, suffix=" M"),
    build_kpi("High%", total=high_mean, red=high_red, green=high_green, total_med=high_median, red_med=high_red_med, green_med=high_green_med),
    build_kpi("Time High Medio", total=seconds_to_hhmm(time_mean_total), red=seconds_to_hhmm(time_red), green=seconds_to_hhmm(time_green), total_med=seconds_to_hhmm(time_median_total), red_med=seconds_to_hhmm(time_red_med), green_med=seconds_to_hhmm(time_green_med), suffix="", show_bar=False),
    build_kpi("Open vs PMH %", total=ovp_mean, red=ovp_red, green=ovp_green, total_med=ovp_median, red_med=ovp_red_med, green_med=ovp_green_med, suffix="%", show_bar=True),
    build_kpi("Volume PM", total=volpm_mean, red=volpm_red, green=volpm_green, total_med=volpm_median, red_med=volpm_red_med, green_med=volpm_green_med, suffix=" M", show_bar=True),
    build_kpi("Shs Out",total=shout_mean,red=shout_red,green=shout_green,total_med=shout_median,red_med=shout_red_med,green_med=shout_green_med,suffix=" k",show_bar=True)
]


# ----------

col1, col2, col3, col4 = st.columns(4)
columns = [col1, col2, col3, col4]

for i, kpi in enumerate(kpi_list):
    col = columns[i % 4]
    with col:
        kpi_box_statual(kpi)

st.markdown("---")
st.subheader("Volume Behaviour vs PreMarket")


import plotly.graph_objects as go

# --- Prepariamo i dati ---
timeframes = ["5m", "30m", "60m"]

total_vol = [df_all["Vol5_vs_PM_%"].mean(), df_all["Vol30_vs_PM_%"].mean(), df_all["Vol60_vs_PM_%"].mean()]
loss_vol  = [df_red["Vol5_vs_PM_%"].mean(), df_red["Vol30_vs_PM_%"].mean(), df_red["Vol60_vs_PM_%"].mean()]
profit_vol= [df_green["Vol5_vs_PM_%"].mean(), df_green["Vol30_vs_PM_%"].mean(), df_green["Vol60_vs_PM_%"].mean()]

# --- Layout a due colonne: KPI e Grafico ---
col_kpi, col_graph = st.columns([1,3])

# --- KPI piccoli nella colonna di sinistra ---
with col_kpi:
    for label, value in [("5m Loss", loss_vol[0]), ("5m Profit", profit_vol[0]),
                         ("30m Loss", loss_vol[1]), ("30m Profit", profit_vol[1]),
                         ("60m Loss", loss_vol[2]), ("60m Profit", profit_vol[2]),
                         ("Total Avg", total_vol[2])]:
        st.markdown(f'<div style="font-size:16px; font-weight:600; margin-bottom:4px;">{label}: {value:.0f}%</div>', unsafe_allow_html=True)

# --- Grafico nella colonna di destra ---
with col_graph:
    fig = go.Figure()
    # Linea Total/Media tratteggiata blu
    fig.add_trace(go.Scatter(x=timeframes, y=total_vol, mode='lines+markers', name='Total', line=dict(color='blue', width=2)))
    # Linea Loss rossa
    fig.add_trace(go.Scatter(x=timeframes, y=loss_vol, mode='lines+markers', name='Loss', line=dict(color='red', width=2)))
    # Linea Profit verde
    fig.add_trace(go.Scatter(x=timeframes, y=profit_vol, mode='lines+markers', name='Profit', line=dict(color='green', width=2)))

    # Layout grafico
    fig.update_layout(
        height=350,
        yaxis_title="Volume vs PM (%)",
        xaxis_title="Timeframe",
        legend_title="Category",
        margin=dict(l=20, r=20, t=20, b=20)
    )
    
    # Linea di riferimento 100%
    fig.add_hline(y=100, line_dash="dot", line_color="gray")

    st.plotly_chart(fig, use_container_width=True)


# endregion


#==========================================================
# region FUNZIONE UNIFICATA PER LE SEZIONI A SCOMPARSA 
# =========================================================



def show_kpi_section(df, title, box_color):
    """
    Mostra una sezione di KPI in un expander Streamlit usando box uniformi con display:grid.
    
    df: DataFrame già filtrato (es. SL=1, TP=1)
    title: stringa per il titolo della sezione
    box_color: colore dei box (es. "#5E2B2B" per SL, verde per TP, giallo chiaro per BE)
    """
    with st.expander(f"{title} (clicca per espandere)"):
        st.markdown(f"Numero di righe filtrate:   **{len(df)}**")

        if df.empty:
            st.info(f"⚠️ Nessun record con {title} = 1 nel dataset filtrato.")
            return

        # --- Calcoli ---
        gap_mean = df["Gap%"].mean() if "Gap%" in df.columns else None
        gap_median = df["Gap%"].median() if "Gap%" in df.columns else None

        shs_float_mean = df["Shs Float"].mean() if "Shs Float" in df.columns else None
        shs_float_median = df["Shs Float"].median() if "Shs Float" in df.columns else None

        shs_out_mean = df["Shares Outstanding"].mean() if "Shares Outstanding" in df.columns else None
        shs_out_median = df["Shares Outstanding"].median() if "Shares Outstanding" in df.columns else None

        volume_mean = df["Volume"].mean() if "Volume" in df.columns else None
        volume_median = df["Volume"].median() if "Volume" in df.columns else None

        volumePM_mean = df["VolumePM"].mean() if "VolumePM" in df.columns else None
        volumePM_median = df["VolumePM"].median() if "VolumePM" in df.columns else None

        volume5_mean = df["Volume_5m"].mean() if "Volume_5m" in df.columns else None
        volume5_median = df["Volume_5m"].median() if "Volume_5m" in df.columns else None

        volume30_mean = df["Volume_30m"].mean() if "Volume_30m" in df.columns else None
        volume30_median = df["Volume_30m"].median() if "Volume_30m" in df.columns else None

        if "High" in df.columns:
            df["high%"] = ((df["High"] - df["Open"])/df["High"])*100
            high_mean = df["high%"].mean()
            high_median = df["high%"].median()
        else:
            high_mean = None
            high_median = None

        # TimeHigh medio
        if "TimeHigh" in df.columns:
            df["TimeHigh"] = pd.to_datetime(df["TimeHigh"], errors="coerce")
            time_seconds = df["TimeHigh"].dropna().apply(lambda x: x.hour*3600 + x.minute*60)
            if not time_seconds.empty:
                time_avg = time_seconds.mean()
                time_mean_formatted = f"{int(time_avg//3600):02d}:{int((time_avg%3600)//60):02d}"
            else:
                time_mean_formatted = "-"
        else:
            time_mean_formatted = "-"

        # Open vs HighPM
        if "HighPM" in df.columns:
            df["openVSpmh"] = ((df["Open"] - df["HighPM"])/df["HighPM"])*100
            openVSpmh_mean = df["openVSpmh"].mean()
            openVSpmh_median = df["openVSpmh"].median()
        else:
            openVSpmh_mean = None
            openVSpmh_median = None

        # --- Rapporti % tra volumi ---
        if all(col in df.columns for col in ["Volume_5m", "VolumePM"]):
            df["Vol5_vs_PM_%"] = (df["Volume_5m"] / df["VolumePM"].replace(0,np.nan)) * 100
            vol5_vs_PM_mean = df["Vol5_vs_PM_%"].mean()
            vol5_vs_PM_median = df["Vol5_vs_PM_%"].median()
        else:
            vol5_vs_PM_mean = vol5_vs_PM_median = None

        if all(col in df.columns for col in ["Volume_30m", "VolumePM"]):
            df["Vol30_vs_PM_%"] = (df["Volume_30m"] / df["VolumePM"]) * 100
            vol30_vs_PM_mean = df["Vol30_vs_PM_%"].mean()
            vol30_vs_PM_median = df["Vol30_vs_PM_%"].median()
        else:
            vol30_vs_PM_mean = vol30_vs_PM_median = None

        # --- Calcoli Market Cap ---
        if "Market Cap" in df.columns:
            mc_mean = df["Market Cap"].mean()
            mc_median = df["Market Cap"].median()
            mc_mean_str = f"{mc_mean/1_000_000:.0f}M"
            mc_median_str = f"{mc_median/1_000_000:.2f}M"
        else:
            mc_mean_str = mc_median_str = "-"

        # --- Formattazione valori ---
        gap_mean_str = f"{gap_mean:.0f}%" if gap_mean is not None else "-"
        gap_median_str = f"{gap_median:.0f}%" if gap_median is not None else "-"

        shs_float_mean_str = f"{shs_float_mean/1_000_000:.0f}M" if shs_float_mean is not None else "-"
        shs_float_median_str = f"{shs_float_median/1_000_000:.2f}M" if shs_float_median is not None else "-"

        shs_out_mean_str = f"{shs_out_mean/1_000_000:.0f}M" if shs_out_mean is not None else "-"
        shs_out_median_str = f"{shs_out_median/1_000_000:.2f}M" if shs_out_median is not None else "-"

        high_mean_str = f"{high_mean:.0f}%" if high_mean is not None else "-"
        high_median_str = f"{high_median:.0f}%" if high_median is not None else "-"

        openVSpmh_mean_str = f"{openVSpmh_mean:.0f}%" if openVSpmh_mean is not None else "-"
        openVSpmh_median_str = f"{openVSpmh_median:.0f}%" if openVSpmh_median is not None else "-"

        volume_mean_str = f"{volume_mean/1_000_000:.0f}M" if volume_mean is not None else "-"
        volume_median_str = f"{volume_median/1_000_000:.2f}M" if volume_median is not None else "-"

        volumePM_mean_str = f"{volumePM_mean/1_000_000:.0f}M" if volumePM_mean is not None else "-"
        volumePM_median_str = f"{volumePM_median/1_000_000:.2f}M" if volumePM_median is not None else "-"

        volume30_mean_str = f"{volume30_mean/1_000_000:.0f}M" if volume30_mean is not None else "-"
        volume30_median_str = f"{volume30_median/1_000_000:.2f}M" if volume30_median is not None else "-"

        vol5_vs_PM_mean_str = f"{vol5_vs_PM_mean:.0f}%" if vol5_vs_PM_mean is not None else "-"
        vol5_vs_PM_median_str = f"{vol5_vs_PM_median:.0f}%" if vol5_vs_PM_median is not None else "-"

        vol30_vs_PM_mean_str = f"{vol30_vs_PM_mean:.0f}%" if vol30_vs_PM_mean is not None else "-"
        vol30_vs_PM_median_str = f"{vol30_vs_PM_median:.0f}%" if vol30_vs_PM_median is not None else "-"

        # --- Lista dei box ---
        boxes = [
            {"label": "Shs Out medio", "value": shs_out_mean_str, "sub": f"Mediana: {shs_out_median_str}"},
            {"label": "Vol 30m medio", "value": volume30_mean_str, "sub": f"Mediana: {volume30_median_str}"},
            {"label": "Vol5m/PM", "value": vol5_vs_PM_mean_str, "sub": f"Mediana: {vol5_vs_PM_median_str}"},
            {"label": "Vol30m/PM", "value": vol30_vs_PM_mean_str, "sub": f"Mediana: {vol30_vs_PM_median_str}"}
        ]


        # --- Stile ---
        LABEL_STYLE = "font-size:14px; opacity:0.85;"
        VALUE_STYLE = "font-size:20px; font-weight:bold; margin-left: 8px"
        SUBVALUE_STYLE = "font-size:14px; font-weight:500; opacity:0.85; margin-top:0px;"

        BOX_STYLE = f"""
            background-color:{{}}; 
            padding:5px; 
            border-radius:12px; 
            text-align:center; 
            box-shadow: 0 2px 6px rgba(0,0,0,0.3); 
            display:flex; 
            flex-direction:column; 
            justify-content:center; 
            align-items:center;
            min-height:50px;
        """

        # --- Container grid responsive ---
        container_html_start = """
        <div style="
            display:grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            row-gap: 12px;
            margin-top: 10px;
            margin-bottom :10px;
        ">
        """
        container_html_end = "</div>"

        # --- Genera HTML dei box ---
        boxes_html = ""
        for box in boxes:
            sub_html = f'<div style="{SUBVALUE_STYLE}">{box["sub"]}</div>' if "sub" in box else ""
            boxes_html += f'<div style="{BOX_STYLE.format(box_color)}">' \
                        f'<div style="display:flex; justify-content:center; align-items:center;">' \
                        f'<div style="{LABEL_STYLE}">{box["label"]}</div>' \
                        f'<div style="{VALUE_STYLE}">{box["value"]}</div>' \
                        f'</div>' \
                        f'{sub_html}' \
                        f'</div>'

        st.markdown(container_html_start + boxes_html + container_html_end, unsafe_allow_html=True)


# ---- USO DELLA FUNZIONE ----
sl_df = filtered[filtered["SL"] == 1].copy()
show_kpi_section(sl_df, "🔴 Stop Loss", "#5E2B2B")

tp_df = filtered[filtered["TP"] == 1].copy()
show_kpi_section(tp_df, "🟢 Take Profit", "#035506")

# endregion

#===========================
# region TABELLA 
#===========================

# Colonne da mostrare in tabella
cols_to_show = ["Date", "Ticker", "Gap%", "High_60m", "Low_60m",
                "High_90m", "Low_90m", "Close_90m", "Entry_price", "SL_price", "TP_price",
                "TP_90m%", "attivazione", "SL", "TP"]


# Funzione per righe alternate
def style_rows(s):
    return ['background-color: #202326' if i % 2 == 0 else '' for i in range(len(s))]

# Funzione per colorare celle condizionalmente
def highlight_cells(val, col_name):
    if col_name == "attivazione" and val == 1:
        return "background-color: #473C06; font-weight:bold;"
    elif col_name == "SL" and val == 1:
        return "background-color: #8B2A06; color:white; font-weight:bold;"
    elif col_name == "TP" and val == 1:
        return "background-color: #024902; color:white; font-weight:bold;"

    else:
        return ""

# Definizione formato numeri
format_dict = {}
for col in cols_to_show:
    if col == "Gap%":
        format_dict[col] = "{:.0f}"
    elif col in ["attivazione", "SL", "TP"]:
        format_dict[col] = "{:.0f}"
    elif filtered[col].dtype in ['float64', 'int64']:
        format_dict[col] = "{:.2f}"

# Applica formattazione e colori
styled_df = (
    filtered[cols_to_show]
    .style.apply(style_rows, axis=0)
    .format(format_dict)
    .apply(lambda x: [highlight_cells(v, x.name) for v in x], axis=0)
)

st.markdown('<h3 style="font-size:16px; color:#FFFFFF;">📋 Tabella filtrata</h3>', unsafe_allow_html=True)
st.dataframe(styled_df, use_container_width=True)
st.caption(f"Mostrando {len(filtered)} record filtrati su {len(df)} totali.")

# endregion

# =======================================
# region EQUITY & DRAWDOWN SIMULATION 
# =======================================

st.markdown("### 📈 Simulazione Equity & Drawdown")


# ---- COSTRUZIONE DATAFRAME ----
df_equity = filtered.copy()

# Considera solo i trade attivati
df_equity = df_equity[df_equity["attivazione"] == 1].copy()

# Evitiamo errori su colonne mancanti
for col in ["TP", "SL", "TP_90m%", "Entry_price", "SL_price", "TP_price"]:
    if col not in df_equity.columns:
        st.warning(f"Manca la colonna '{col}' nel dataframe.")
        st.stop()

# endregion

# region EQUITY

capital = initial_capital
equity_values = []
drawdowns = []

for pnl in df_equity["PnL_$"]:
    capital += pnl
    equity_values.append(capital)
    peak = max(equity_values)
    drawdown = (capital - peak) / peak * 100
    drawdowns.append(drawdown)

# Calcolo Size (dimensione del trade)
df_equity["Size"] = df_equity.apply(
    lambda row: (initial_capital * (risk_pct/100)) / abs(row["SL_price"] - row["Entry_price"])
                if row["SL_price"] != row["Entry_price"] else 0,
    axis=1
)

# Assembla dataframe finale con Equity e Drawdown
df_equity["Equity"] = equity_values
df_equity["Drawdown_%"] = drawdowns


# ---- STILE BASE KPI ----
def kpi_box(title, value, color="#FFD700"):
    return f"""
    <div style="
        display:flex; 
        justify-content:center; 
        align-items:center; 
        gap:10px; 
        background-color:#184F5F; 
        color:white; 
        padding:15px; 
        border-radius:12px;
        margin-bottom:20px;
    ">
        <span style="font-weight:600;">{title}:</span>
        <span style="color:{color}; font-size:20px; font-weight:700;">{value}</span>
    </div>
    """




# ---- CALCOLO COLONNA ESITO ----
def get_result_icon(row):
    if row["TP"] == 1:
        return "🟢"
    elif row["SL"] == 1:
        return "🔴"
    else:
        return "🟠"

df_equity["Esito"] = df_equity.apply(get_result_icon, axis=1)

# ---- TABELLA RIASSUNTIVA ----
df_display = df_equity[["Date", "Ticker", "Esito", "Size", "TP_90m%", "PnL_$", "Equity", "Drawdown_%"]].copy()
df_display["PnL_$"] = df_display["PnL_$"].round(2)
df_display["Equity"] = df_display["Equity"].round(2)
df_display["Drawdown_%"] = df_display["Drawdown_%"].round(2)
df_display["Size"] = df_display["Size"].round(0)

st.dataframe(df_display, use_container_width=True)

# ---- GRAFICO EQUITY ----
fig1, ax1 = plt.subplots(figsize=(10, 2))  # più compatto
ax1.plot(
    range(len(df_display)),
    df_display["Equity"],
    linewidth=1,
    color="royalblue",
)

# Cambia il colore di fondo dell’intera figura
fig1.patch.set_facecolor('#D5D9DF')  # ad esempio un blu-scuro

# Cambia il colore di fondo dell’area degli assi (grafico)
ax1.set_facecolor('#D5D9DF')  # ancora più scuro

ax1.axhline(initial_capital, color="gray", linestyle="--", linewidth=1)  # linea capitale iniziale
ax1.set_title("Equity Line", fontsize=9)
ax1.set_xlabel("Trade", fontsize=8)
ax1.set_ylabel("Capitale ($)", fontsize=8)
ax1.tick_params(axis='both', which='major', labelsize=7)  # riduce la dimensione delle etichette assi
ax1.set_xticks(range(0, len(df_display), max(1, len(df_display)//10)))
plt.tight_layout()
st.pyplot(fig1)

# ---- GRAFICO DRAWDOWN ----
fig2, ax2 = plt.subplots(figsize=(10, 2))  # più compatto

# Grafico a barre invece che linea
ax2.bar(
    range(len(df_display)),
    df_display["Drawdown_%"],
    color="#DE9D9D",
    width=0.8,
)

# Cambia il colore di fondo dell’intera figura
fig2.patch.set_facecolor('#D5D9DF')

# Cambia il colore di fondo dell’area degli assi (grafico)
ax2.set_facecolor('#D5D9DF')

ax2.set_title("Drawdown (%)", fontsize=9)
ax2.set_xlabel("Trade", fontsize=8)
ax2.set_ylabel("Drawdown (%)", fontsize=8)
ax2.axhline(0, color="gray", linestyle="--", linewidth=0.8)
ax2.tick_params(axis='both', which='major', labelsize=7)
ax2.set_xticks(range(0, len(df_display), max(1, len(df_display)//10)))

plt.tight_layout()
st.pyplot(fig2)

# endregion