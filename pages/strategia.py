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
        "Date", "Ticker", "Open", "Gap%", "Shs Float", "Shares Outstanding", "TimeHigh",
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


# ---- SEZIONE DETTAGLIO SL ----
with st.expander("📉 Dettaglio Stop Loss (clicca per espandere)"):
    sl_df = filtered[filtered["SL"] == 1].copy()


    if not sl_df.empty:
        # Calcoli
        gap_mean = sl_df["Gap%"].mean()
        gap_median = sl_df["Gap%"].median()
        shs_float_mean = sl_df["Shs Float"].mean() if "Shs Float" in sl_df.columns else None
        shs_out_mean = sl_df["Shares Outstanding"].mean() if "Shares Outstanding" in sl_df.columns else None

        # TimeHigh medio
        if "TimeHigh" in sl_df.columns:
            time_seconds = sl_df["TimeHigh"].dropna().apply(lambda x: pd.to_timedelta(str(x)).total_seconds())
            time_avg = time_seconds.mean()
            if pd.notna(time_avg):
                hhmm_avg = f"{int(time_avg//3600):02d}:{int((time_avg%3600)//60):02d}"
            else:
                hhmm_avg = "-"
        else:
            hhmm_avg = "-"

        # Open vs HighPM
        if "HighPM" in sl_df.columns:
            sl_df["openVSpmh"] = sl_df["Open"] - sl_df["HighPM"]
            openVSpmh_mean = sl_df["openVSpmh"].mean()
        else:
            openVSpmh_mean = None

        # ✅ Pre-formatto qui i valori in stringhe
        gap_mean_str = f"{gap_mean:.0f}"
        gap_median_str = f"{gap_median:.0f}"
        shs_float_str = f"{shs_float_mean:.2f}" if shs_float_mean is not None else "-"
        shs_out_str = f"{shs_out_mean:.2f}" if shs_out_mean is not None else "-"
        openvspmh_str = f"{openVSpmh_mean:.2f}" if openVSpmh_mean is not None else "-"

        # ---- BOX KPI ----
        st.markdown(
            f"""
            <div style="display:flex; gap:15px; margin-top:10px; margin-bottom:10px;">
                <div style="flex:1; background-color:#5E2B2B; color:white; padding:15px; border-radius:12px; text-align:center;">
                    <div style="font-size:14px; opacity:0.8;">Gap% medio</div>
                    <div style="font-size:24px; font-weight:bold;">{gap_mean_str}</div>
                </div>
                <div style="flex:1; background-color:#5E2B2B; color:white; padding:15px; border-radius:12px; text-align:center;">
                    <div style="font-size:14px; opacity:0.8;">Gap% mediana</div>
                    <div style="font-size:24px; font-weight:bold;">{gap_median_str}</div>
                </div>
                <div style="flex:1; background-color:#5E2B2B; color:white; padding:15px; border-radius:12px; text-align:center;">
                    <div style="font-size:14px; opacity:0.8;">Shs Float medio</div>
                    <div style="font-size:24px; font-weight:bold;">{shs_float_str}</div>
                </div>
                <div style="flex:1; background-color:#5E2B2B; color:white; padding:15px; border-radius:12px; text-align:center;">
                    <div style="font-size:14px; opacity:0.8;">Shares Outstanding medio</div>
                    <div style="font-size:24px; font-weight:bold;">{shs_out_str}</div>
                </div>
                <div style="flex:1; background-color:#5E2B2B; color:white; padding:15px; border-radius:12px; text-align:center;">
                    <div style="font-size:14px; opacity:0.8;">TimeHigh medio</div>
                    <div style="font-size:24px; font-weight:bold;">{hhmm_avg}</div>
                </div>
                <div style="flex:1; background-color:#5E2B2B; color:white; padding:15px; border-radius:12px; text-align:center;">
                    <div style="font-size:14px; opacity:0.8;">Open vs HighPM (medio)</div>
                    <div style="font-size:24px; font-weight:bold;">{openvspmh_str}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    else:
        st.info("⚠️ Nessun record con SL = 1 nel dataset filtrato.")





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

