import streamlit as st
import pandas as pd
from dateutil import parser
import numpy as np
import matplotlib.pyplot as plt

# ---- CONFIGURAZIONE ----
st.set_page_config(page_title="Strategia Intraday", layout="wide")
st.title("📊 Strategia Intraday")

# ---- CARICAMENTO DATI CON CACHE ----
SHEET_URL = "https://docs.google.com/spreadsheets/d/15ev2l8av7iil_-HsXMZihKxV-B5MgTVO-LnK1y_f2-o/export?format=xlsx"

@st.cache_data
def load_data():
    usecols = [
        "Date", "Ticker", "Open", "Gap%", "Shs Float", "Shares Outstanding", "TimeHigh", "HighPM", "High",
        "Close_1030", "High_60m", "Low_60m", "High_90m", "Low_90m", "Close_1100"
    ]
    df = pd.read_excel(SHEET_URL, sheet_name="scarico_intraday", usecols=usecols)
    # Parse date
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d-%m-%Y")
    return df

df = load_data()



# region Filtri
# ---- FILTRI LATERALI ----
st.sidebar.header("🔍 Filtri e parametri")
date_range = st.sidebar.date_input("Intervallo date", [])
min_open = st.sidebar.number_input("Open minimo", value=0.0)
min_gap = st.sidebar.number_input("Gap% minimo", value=0.0)
max_float = st.sidebar.number_input("Shs Float", value=1000000000)
param_sl = st.sidebar.number_input("%SL", value=30.0)
param_tp = st.sidebar.number_input("%TP", value=-15.0)
param_entry = st.sidebar.number_input("%entry", value=15.0)
param_BE = st.sidebar.number_input("%BEparam", value=5.0,
    help="Percentuale da aggiungere al prezzo di TP"
)

filtered = df.copy()

# Converti Gap% e Open in numerico
filtered["Gap%"] = pd.to_numeric(filtered["Gap%"], errors="coerce")
filtered["Open"] = pd.to_numeric(filtered["Open"], errors="coerce")

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
filtered = filtered[filtered["Open"] >= min_open]
filtered = filtered[filtered["Gap%"] >= min_gap]
filtered = filtered[filtered["Shs Float"] <= max_float]

# ---- Dopo filtraggio ----
if not filtered.empty:
    min_date = filtered["Date_dt"].min()
    max_date = filtered["Date_dt"].max()
    if pd.notna(min_date) and pd.notna(max_date):
        # Solo le date colorate e in grassetto
        st.markdown(
            f"""
            <div style='font-size:16px; font-weight:600; margin-bottom:10px;'>
                Dati filtrati dal <span style='font-size:18px; color:#1E90FF; font-weight:bold;'>{min_date.strftime('%d-%m-%Y')}</span> 
                al <span style='color:#1E90FF; font-weight:bold;'>{max_date.strftime('%d-%m-%Y')}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.info("⚠️ Nessun dato disponibile dopo i filtri.")


# endregion

# region ---- CALCOLI ENTRY / SL / TP / ATTIVAZIONE ----
filtered["SL_price"] = filtered["Open"] * (1 + param_sl/100)
filtered["TP_price"] = filtered["Open"] * (1 + param_tp/100)
filtered["Entry_price"] = filtered["Open"] * (1 + param_entry/100)

filtered["attivazione"] = (filtered["High_60m"] >= filtered["Entry_price"]).astype(int)
filtered["SL"] = ((filtered["attivazione"] == 1) & (filtered["High_90m"] >= filtered["SL_price"])).astype(int)
filtered["TP"] = ((filtered["attivazione"] == 1) & (filtered["SL"] == 0) & (filtered["Low_90m"] <= filtered["TP_price"])).astype(int)

# Calcolo BEprofit
filtered["BEprofit"] = (
    (filtered["attivazione"] == 1) &
    (filtered["SL"] == 0) &
    (filtered["TP"] == 0) &
    (filtered["Low_90m"] <= filtered["TP_price"] * (1 + param_BE/100))
).astype(int)

filtered["BE_price"] = filtered["TP_price"] * (1 + param_BE/100)

# Calcolo TP_90m
filtered["TP_90m%"] = ((filtered["Close_1100"] - filtered["Entry_price"]) / filtered["Open"] * 100).round(2)
mask_green = (
    (filtered["attivazione"] == 1) & 
    (filtered["SL"] == 0) & 
    (filtered["TP"] == 0) & 
    (filtered["BEprofit"] == 0) &
    (filtered["TP_90m%"] < 0)
)
mask_red = (
    (filtered["attivazione"] == 1) & 
    (filtered["SL"] == 0) & 
    (filtered["TP"] == 0) & 
    (filtered["BEprofit"] == 0) &
    (filtered["TP_90m%"] >= 0)
)
tp_90m_green_avg = round(filtered.loc[mask_green, "TP_90m%"].mean(), 0)
tp_90m_red_avg   = round(filtered.loc[mask_red, "TP_90m%"].mean(), 0)
# Se è NaN → "-"
tp_90m_green_avg = "-" if np.isnan(tp_90m_green_avg) else tp_90m_green_avg
tp_90m_red_avg   = "-" if np.isnan(tp_90m_red_avg) else tp_90m_red_avg


# Calcolo RR
filtered["RR"] = (filtered["Entry_price"]-filtered["TP_price"])/(filtered["SL_price"]-filtered["Entry_price"])
filtered["RR_be"] = (filtered["Entry_price"]-filtered["BE_price"])/(filtered["SL_price"]-filtered["Entry_price"])

# endregion

# region ---- KPI BOX ----
total = len(filtered)
attivazioni = filtered["attivazione"].sum()
numero_SL = filtered["SL"].sum()
numero_TP = filtered["TP"].sum()
BE_profit = filtered["BEprofit"].sum()
close_90m_red = ((filtered["attivazione"] == 1) & 
             (filtered["SL"] == 0) & 
             (filtered["TP"] == 0) & 
             (filtered["BEprofit"] == 0) &
             (filtered["TP_90m%"] >= 0)
            ).sum()
close_90m_green = ((filtered["attivazione"] == 1) & 
             (filtered["SL"] == 0) & 
             (filtered["TP"] == 0) & 
             (filtered["BEprofit"] == 0) &
             (filtered["TP_90m%"] < 0)
            ).sum()

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
    padding:15px; 
    border-radius:12px; 
    text-align:center;
"""

# Stile del titolo e del valore
title_style = "font-size:18px; opacity:0.8;"
value_style = "font-size:30px; font-weight:bold;"

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

<!-- SECONDA RIGA: 3 BOX -->
<div style="display:flex; gap:15px; margin-bottom:20px;">
    <!-- Box con colore testo personalizzato -->
    <div style="{base_box_style} color:#EE4419;">
        <div style="{title_style}">Close 90m RED</div>
        <div style="{value_style}">{close_90m_red}</div>
    </div>
    <!-- Box con colore testo personalizzato -->
    <div style="{base_box_style} color:#2EDB2E;">
        <div style="{title_style}">Close 90m GREEN</div>
        <div style="{value_style}">{close_90m_green}</div>
    </div>
    <div style="{base_box_style} color:#2EDB2E;">
        <div style="{title_style}">tp 90m GREEN</div>
        <div style="{value_style}">{tp_90m_green_avg}</div>
    </div>
</div>
""", unsafe_allow_html=True)


# endregion

# region ---- FUNZIONE UNIFICATA PER LE SEZIONI A SCOMPARSA ----

import pandas as pd
import streamlit as st

def show_kpi_section(df, title, box_color):
    """
    Mostra una sezione di KPI in un expander Streamlit usando box uniformi con display:grid.
    
    df: DataFrame già filtrato (es. SL=1, TP=1, BEprofit=1)
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

        # --- Lista dei box ---
        boxes = [
            {"label": "Gap%", "value": gap_mean_str, "sub": f"Mediana: {gap_median_str}"},
            {"label": "Shs Float medio", "value": shs_float_mean_str, "sub": f"Mediana: {shs_float_median_str}"},
            {"label": "Shs Outstanding medio", "value": shs_out_mean_str, "sub": f"Mediana: {shs_out_median_str}"},
            {"label": "Spinta medio", "value": high_mean_str, "sub": f"Mediana: {high_median_str}"},
            {"label": "TimeHigh medio", "value": time_mean_formatted},
            {"label": "Open vs PMH medio", "value": openVSpmh_mean_str, "sub": f"Mediana: {openVSpmh_median_str}"}
        ]

        # --- Stile ---
        LABEL_STYLE = "font-size:14px; opacity:0.85;"
        VALUE_STYLE = "font-size:24px; font-weight:bold;"
        SUBVALUE_STYLE = "font-size:15px; font-weight:600; opacity:0.85; margin-top:6px;"

        BOX_STYLE = f"""
            background-color:{{}}; 
            padding:15px; 
            border-radius:12px; 
            text-align:center; 
            box-shadow: 0 2px 6px rgba(0,0,0,0.3); 
            display:flex; 
            flex-direction:column; 
            justify-content:center; 
            align-items:center;
            min-height:150px;
        """

        # --- Container grid responsive ---
        container_html_start = """
        <div style="
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); 
            gap: 10px; 
            grid-auto-rows: 1fr;
            margin-top:10px; 
            margin-bottom:10px;
        ">
        """
        container_html_end = "</div>"

        # --- Genera HTML dei box ---
        boxes_html = ""
        for box in boxes:
            sub_html = f'<div style="{SUBVALUE_STYLE}">{box["sub"]}</div>' if "sub" in box else ""
            boxes_html += f'<div style="{BOX_STYLE.format(box_color)}">' \
                          f'<div style="{LABEL_STYLE}">{box["label"]}</div>' \
                          f'<div style="{VALUE_STYLE}">{box["value"]}</div>' \
                          f'{sub_html}' \
                          f'</div>'

        st.markdown(container_html_start + boxes_html + container_html_end, unsafe_allow_html=True)


# ---- USO DELLA FUNZIONE ----
sl_df = filtered[filtered["SL"] == 1].copy()
show_kpi_section(sl_df, "🔴 Stop Loss", "#5E2B2B")

tp_df = filtered[filtered["TP"] == 1].copy()
show_kpi_section(tp_df, "🟢 Take Profit", "#035506")

be_df = filtered[filtered["BEprofit"] == 1].copy()
show_kpi_section(be_df, "🟡 Break Even", "#705B15")

# endregion

# region ---- TABELLA ----

# Colonne da mostrare in tabella
cols_to_show = ["Date", "Ticker", "Gap%", "High_60m", "Low_60m", "Close_1030",
                "High_90m", "Low_90m", "Close_1100", "Entry_price", "SL_price", "TP_price",
                "TP_90m%", "RR","RR_be", "attivazione", "SL", "TP", "BEprofit"]


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
    elif col_name == "BEprofit" and val == 1:
        return "background-color: #243624; font-weight:bold;" 

    else:
        return ""

# Definizione formato numeri
format_dict = {}
for col in cols_to_show:
    if col == "Gap%":
        format_dict[col] = "{:.0f}"
    elif col in ["attivazione", "SL", "TP", "BEprofit"]:
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

# === EQUITY & DRAWDOWN SIMULATION ===


st.markdown("### 📈 Simulazione Equity & Drawdown")

# ---- INPUT PARAMETRI ----
col1, col2, col3, col4 = st.columns(4)
initial_capital = col1.number_input("💰 Capitale iniziale", value=10000.0, step=1000.0)
risk_pct = col2.number_input("📉 % Rischio per trade (SL%)", value=3.0, step=0.5)
rr = col3.number_input("📈 Rapporto Rischio/Rendimento (RR)", value=2.0, step=0.5)
rr_be = col4.number_input("⚖️ RR Break-Even profit", value=0.3, step=0.1)

# ---- COSTRUZIONE DATAFRAME ----
df_equity = filtered.copy()  # df filtrato dopo i controlli e filtri utente

# Evitiamo errori su colonne mancanti
for col in ["TP", "SL", "BEprofit", "TP_90m%"]:
    if col not in df_equity.columns:
        st.warning(f"Manca la colonna '{col}' nel dataframe.")
        st.stop()

# ---- CALCOLO RENDIMENTO PERCENTUALE ----
sl_pct = risk_pct / 100.0

def calc_trade_return(row):
    if row["TP"] == 1:
        return rr * sl_pct       # profitto
    elif row["SL"] == 1:
        return -sl_pct            # perdita
    elif "BEprofit" in row and row["BEprofit"] == 1:
        return rr_be * sl_pct     # piccolo profitto
    else:
        # Caso chiusura 90m: se negativo = guadagno (short)
        val = row["TP_90m%"]
        return (-val / 100) if pd.notna(val) else 0

df_equity["Trade_Return"] = df_equity.apply(calc_trade_return, axis=1)

# ---- SIMULAZIONE EQUITY ----
df_equity["Equity"] = initial_capital * (1 + df_equity["Trade_Return"]).cumprod()

# ---- CALCOLO DRAWDOWN ----
df_equity["Peak"] = df_equity["Equity"].cummax()
df_equity["Drawdown"] = (df_equity["Equity"] - df_equity["Peak"]) / df_equity["Peak"] * 100

# ---- TABELLA RIASSUNTIVA ----
df_display = df_equity[["Date", "Ticker", "TP", "SL", "BEprofit", "TP_90m%", "Trade_Return", "Equity", "Drawdown"]].copy()
df_display["Trade_Return"] = (df_display["Trade_Return"] * 100).round(2)
df_display["Equity"] = df_display["Equity"].round(2)
df_display["Drawdown"] = df_display["Drawdown"].round(2)

st.dataframe(df_display, use_container_width=True)

# ---- GRAFICO EQUITY ----
fig1, ax1 = plt.subplots()
ax1.plot(df_equity["Equity"], linewidth=2)
ax1.set_title("Equity Line")
ax1.set_xlabel("Trade #")
ax1.set_ylabel("Capitale ($)")
st.pyplot(fig1)

# ---- GRAFICO DRAWDOWN ----
fig2, ax2 = plt.subplots()
ax2.plot(df_equity["Drawdown"], color="red", linewidth=2)
ax2.set_title("Drawdown (%)")
ax2.set_xlabel("Trade #")
ax2.set_ylabel("Drawdown (%)")
st.pyplot(fig2)
