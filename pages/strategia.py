import streamlit as st
import pandas as pd
from dateutil import parser
import numpy as np

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

# ---- FILTRI LATERALI ----
st.sidebar.header("🔍 Filtri e parametri")
date_range = st.sidebar.date_input("Intervallo date", [])
min_open = st.sidebar.number_input("Open minimo", value=0.0)
min_gap = st.sidebar.number_input("Gap% minimo", value=0.0)
param_sl = st.sidebar.number_input("%SL", value=30.0)
param_tp = st.sidebar.number_input("%TP", value=-15.0)
param_entry = st.sidebar.number_input("%entry", value=15.0)
param_BE = st.sidebar.number_input("%BEparam", value=5.0,
    help="Percentuale da aggiungere al prezzo di TP"
)


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

# Calcolo BEprofit
filtered["BEprofit"] = (
    (filtered["attivazione"] == 1) &
    (filtered["SL"] == 0) &
    (filtered["TP"] == 0) &
    (filtered["Low_90m"] <= filtered["TP_price"] * (1 + param_BE/100))
).astype(int)

filtered["BE_price"] = filtered["TP_price"] * (1 + param_BE/100)

# Calcolo TP_90m
filtered["TP_90m"] = filtered["Entry_price"] - filtered["Close_1100"]

# Calcolo RR
filtered["RR"] = (filtered["Entry_price"]-filtered["TP_price"])/(filtered["SL_price"]-filtered["Entry_price"])
filtered["RR_be"] = (filtered["Entry_price"]-filtered["BE_price"])/(filtered["SL_price"]-filtered["Entry_price"])


# ---- KPI BOX ----
total = len(filtered)
attivazioni = filtered["attivazione"].sum()
numero_SL = filtered["SL"].sum()
numero_TP = filtered["TP"].sum()
BE_profit = filtered["BEprofit"].sum()
close_90m_red = ((filtered["attivazione"] == 1) & 
             (filtered["SL"] == 0) & 
             (filtered["TP"] == 0) & 
             (filtered["BEprofit"] == 0) &
             (filtered["TP_90m"] <= 0)
            ).sum()
close_90m_green = ((filtered["attivazione"] == 1) & 
             (filtered["SL"] == 0) & 
             (filtered["TP"] == 0) & 
             (filtered["BEprofit"] == 0) &
             (filtered["TP_90m"] > 0)
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

st.markdown(
    f"""
    <!-- PRIMA RIGA: 4 BOX -->
    <div style="display:flex; gap:15px; margin-bottom:20px;">
        <div style="flex:1; background-color:#184F5F; color:white; padding:15px; border-radius:12px; text-align:center;">
            <div style="font-size:14px; opacity:0.8;">Totale record</div>
            <div style="font-size:24px; font-weight:bold;">{total}</div>
        </div>
        <div style="flex:1; background-color:#184F5F; color:white; padding:15px; border-radius:12px; text-align:center;">
            <div style="font-size:14px; opacity:0.8;">Attivazioni</div>
            <div style="font-size:24px; font-weight:bold;">{attivazioni}</div>
        </div>
        <div style="flex:1; background-color:#184F5F; color:white; padding:15px; border-radius:12px; text-align:center;">
            <div style="font-size:14px; opacity:0.8;">Numero SL</div>
            <div style="font-size:24px; font-weight:bold;">{numero_SL}</div>
        </div>
        <div style="flex:1; background-color:#184F5F; color:white; padding:15px; border-radius:12px; text-align:center;">
            <div style="font-size:14px; opacity:0.8;">Numero TP</div>
            <div style="font-size:24px; font-weight:bold;">{numero_TP}</div>
        </div>
    </div>
    <!-- SECONDA RIGA: 3 BOX -->
    <div style="display:flex; gap:15px; margin-bottom:20px;">
        <div style="flex:1; background-color:#184F5F; color:white; padding:15px; border-radius:12px; text-align:center;">
            <div style="font-size:14px; opacity:0.8;">BE profit</div>
            <div style="font-size:24px; font-weight:bold;">{BE_profit}</div>
        </div>
        <div style="flex:1; background-color:#184F5F; color:#EE4419; padding:15px; border-radius:12px; text-align:center;">
            <div style="font-size:14px; opacity:0.8;">Close 90m RED</div>
            <div style="font-size:24px; font-weight:bold;">{close_90m_red}</div>
        </div>
        <div style="flex:1; background-color:#184F5F; color:#2EDB2E; padding:15px; border-radius:12px; text-align:center;">
            <div style="font-size:14px; opacity:0.8;">Close 90m GREEN</div>
            <div style="font-size:24px; font-weight:bold;">{close_90m_green}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ---- FUNZIONE UNIFICATA PER LE SEZIONI A SCOMPARSA ----

def show_kpi_section(df, col_filter, titolo, colore):
    """
    df: DataFrame filtrato
    col_filter: colonna da filtrare (SL, TP, BEprofit)
    titolo: nome della sezione
    colore: colore dei box in HEX
    """
    df_sel = df[df[col_filter] == 1].copy()
    st.markdown(f"**{titolo} - Numero di righe filtrate: {len(df_sel)}**")
    
    if df_sel.empty:
        st.info(f"⚠️ Nessun record con {col_filter} = 1 nel dataset filtrato.")
        return
    
    # Calcoli
    gap_mean = df_sel["Gap%"].mean()
    gap_median = df_sel["Gap%"].median()
    shs_float_mean = df_sel["Shs Float"].mean() if "Shs Float" in df_sel.columns else None
    shs_float_median = df_sel["Shs Float"].median() if "Shs Float" in df_sel.columns else None
    shs_out_mean = df_sel["Shares Outstanding"].mean() if "Shares Outstanding" in df_sel.columns else None
    shs_out_median = df_sel["Shares Outstanding"].median() if "Shares Outstanding" in df_sel.columns else None

    # High%
    if "High" in df_sel.columns:
        df_sel["high%"] = ((df_sel["High"] - df_sel["Open"])/df_sel["High"])*100
        high_mean = df_sel["high%"].mean()
        high_median = df_sel["high%"].median()
    else:
        high_mean = high_median = None

    # TimeHigh
    df_sel["TimeHigh"] = pd.to_datetime(df_sel["TimeHigh"], errors="coerce")
    if not df_sel["TimeHigh"].dropna().empty:
        time_seconds = df_sel["TimeHigh"].dropna().apply(lambda x: x.hour*3600 + x.minute*60)
        time_avg = time_seconds.mean()
        time_mean_formatted = f"{int(time_avg // 3600):02d}:{int((time_avg % 3600)//60):02d}"
    else:
        time_mean_formatted = "-"

    # Open vs HighPM
    if "HighPM" in df_sel.columns:
        df_sel["openVSpmh"] = ((df_sel["Open"] - df_sel["HighPM"])/df_sel["HighPM"])*100
        openVSpmh_mean = df_sel["openVSpmh"].mean()
        openVSpmh_median = df_sel["openVSpmh"].median()
    else:
        openVSpmh_mean = openVSpmh_median = None

    # Formattazione valori
    gap_mean_str = f"{gap_mean:.0f}%" if gap_mean is not None else "-"
    gap_median_str = f"{gap_median:.0f}%" if gap_median is not None else "-"
    shs_float_mean_str = f"{shs_float_mean/1_000_000:.0f}M" if shs_float_mean is not None else "-"
    shs_float_median_str = f"{shs_float_median/1_000_000:.2f}M" if shs_float_median is not None else "-"
    shs_out_mean_str = f"{shs_out_mean/1_000_000:.0f}M" if shs_out_mean is not None else "-"
    shs_out_median_str = f"{shs_out_median/1_000_000:.2f}M" if shs_out_median is not None else "-"
    high_mean_str = f"{high_mean:.0f}%" if high_mean is not None else "-"
    high_median_str = f"{high_median:.0f}%" if high_median is not None else "-"
    openvspmh_mean_str = f"{openVSpmh_mean:.0f}%" if openVSpmh_mean is not None else "-"
    openvspmh_median_str = f"{openVSpmh_median:.0f}%" if openVSpmh_median is not None else "-"

    # Stile unico
    BOX_STYLE = f"flex:1; background-color:{colore}; color:white; padding:15px; border-radius:12px; text-align:center; box-shadow: 0 2px 6px rgba(0,0,0,0.3);"
    LABEL_STYLE = "font-size:14px; opacity:0.85;"
    VALUE_STYLE = "font-size:24px; font-weight:bold;"
    SUBVALUE_STYLE = "font-size:15px; font-weight:600; opacity:0.85; margin-top:6px;"

    html = f"""
    <div style="display:flex; gap:15px; margin-top:10px; margin-bottom:10px; flex-wrap:wrap;">
        <div style="{BOX_STYLE}">
            <div style="{LABEL_STYLE}">Gap%</div>
            <div style="{VALUE_STYLE}">{gap_mean_str}</div>
            <div style="{SUBVALUE_STYLE}">Mediana: {gap_median_str}</div>
        </div>

        <div style="{BOX_STYLE}">
            <div style="{LABEL_STYLE}">Shs Float medio</div>
            <div style="{VALUE_STYLE}">{shs_float_mean_str}</div>
            <div style="{SUBVALUE_STYLE}">Mediana: {shs_float_median_str}</div>
        </div>

        <div style="{BOX_STYLE}">
            <div style="{LABEL_STYLE}">Shares Outstanding medio</div>
            <div style="{VALUE_STYLE}">{shs_out_mean_str}</div>
            <div style="{SUBVALUE_STYLE}">Mediana: {shs_out_median_str}</div>
        </div>

        <div style="{BOX_STYLE}">
            <div style="{LABEL_STYLE}">Spinta medio</div>
            <div style="{VALUE_STYLE}">{high_mean_str}</div>
            <div style="{SUBVALUE_STYLE}">Mediana: {high_median_str}</div>
        </div>

        <div style="{BOX_STYLE}">
            <div style="{LABEL_STYLE}">TimeHigh medio</div>
            <div style="{VALUE_STYLE}">{time_mean_formatted}</div>
        </div>

        <div style="{BOX_STYLE}">
            <div style="{LABEL_STYLE}">Open vs HighPM (medio)</div>
            <div style="{VALUE_STYLE}">{openvspmh_mean_str}</div>
            <div style="{SUBVALUE_STYLE}">Mediana: {openvspmh_median_str}</div>
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


# ---- USO DELLA FUNZIONE ----
with st.expander("📉 Dettaglio Stop Loss (clicca per espandere)"):
    show_kpi_section(filtered, "SL", "Stop Loss", "#5E2B2B")  # rosso scuro

with st.expander("🟢 Dettaglio Take Profit (clicca per espandere)"):
    show_kpi_section(filtered, "TP", "Take Profit", "#27AE60")  # verde

with st.expander("💛 Dettaglio Break Even (clicca per espandere)"):
    show_kpi_section(filtered, "BEprofit", "Break Even", "#F9E79F")  # giallo chiaro



# ---- TABELLA ----

# Colonne da mostrare in tabella
cols_to_show = ["Date", "Ticker", "Gap%", "High_60m", "Low_60m", "Close_1030",
                "High_90m", "Low_90m", "Close_1100", "Entry_price", "SL_price", "TP_price",
                "TP_90m", "RR","RR_be", "attivazione", "SL", "TP", "BEprofit"]


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

