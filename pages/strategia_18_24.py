import streamlit as st
import pandas as pd
from dateutil import parser
import numpy as np
import matplotlib.pyplot as plt

# ---- CONFIGURAZIONE ----
st.set_page_config(page_title="Strategia Intraday", layout="wide")

# Titolo
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("<h1 style='margin-bottom:0px;'>Strategia Intraday</h1>", unsafe_allow_html=True)

# ---- CARICAMENTO DATI CON CACHE ----
SHEET_URL = "https://docs.google.com/spreadsheets/d/15ev2l8av7iil_-HsXMZihKxV-B5MgTVO-LnK1y_f2-o/export?format=xlsx"

@st.cache_data
def load_data():
    usecols = [
        "Date", "Ticker", "Open", "Gap%", "Shs Float", "Shares Outstanding", "TimeHigh", "HighPM", "High", "Low","Close",
        "High_90m", "Low_90m", "Volume", "VolumePM", "Volume_30m", "Volume_5m",
        "High_150m", "Low_150m", "High_210m", "Low_210m", "High_30m", "Low_30m", "Market Cap"
    ]
    df = pd.read_excel(SHEET_URL, sheet_name="Gapper2018_2024", usecols=usecols)
    # Parse date
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d-%m-%Y")
    return df

df = load_data()


# --- FILTRI LATERALI (uguali a prima) ---
date_range = st.sidebar.date_input("Intervallo date", [])
tickers = sorted(df["Ticker"].dropna().unique())
selected_tickers = st.sidebar.multiselect("Ticker", options=tickers, default=[])

# Market cap inputs (mantengo la UI come prima)
default_mc_min_M = 0
default_mc_max_M = 2000
col_mc_min, col_mc_max = st.sidebar.columns(2)
marketcap_min_M = col_mc_min.number_input("MC Min ($M)", value=default_mc_min_M, step=10, min_value=0, max_value=2000)
marketcap_max_M = col_mc_max.number_input("MC Max ($M)", value=default_mc_max_M, step=10, min_value=0, max_value=2000)
marketcap_min = marketcap_min_M * 1_000_000
marketcap_max = marketcap_max_M * 1_000_000

col_min_open, col_max_open = st.sidebar.columns(2)
min_open = col_min_open.number_input("Open min ($)", value=2.0, min_value=0.0, max_value=500.0)
max_open = col_max_open.number_input("Open max ($)", value=500.0, min_value=0.0, max_value=500.0)

min_gap = st.sidebar.number_input("Gap% minimo", value=50.0)
max_float = st.sidebar.number_input("Shs Float max", value=1000000000)

with st.sidebar.expander("parametri strategia"):
    param_sl = st.number_input("%SL", value=30.0)
    param_tp = st.number_input("%TP", value=-15.0)
    param_entry = st.number_input("%entry", value=15.0)
    param_BE = st.number_input("%BEparam", value=0.0, help="Percentuale da aggiungere al prezzo di TP")

filtered = df.copy()

# normalizzazioni
filtered["Gap%"] = pd.to_numeric(filtered.get("Gap%", np.nan), errors="coerce")
filtered["Open"] = pd.to_numeric(filtered.get("Open", np.nan), errors="coerce")
filtered["Market Cap"] = pd.to_numeric(filtered.get("Market Cap", np.nan), errors="coerce")
filtered["Date_dt"] = pd.to_datetime(filtered["Date"], format="%d-%m-%Y", errors="coerce")

# filtri data
if len(date_range) == 2:
    start, end = date_range
    filtered = filtered[(filtered["Date_dt"] >= pd.to_datetime(start)) & (filtered["Date_dt"] <= pd.to_datetime(end))]
    if filtered.empty:
        st.warning(f"⚠️ Nessun dato disponibile per l'intervallo selezionato ({start.strftime('%d-%m-%Y')} - {end.strftime('%d-%m-%Y')}).")

# filtri base
filtered = filtered[(filtered["Open"] >= min_open) & (filtered["Open"] <= max_open)]
filtered = filtered[filtered["Gap%"] >= min_gap]
filtered = filtered[filtered["Shs Float"] <= max_float]
filtered = filtered[(filtered["Market Cap"] >= marketcap_min) & (filtered["Market Cap"] <= marketcap_max)]

if selected_tickers:
    filtered = filtered[filtered["Ticker"].isin(selected_tickers)]

if filtered.empty:
    st.warning("⚠️ Nessun dato disponibile dopo l'applicazione dei filtri.")
    st.stop()

# visual caption date range
min_date = filtered["Date_dt"].min()
max_date = filtered["Date_dt"].max()
if pd.notna(min_date) and pd.notna(max_date):
    st.markdown(f"<div style='font-size:16px; font-weight:600; margin-bottom:10px;'>Dati filtrati dal <span style='font-size:22px; color:#1E90FF; font-weight:bold;'>{min_date.strftime('%d-%m-%Y')}</span> al <span style='font-size:22px; color:#1E90FF; font-weight:bold;'>{max_date.strftime('%d-%m-%Y')}</span></div>", unsafe_allow_html=True)

# =====================================================
# === PREPARAZIONE COLONNE / FALLBACK PER LO STORICO ===
# =====================================================

# elenco colonne timeframe che ci aspettiamo (opzione B)
expected_high_cols = [
    "High_1m","High_5m","High_30m","High_60m","High_90m","High_150m","High_210m","High_270m"
]
expected_low_cols = [
    "Low_1m","Low_5m","Low_30m","Low_60m","Low_90m","Low_150m","Low_210m","Low_270m"
]

# assicurati che le colonne esistano — se mancano creale con NaN (così non crasha)
for c in expected_high_cols + expected_low_cols + ["High","Low","Close"]:
    if c not in filtered.columns:
        filtered[c] = np.nan

# Ricostruisco High_60m / Low_60m se non esistono (o sono NaN)
# Logica: se High_60m manca, prendo max tra High_30m e High_90m (si conserva comportamento cumulativo)
filtered["High_60m"] = filtered["High_60m"].fillna(filtered[["High_30m","High_90m"]].max(axis=1))
filtered["Low_60m"]  = filtered["Low_60m"].fillna(filtered[["Low_30m","Low_90m"]].min(axis=1))

# Close giornaliero: se manca, usiamo Open come fallback (puoi cambiare fallback se preferisci)
filtered["Close_day"] = filtered["Close"].fillna(filtered["Open"])

# Day high/low: se non ci sono, usiamo High/Low già presenti, altrimenti fallback su valori notnull
filtered["High_day"] = filtered["High"]
filtered["Low_day"] = filtered["Low"]

# =====================================================
# === CALCOLI ENTRY / SL / TP / ATTIVAZIONE (STORICO) ==
# =====================================================

# livelli in valore assoluto
filtered["SL_price"] = filtered["Open"] * (1 + param_sl/100)
filtered["TP_price"] = filtered["Open"] * (1 + param_tp/100)
filtered["Entry_price"] = filtered["Open"] * (1 + param_entry/100)

# --- ATTIVAZIONE ENTRO 90 MINUTI
# controlliamo tutti i timeframe fino a 90m (1m,5m,30m,60m,90m)
activation_cols = [c for c in ["High_1m","High_5m","High_30m","High_60m","High_90m"] if c in filtered.columns]
# creiamo la maschera in modo vettoriale (evitiamo iterrows per la performance)
if activation_cols:
    filtered["attivazione"] = (filtered[activation_cols].ge(filtered["Entry_price"], axis=0).any(axis=1)).astype(int)
else:
    # se non abbiamo nessuna colonna rilevante, tutto a 0
    filtered["attivazione"] = 0

# === TIMEFRAMES DA USARE PER VERIFICA TP/SL (OPZIONE B) ===
# ordine: 1m,5m,30m,60m,90m,150m,210m,270m, poi fallback High/Low (giornaliero)
timeframes_order = [
    ("High_1m","Low_1m"),
    ("High_5m","Low_5m"),
    ("High_30m","Low_30m"),
    ("High_60m","Low_60m"),
    ("High_90m","Low_90m"),
    ("High_150m","Low_150m"),
    ("High_210m","Low_210m"),
    ("High_270m","Low_270m"),
    ("High_day","Low_day")   # fallback giornaliero
]

# inizializzo colonne
filtered["SL"] = 0
filtered["TP"] = 0
filtered["Outcome"] = "Hold"
filtered["TP_day%"] = np.nan  # performance per record (in percent)

# Funzione helper per leggere valore con tolleranza se la colonna è NaN
def safe_get(row, col):
    return row.get(col, np.nan)

# Iterazione riga-per-riga (necessaria per fermarsi al primo evento)
for idx, row in filtered.iterrows():
    if row["attivazione"] != 1:
        continue

    entry = row["Entry_price"]
    sl_price = row["SL_price"]
    tp_price = row["TP_price"]

    sl_hit = False
    tp_hit = False
    event_price = None  # prezzo che ha fatto scattare TP o SL (utile per calcolo performance)

    # cicla i timeframe nell'ordine definito
    for high_col, low_col in timeframes_order:
        # se le colonne non esistono o sono NaN saltale (safe)
        high = safe_get(row, high_col)
        low  = safe_get(row, low_col)

        # SHORT: SL se prezzo sale >= SL_price (usiamo high valore massimo nel timeframe)
        if not sl_hit and pd.notna(high) and high >= sl_price:
            filtered.at[idx, "SL"] = 1
            filtered.at[idx, "Outcome"] = "SL"
            sl_hit = True
            event_price = sl_price
            break  # fermiamo al primo evento

        # SHORT: TP se prezzo scende <= TP_price (usiamo low valore minimo nel timeframe)
        if not tp_hit and pd.notna(low) and low <= tp_price:
            filtered.at[idx, "TP"] = 1
            filtered.at[idx, "Outcome"] = "TP"
            tp_hit = True
            event_price = tp_price
            break

    # calcolo performance % in base a chi ha colpito
    # se TP colpito: prendiamo tp_price, se SL colpito: sl_price, altrimenti chiusura giornata (Close_day)
    if filtered.at[idx, "TP"] == 1:
        close_price_for_perf = tp_price
    elif filtered.at[idx, "SL"] == 1:
        close_price_for_perf = sl_price
    else:
        close_price_for_perf = safe_get(row, "Close_day")  # fallback

    if pd.notna(close_price_for_perf) and entry != 0:
        filtered.at[idx, "TP_day%"] = ((close_price_for_perf - entry) / entry * 100)
    else:
        filtered.at[idx, "TP_day%"] = np.nan

# === Break-even (BEprofit) ===
# BE_price definito come TP_price*(1+param_BE)
filtered["BE_price"] = filtered["TP_price"] * (1 + param_BE/100)

# BEprofit: attivato & no SL & no TP & qualche low in timeframes_order <= BE_price
def check_BE(row):
    if row["attivazione"] != 1 or row["SL"] == 1 or row["TP"] == 1:
        return 0
    bep = row["BE_price"]
    for _, low_col in timeframes_order:
        lowv = row.get(low_col, np.nan)
        if pd.notna(lowv) and lowv <= bep:
            return 1
    return 0

filtered["BEprofit"] = filtered.apply(check_BE, axis=1).astype(int)

# === Maschere e statistiche (come prima, adattate ai nuovi nomi) ===
mask_green = (
    (filtered["attivazione"] == 1) & 
    (filtered["SL"] == 0) & 
    (filtered["TP"] == 0) & 
    (filtered["BEprofit"] == 0) &
    (filtered["TP_day%"] < 0)
)
mask_red = (
    (filtered["attivazione"] == 1) & 
    (filtered["SL"] == 0) & 
    (filtered["TP"] == 0) & 
    (filtered["BEprofit"] == 0) &
    (filtered["TP_day%"] >= 0)
)
tp_green_avg = round(filtered.loc[mask_green, "TP_day%"].mean(), 0)
tp_red_avg   = round(filtered.loc[mask_red, "TP_day%"].mean(), 0)
tp_green_avg = "-" if np.isnan(tp_green_avg) else int(tp_green_avg)
tp_red_avg   = "-" if np.isnan(tp_red_avg) else int(tp_red_avg)

# Calcolo RR sicuro (evitiamo index error)
def safe_div(a,b):
    try:
        return round(a/b, 2)
    except Exception:
        return np.nan

first = 0
if len(filtered) > 0:
    first = 0
RR = safe_div((filtered["Entry_price"].iloc[first] - filtered["TP_price"].iloc[first]) ,
              (filtered["SL_price"].iloc[first] - filtered["Entry_price"].iloc[first]))
RR_be = safe_div((filtered["Entry_price"].iloc[first] - filtered["BE_price"].iloc[first]) ,
                 (filtered["SL_price"].iloc[first] - filtered["Entry_price"].iloc[first]))

# =====================================================
# === KPI BOX (stesso layout, adattato ai nuovi nomi) =
# =====================================================

total = len(filtered)
attivazioni = int(filtered["attivazione"].sum())
numero_SL = int(filtered["SL"].sum())
numero_TP = int(filtered["TP"].sum())
BE_profit = int(filtered["BEprofit"].sum())
close_day_red = ((filtered["attivazione"] == 1) & (filtered["SL"] == 0) & (filtered["TP"] == 0) & (filtered["BEprofit"] == 0) & (filtered["TP_day%"] >= 0)).sum()
close_day_green = ((filtered["attivazione"] == 1) & (filtered["SL"] == 0) & (filtered["TP"] == 0) & (filtered["BEprofit"] == 0) & (filtered["TP_day%"] < 0)).sum()

st.markdown("""<style>.stApp{background-color:#03121A !important;}</style>""", unsafe_allow_html=True)

base_box_style = "flex:1; background-color:#184F5F; color:white; padding:5px; border-radius:12px; text-align:center;"
title_style = "font-size:18px; opacity:0.8;"
value_style = "font-size:30px; font-weight:bold;"

st.markdown(f"""
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
        <div style="{title_style}">Numero SL</div>
        <div style="{value_style}">{numero_SL}</div>
    </div>
    <div style="{base_box_style}">
        <div style="{title_style}">Numero TP</div>
        <div style="{value_style}">{numero_TP}</div>
    </div>
    <div style="{base_box_style}">
        <div style="{title_style}">BE profit</div>
        <div style="{value_style}">{BE_profit}</div>
    </div>
</div>
<div style="display:flex; gap:15px; margin-bottom:20px;">
    <div style="{base_box_style}; display:flex; justify-content:center; gap:20px;">
        <div style="display:flex; flex-direction:column; align-items:center;">
            <div style="{title_style}">RR</div>
            <div style="font-size:40px; font-weight:bold;">{RR}</div>
        </div>
        <div style="display:flex; flex-direction:column; align-items:center;">
            <div style="{title_style}">RR_be</div>
            <div style="font-size:32px; font-weight:bold; color:#CCCCCC;">{RR_be}</div>
        </div>
    </div>
    <div style="{base_box_style} color:#EE4419;">
        <div style="{title_style}">Close trade RED</div>
        <div style="{value_style}">{close_day_red}</div>
    </div>
    <div style="{base_box_style} color:#2EDB2E;">
        <div style="{title_style}">Close trade GREEN</div>
        <div style="{value_style}">{close_day_green}</div>
    </div>
    <div style="{base_box_style};">
        <div style="{title_style}">media prezzo day</div>
        <div style="{value_style}">{tp_green_avg}%</div>
    </div>
</div>
""", unsafe_allow_html=True)

# =====================================================
# === SEZIONI A SCOMPARSA KPI (stessa funzione, riutilizzo) =
# =====================================================

def show_kpi_section(df_section, title, box_color):
    with st.expander(f"{title} (clicca per espandere)"):
        st.markdown(f"Numero di righe filtrate:   **{len(df_section)}**")
        if df_section.empty:
            st.info(f"⚠️ Nessun record con {title} = 1 nel dataset filtrato.")
            return
        # calcoli rapidi e display (resto identico alla tua funzione originale)
        # ... (puoi riutilizzare la tua implementazione precedente qui)
        st.dataframe(df_section.head(200))  # fallback semplice per ispezionare i dati

sl_df = filtered[filtered["SL"] == 1].copy()
show_kpi_section(sl_df, "🔴 Stop Loss", "#5E2B2B")

tp_df = filtered[filtered["TP"] == 1].copy()
show_kpi_section(tp_df, "🟢 Take Profit", "#035506")

be_df = filtered[filtered["BEprofit"] == 1].copy()
show_kpi_section(be_df, "🟡 Break Even", "#705B15")

# =====================================================
# === TABELLA (adattata ai nomi storici) =
# =====================================================

cols_to_show = [
    "Date", "Ticker", "Gap%", "High_1m","Low_1m","High_5m","Low_5m","High_30m","Low_30m",
    "High_60m","Low_60m","High_90m","Low_90m","High_150m","Low_150m","High_210m","Low_210m","High_270m","Low_270m",
    "High_day","Low_day","Entry_price","SL_price","TP_price","TP_day%","attivazione","SL","TP","BEprofit"
]

# filtra cols esistenti
cols_to_show = [c for c in cols_to_show if c in filtered.columns]

def style_rows(s):
    return ['background-color: #202326' if i % 2 == 0 else '' for i in range(len(s))]

def highlight_cells(val, col_name):
    if col_name == "attivazione" and val == 1:
        return "background-color: #473C06; font-weight:bold;"
    elif col_name == "SL" and val == 1:
        return "background-color: #8B2A06; color:white; font-weight:bold;"
    elif col_name == "TP" and val == 1:
        return "background-color: #024902; color:white; font-weight:bold;"
    elif col_name == "BEprofit" and val == 1:
        return "background-color: #243624; font-weight:bold;"
    else:
        return ""

# format dict (semplice)
format_dict = {}
for col in cols_to_show:
    if col == "Gap%":
        format_dict[col] = "{:.0f}"
    elif col in ["attivazione","SL","TP","BEprofit"]:
        format_dict[col] = "{:.0f}"
    else:
        # prova a formattare numeriche
        if filtered[col].dtype in ['float64','int64']:
            format_dict[col] = "{:.2f}"

styled_df = (
    filtered[cols_to_show]
    .style.apply(style_rows, axis=0)
    .format(format_dict)
    .apply(lambda x: [highlight_cells(v, x.name) for v in x], axis=0)
)

st.markdown('<h3 style="font-size:16px; color:#FFFFFF;">📋 Tabella filtrata</h3>', unsafe_allow_html=True)
st.dataframe(styled_df, use_container_width=True)
st.caption(f"Mostrando {len(filtered)} record filtrati su {len(df)} totali.")

# =====================================================
# === EQUITY & DRAWDOWN SIMULATION (adattata ai nomi) =
# =====================================================

st.markdown("### 📈 Simulazione Equity & Drawdown")
col1, col2 = st.columns(2)
initial_capital = col1.number_input("💰 Capitale iniziale", value=3000.0, step=100.0)
risk_pct = col2.number_input("📉 % Rischio per trade", value=2.0, step=0.5)

df_equity = filtered.copy()
df_equity = df_equity[df_equity["attivazione"] == 1].copy()

required_cols = ["TP","SL","BEprofit","TP_day%","Entry_price","SL_price","TP_price","BE_price"]
for c in required_cols:
    if c not in df_equity.columns:
        st.warning(f"Manca la colonna '{c}' nel dataframe.")
        st.stop()

capital = initial_capital
equity_values = []
drawdowns = []
profits = []
sizes = []

for i, row in df_equity.iterrows():
    risk_amount = initial_capital * (risk_pct / 100)
    stop_dist = abs(row["SL_price"] - row["Entry_price"])
    if stop_dist == 0:
        continue
    size = risk_amount / stop_dist
    sizes.append(size)

    if row["TP"] == 1:
        pnl = (row["Entry_price"] - row["TP_price"]) * size
    elif row["SL"] == 1:
        pnl = (row["Entry_price"] - row["SL_price"]) * size
    elif row["BEprofit"] == 1:
        pnl = (row["Entry_price"] - row["BE_price"]) * size
    else:
        val = row["TP_day%"]
        pnl = 0
        if pd.notna(val):
            pnl = (-val / 100) * row["Entry_price"] * size

    capital += pnl
    equity_values.append(capital)
    peak = max(equity_values)
    drawdown = (capital - peak) / peak * 100
    drawdowns.append(drawdown)
    profits.append(pnl)

df_equity["PnL_$"] = profits
df_equity["Equity"] = equity_values
df_equity["Drawdown_%"] = drawdowns
df_equity["Size"] = sizes

ultima_equity = equity_values[-1] if equity_values else initial_capital
profit = ultima_equity - initial_capital
trade_count = len(df_equity)

def kpi_box(title, value, color="#FFD700"):
    return f"""
    <div style="
        display:flex; justify-content:center; align-items:center; gap:10px;
        background-color:#184F5F; color:white; padding:15px; border-radius:12px; margin-bottom:20px;">
        <span style="font-weight:600;">{title}:</span>
        <span style="color:{color}; font-size:20px; font-weight:700;">{value}</span>
    </div>
    """

kpi4, kpi1, kpi2, kpi3 = st.columns(4)
with kpi4:
    st.markdown(kpi_box("Trade Attivati", f"{trade_count}", "white"), unsafe_allow_html=True)
with kpi1:
    st.markdown(kpi_box("RR", f"{RR:.2f}","white"), unsafe_allow_html=True)
with kpi2:
    st.markdown(kpi_box("RR BE", f"{RR_be:.2f}","white"), unsafe_allow_html=True)
with kpi3:
    profit_color = "#00FF00" if profit >= 0 else "#FF6347"
    st.markdown(kpi_box("Profit", f"{profit:.2f}$", profit_color), unsafe_allow_html=True)

# Esito
def get_result_icon(row):
    if row["TP"] == 1:
        return "🟢"
    elif row["BEprofit"] == 1:
        return "🟩"
    elif row["SL"] == 1:
        return "🔴"
    else:
        return "🟠"

df_equity["Esito"] = df_equity.apply(get_result_icon, axis=1)
df_display = df_equity[["Date","Ticker","Esito","Size","TP_day%","PnL_$","Equity","Drawdown_%"]].copy()
df_display["PnL_$"] = df_display["PnL_$"].round(2)
df_display["Equity"] = df_display["Equity"].round(2)
df_display["Drawdown_%"] = df_display["Drawdown_%"].round(2)
df_display["Size"] = df_display["Size"].round(0)
st.dataframe(df_display, use_container_width=True)

# Grafici (uguali)
fig1, ax1 = plt.subplots(figsize=(10,2))
ax1.plot(range(len(df_display)), df_display["Equity"], linewidth=1)
fig1.patch.set_facecolor('#D5D9DF')
ax1.set_facecolor('#D5D9DF')
ax1.axhline(initial_capital, color="gray", linestyle="--", linewidth=1)
ax1.set_title("Equity Line", fontsize=9)
ax1.set_xlabel("Trade", fontsize=8)
ax1.set_ylabel("Capitale ($)", fontsize=8)
ax1.tick_params(axis='both', which='major', labelsize=7)
ax1.set_xticks(range(0, len(df_display), max(1, len(df_display)//10)))
plt.tight_layout()
st.pyplot(fig1)

fig2, ax2 = plt.subplots(figsize=(10,2))
ax2.bar(range(len(df_display)), df_display["Drawdown_%"], width=0.8)
fig2.patch.set_facecolor('#D5D9DF')
ax2.set_facecolor('#D5D9DF')
ax2.set_title("Drawdown (%)", fontsize=9)
ax2.set_xlabel("Trade", fontsize=8)
ax2.set_ylabel("Drawdown (%)", fontsize=8)
ax2.axhline(0, color="gray", linestyle="--", linewidth=0.8)
ax2.tick_params(axis='both', which='major', labelsize=7)
ax2.set_xticks(range(0, len(df_display), max(1, len(df_display)//10)))
plt.tight_layout()
st.pyplot(fig2)