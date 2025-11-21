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
    st.markdown("<h1 style='margin-bottom:0px;'>Strategia Intraday Opzioni</h1>", unsafe_allow_html=True)

with col2:
    mode = st.radio(
        "Modalità",
        ["Fino a chiusura", "90 minuti"],
        index=1,
        horizontal=True,
        label_visibility="visible"
    )

# ---- CARICAMENTO DATI CON CACHE ----
SHEET_URL = "https://docs.google.com/spreadsheets/d/15ev2l8av7iil_-HsXMZihKxV-B5MgTVO-LnK1y_f2-o/export?format=xlsx"

@st.cache_data
def load_data():
    usecols = [
        "Date", "Ticker", "Open", "Gap%", "Shs Float", "Shares Outstanding", "TimeHigh", "HighPM", "High", "Low","Close",
        "Close_1030", "High_60m", "Low_60m", "High_90m", "Low_90m", "Close_1100", "Volume", "VolumePM", "Volume_30m", "Volume_5m",
        "High_120m", "Low_120m", "High_240m", "Low_240m", "High_30m", "Low_30m", "Market Cap"
    ]
    df = pd.read_excel(SHEET_URL, sheet_name="scarico_intraday", usecols=usecols)
    # Parse date
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d-%m-%Y")
    return df

df = load_data()



# region Filtri
# ---- FILTRI LATERALI ----

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
min_open = st.sidebar.number_input("Open minimo", value=2.0)
min_gap = st.sidebar.number_input("Gap% minimo", value=50.0)
max_float = st.sidebar.number_input("Shs Float", value=1000000000)
param_sl = st.sidebar.number_input("%SL", value=30.0)
param_tp = st.sidebar.number_input("%TP", value=-15.0)
param_entry = st.sidebar.number_input("%entry", value=15.0)
param_BE = st.sidebar.number_input("%BEparam", value=0.0,
    help="Percentuale da aggiungere al prezzo di TP"
)

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
filtered = filtered[filtered["Open"] >= min_open]
filtered = filtered[filtered["Gap%"] >= min_gap]
filtered = filtered[filtered["Shs Float"] <= max_float]
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

# region ---- CALCOLI ENTRY / SL / TP / ATTIVAZIONE ----
filtered["SL_price"] = filtered["Open"] * (1 + param_sl/100)
filtered["TP_price"] = filtered["Open"] * (1 + param_tp/100)
filtered["Entry_price"] = filtered["Open"] * (1 + param_entry/100)

filtered["attivazione"] = (filtered["High_60m"] >= filtered["Entry_price"]).astype(int)

if mode == "90 minuti":
    # usiamo timeframes 30m, 60m, 90m
    timeframes_90m = [
        ("High_30m", "Low_30m"),
        ("High_60m", "Low_60m"),
        ("High_90m", "Low_90m")
    ]

    # inizializzo colonne
    filtered["SL"] = 0
    filtered["TP"] = 0
    filtered["TP_90m%"] = 0.0
    filtered["Outcome"] = "Hold"

    for idx, row in filtered.iterrows():
        if row["attivazione"] != 1:
            continue
        
        entry = row["Entry_price"]
        sl_price = row["SL_price"]
        tp_price = row["TP_price"]
        sl_hit = False
        tp_hit = False

        for high_col, low_col in timeframes_90m:
            high = row[high_col]
            low = row[low_col]

            # SHORT: SL se prezzo sale sopra SL_price
            if not sl_hit and high >= sl_price:
                filtered.at[idx, "SL"] = 1
                filtered.at[idx, "Outcome"] = "SL"
                sl_hit = True
                break  # fermiamo al primo evento

            # SHORT: TP se prezzo scende sotto TP_price
            if not tp_hit and low <= tp_price:
                filtered.at[idx, "TP"] = 1
                filtered.at[idx, "Outcome"] = "TP"
                tp_hit = True
                break

        # calcolo performance % in base a chi ha colpito
        close_price = row["Close_1100"] if filtered.at[idx, "TP"] == 0 else tp_price
        filtered.at[idx, "TP_90m%"] = ((close_price - entry) / entry * 100)
else:
    # modalità fino a chiusura: aggiungiamo anche 30 minuti al primo timeframe
    timeframes = [
        ("High_30m", "Low_30m"),
        ("High_60m", "Low_60m"),
        ("High_90m", "Low_90m"),
        ("High_120m", "Low_120m"),
        ("High_240m", "Low_240m"),
        ("High", "Low")  # fallback finale
    ]

    # inizializzo colonne
    filtered["SL"] = 0
    filtered["TP"] = 0
    filtered["TP_90m%"] = 0.0
    filtered["Outcome"] = "Hold"

    for idx, row in filtered.iterrows():
        if row["attivazione"] != 1:
            continue
        
        entry = row["Entry_price"]
        sl_price = row["SL_price"]
        tp_price = row["TP_price"]
        sl_hit = False
        tp_hit = False

        for high_col, low_col in timeframes:
            high = row[high_col]
            low = row[low_col]

            # SHORT: SL se prezzo sale sopra SL_price
            if not sl_hit and high >= sl_price:
                filtered.at[idx, "SL"] = 1
                filtered.at[idx, "Outcome"] = "SL"
                sl_hit = True
                break

            # SHORT: TP se prezzo scende sotto TP_price
            if not tp_hit and low <= tp_price:
                filtered.at[idx, "TP"] = 1
                filtered.at[idx, "Outcome"] = "TP"
                tp_hit = True
                break

        # calcolo performance % in base a chi ha colpito
        close_price = row["Close"] if filtered.at[idx, "TP"] == 0 else tp_price
        filtered.at[idx, "TP_90m%"] = ((close_price - entry) / entry * 100)



filtered["BE_price"] = filtered["TP_price"] * (1 + param_BE/100)


# Calcolo BEprofit
filtered["BEprofit"] = (
    (filtered["attivazione"] == 1) &
    (filtered["SL"] == 0) &
    (filtered["TP"] == 0) &
    (filtered["Low_90m"] <= filtered["TP_price"] * (1 + param_BE/100))
).astype(int)


# Calcolo TP_90m
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
tp_90m_green_avg = "-" if np.isnan(tp_90m_green_avg) else int(tp_90m_green_avg)
tp_90m_red_avg   = "-" if np.isnan(tp_90m_red_avg) else int(tp_90m_red_avg)


# Calcolo RR
RR = round((filtered["Entry_price"].iloc[0] - filtered["TP_price"].iloc[0]) / 
                 (filtered["SL_price"].iloc[0] - filtered["Entry_price"].iloc[0]), 2)

RR_be= round((filtered["Entry_price"].iloc[0] - filtered["BE_price"].iloc[0]) / 
                    (filtered["SL_price"].iloc[0] - filtered["Entry_price"].iloc[0]), 2)


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
    padding:5px; 
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
    <div style="{base_box_style}; display:flex; justify-content:center; gap:20px;">
        <!-- Primo mini-box RR -->
        <div style="display:flex; flex-direction:column; align-items:center;">
            <div style="{title_style}">RR</div>
            <div style="font-size:40px; font-weight:bold;">{RR}</div>
        </div>
        <!-- Secondo mini-box RR_be -->
        <div style="display:flex; flex-direction:column; align-items:center;">
            <div style="{title_style}">RR_be</div>
            <div style="font-size:32px; font-weight:bold; color:#CCCCCC;">{RR_be}</div>
        </div>
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

# region ---- FUNZIONE UNIFICATA PER LE SEZIONI A SCOMPARSA ----


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
            df["Vol5_vs_PM_%"] = (df["Volume_5m"] / df["VolumePM"]) * 100
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
            {"label": "Gap% medio", "value": gap_mean_str, "sub": f"Mediana: {gap_median_str}"},
            {"label": "Market Cap medio", "value": mc_mean_str, "sub": f"Mediana: {mc_median_str}"},
            {"label": "Shs Float medio", "value": shs_float_mean_str, "sub": f"Mediana: {shs_float_median_str}"},
            {"label": "Shs Out medio", "value": shs_out_mean_str, "sub": f"Mediana: {shs_out_median_str}"},
            {"label": "Spinta medio", "value": high_mean_str, "sub": f"Mediana: {high_median_str}"},
            {"label": "TimeHigh medio", "value": time_mean_formatted},
            {"label": "Open/PMH medio", "value": openVSpmh_mean_str, "sub": f"Mediana: {openVSpmh_median_str}"},
            {"label": "Vol medio", "value": volume_mean_str, "sub": f"Mediana: {volume_median_str}"},
            {"label": "VolPM medio", "value": volumePM_mean_str, "sub": f"Mediana: {volumePM_median_str}"},
            {"label": "Vol 30m medio", "value": volume30_mean_str, "sub": f"Mediana: {volume30_median_str}"},
            {"label": "Vol5m/PM", "value": vol5_vs_PM_mean_str, "sub": f"Mediana: {vol5_vs_PM_median_str}"},
            {"label": "Vol30m/PM", "value": vol30_vs_PM_mean_str, "sub": f"Mediana: {vol30_vs_PM_median_str}"}
        ]


        # --- Stile ---
        LABEL_STYLE = "font-size:14px; opacity:0.85;"
        VALUE_STYLE = "font-size:20px; font-weight:bold; margin-left: 8px"
        SUBVALUE_STYLE = "font-size:15px; font-weight:600; opacity:0.85; margin-top:0px;"

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

be_df = filtered[filtered["BEprofit"] == 1].copy()
show_kpi_section(be_df, "🟡 Break Even", "#705B15")

# endregion

# region ---- TABELLA ----

# Colonne da mostrare in tabella
cols_to_show = ["Date", "Ticker", "Gap%", "High_60m", "Low_60m",
                "High_90m", "Low_90m", "Close_1100", "Entry_price", "SL_price", "TP_price",
                "TP_90m%", "attivazione", "SL", "TP", "BEprofit"]


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

# region === EQUITY & DRAWDOWN SIMULATION ===

st.markdown("### 📈 Simulazione Equity & Drawdown")

# ---- INPUT PARAMETRI ----
col1, col2 = st.columns(2)
initial_capital = col1.number_input("💰 Capitale iniziale", value=3000.0, step=100.0)
risk_pct = col2.number_input("📉 % Rischio per trade", value=2.0, step=0.5)

# ---- COSTRUZIONE DATAFRAME ----
df_equity = filtered.copy()

# Considera solo i trade attivati
df_equity = df_equity[df_equity["attivazione"] == 1].copy()

# Evitiamo errori su colonne mancanti
for col in ["TP", "SL", "BEprofit", "TP_90m%", "Entry_price", "SL_price", "TP_price", "BE_price"]:
    if col not in df_equity.columns:
        st.warning(f"Manca la colonna '{col}' nel dataframe.")
        st.stop()

# endregion

# region ---- CALCOLO EQUITY REALE ----
capital = initial_capital
equity_values = []
drawdowns = []
profits = []
sizes = []

for i, row in df_equity.iterrows():
    # rischio in $
    risk_amount = initial_capital * (risk_pct / 100)

    # calcolo quantità (short)
    stop_dist = abs(row["SL_price"] - row["Entry_price"])
    if stop_dist == 0:
        continue
    size = risk_amount / stop_dist
    sizes.append(size)

    # calcolo profit/loss in base al tipo di trade
    if row["TP"] == 1:
        pnl = (row["Entry_price"] - row["TP_price"]) * size  # short profit
    elif row["SL"] == 1:
        pnl = (row["Entry_price"] - row["SL_price"]) * size  # short loss (negativo)
    elif row["BEprofit"] == 1:
        pnl = (row["Entry_price"] - row["BE_price"]) * size  # break-even piccolo guadagno
    else:
        val = row["TP_90m%"]
        pnl = 0
        if pd.notna(val):
            pnl = (-val / 100) * row["Entry_price"] * size  # short: negativo = gain

    # aggiorna capitale
    capital += pnl

    # registra equity e drawdown
    equity_values.append(capital)
    peak = max(equity_values)
    drawdown = (capital - peak) / peak * 100
    drawdowns.append(drawdown)
    profits.append(pnl)

# ---- ASSEMBLA DATAFRAME ----
df_equity["PnL_$"] = profits
df_equity["Equity"] = equity_values
df_equity["Drawdown_%"] = drawdowns
df_equity["Size"] = sizes


# ---- VALORI ----
ultima_equity = equity_values[-1] if equity_values else initial_capital
profit = ultima_equity - initial_capital
trade_count = len(df_equity)

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

# ---- BOX KPI ----

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




# ---- CALCOLO COLONNA ESITO ----
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