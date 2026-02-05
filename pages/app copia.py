import streamlit as st
import pandas as pd
import numpy as np
from dateutil import parser
import yfinance as yf

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="Dashboard Analisi Small Cap",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 Dashboard Analisi Small Cap")

# Carica il CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("theme.css")


# -------------------------------------------------
# INPUT TICKER
# -------------------------------------------------
ticker_input = st.text_input(
    "Inserisci un ticker (es. MARA, TSLA, AAPL)",
    placeholder="Lascia vuoto per usare solo i dati intraday"
).upper().strip()

# -------------------------------------------------
# region LOAD DATA
# -------------------------------------------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/15ev2l8av7iil_-HsXMZihKxV-B5MgTVO-LnK1y_f2-o/export?format=csv"
df = pd.read_csv(SHEET_URL)
df.columns = df.columns.str.strip()

# --- PULIZIA DATI ----
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

# --- PULIZIA COLONNE TIMEFRAME (Close / High / Low) ---
tf_cols = [
    c for c in df.columns
    if c.startswith(("%Close_", "Close_", "High_", "Low_"))
]

for col in tf_cols:
    df[col] = pd.to_numeric(
        df[col].astype(str)
        .str.replace(",", ".", regex=False).str.strip(),
        errors="coerce"
    )




# -----------------------------------------------
# CONTROLLO DATI 
# -----------------------------------------------

problemi_dati = False  # flag per sapere se ci sono problemi

# Mostra il titolo solo se ci sono problemi
if problemi_dati:
    st.markdown('<h3 style="font-size:16px; color:#FFFFFF;">🛠️ Controllo dati</h3>', unsafe_allow_html=True)

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

# endregion

# ------------------------------------------------------------
# region SEZIONE STORICA (solo se ticker valorizzato)
# ------------------------------------------------------------


if ticker_input:
    st.markdown(f"### 📊 Gap giornaliero per - {ticker_input}")

    col1, spacer, col2, spacer, col3 = st.columns([4, 1, 4, 1, 3])  # proporzioni: slider1=4, spazio=1, slider2=4

    with col1:
        # Slider GAP %
        gap_min, gap_max = st.slider(
            "GAP (%)",
            min_value=0,
            max_value=1000,
            value=(30, 1000)
        )

    with col2:
        # Slider Open $
        open_min, open_max = st.slider(
            "Open ($)",
            min_value=0,
            max_value=100,
            value=(2, 100)
        )
    with col3:
        metric_choice = st.radio(
            "Metrica heatmap",
            ["Conteggio gap", "Gap medio (%)"],
            index=0,
            horizontal=True  # rimuovi se la tua versione di Streamlit non supporta 'horizontal'
        )

    # Applico i filtri al dataframe storica
    # Copia df per lavoro storico
    historical_filtered = df.copy()

    if ticker_input:  # solo se l'utente ha inserito un ticker
        historical_filtered = historical_filtered[historical_filtered["Ticker"] == ticker_input].copy()


    historical_filtered = historical_filtered[
        (historical_filtered["GAP"] >= gap_min) &
        (historical_filtered["GAP"] <= gap_max) &
        (historical_filtered["OPEN"] >= open_min) &
        (historical_filtered["OPEN"] <= open_max)
    ]

    try:
        ticker_yf = yf.Ticker(ticker_input)
        df_yf = ticker_yf.history(period="4y", auto_adjust=False)
        df_yf.reset_index(inplace=True)
        df_yf = df_yf.sort_values("Date").reset_index(drop=True)

        # ===== SPLIT =====
        splits = ticker_yf.splits
        df_yf["factor"] = 1.0
        for date, ratio in splits.items():
            split_date = pd.to_datetime(date)
            df_yf.loc[df_yf["Date"] < split_date, "factor"] *= ratio

        # ===== PREZZI AGGIUSTATI =====
        for col in ["Open", "High", "Low", "Close"]:
            df_yf[f"{col}_adj"] = df_yf[col] * df_yf["factor"]

        # ===== VOLUME =====
        df_yf["Volume_adj"] = df_yf["Volume"]  # volume giornaliero reale

        # ===== GAP CORRETTO =====
        df_yf["Prev_Close"] = df_yf["Close"].shift(1) * df_yf["factor"]
        df_yf["Gap%"] = ((df_yf["Open_adj"] - df_yf["Prev_Close"]) / df_yf["Prev_Close"]) * 100
        df_yf["Gap%"] = df_yf["Gap%"].round(2)

        # ===== FILTRI SLIDER =====
        df_filtered = df_yf[
            (df_yf["Gap%"] >= gap_min) &
            (df_yf["Gap%"] <= gap_max) &
            (df_yf["Open_adj"] >= open_min) &
            (df_yf["Open_adj"] <= open_max)
        ].copy()

        # ===== CALCOLI AGGIUNTIVI =====
        df_filtered["% High"] = ((df_filtered["High_adj"] - df_filtered["Open_adj"]) / df_filtered["Open_adj"] * 100).round(2)
        df_filtered["% Low"] = ((df_filtered["Low_adj"] - df_filtered["Open_adj"]) / df_filtered["Open_adj"] * 100).round(2)
        df_filtered["% Close"] = ((df_filtered["Close_adj"] - df_filtered["Open_adj"]) / df_filtered["Open_adj"] * 100).round(2)

        # Colonna chiusura con pallino
        def chiusura_signal(row):
            if row["Close_adj"] > row["Open_adj"]:
                return "🟢"
            elif row["Close_adj"] < row["Open_adj"]:
                return "🔴"
            else:
                return "🟡"

        df_filtered["Chiusura"] = df_filtered.apply(chiusura_signal, axis=1)


        # ===== FORMAT FINALI =====
        df_filtered = df_filtered.copy()  # evitare warning di SettingWithCopy

        # Rinomina colonne solo se non esistono già
        rename_map = {
            "Open_adj": "Open $",
            "High_adj": "High $",
            "Low_adj": "Low $",
            "Close_adj": "Close $",
            "Volume_adj": "Volume",
            "Chiusura": "EoD"
        }

        for old_col, new_col in rename_map.items():
            if old_col in df_filtered.columns and new_col not in df_filtered.columns:
                df_filtered.rename(columns={old_col: new_col}, inplace=True)

        # Formatto date
        df_filtered["Date"] = df_filtered["Date"].dt.strftime("%d-%m-%Y")

        # Aggiungo ticker solo se non presente
        if "Ticker" not in df_filtered.columns:
            df_filtered["Ticker"] = ticker_input

        display_cols = [
            "Ticker", "Date", "Gap%", "Open $",
            "% High", "% Low", "% Close", "EoD", "Volume"
        ]

        left_col, center_col, right_col = st.columns([1, 4, 4])

        with left_col:
            st.text("🔁 Reverse split")
            split_info = []
            for date, ratio in splits.items():
                if ratio < 1:  # reverse split
                    split_info.append({
                        "Date": pd.to_datetime(date).strftime("%d-%m-%Y"),
                        "Reverse Split": f"1 : {int(round(1 / ratio))}"
                    })
            if split_info:
                for s in split_info:
                    st.markdown(f"- **{s['Date']}** → {s['Reverse Split']}")
            else:
                st.caption("Nessun reverse split rilevato")

        with center_col:
            st.dataframe(df_filtered[display_cols], width="stretch")
            st.caption(f"Record filtrati: {len(df_filtered)} su {len(df_yf)} totali")

        with right_col:
            # HEAT MAP  
            # ===== PREPARAZIONE DATI HEATMAP =====
            df_heat = df_yf.copy()

            df_heat["Year"] = df_heat["Date"].dt.year
            df_heat["Month"] = df_heat["Date"].dt.month

            if metric_choice == "Conteggio gap":
                heatmap_data = (
                    df_heat[df_heat["Gap%"] >= gap_min]
                    .groupby(["Year", "Month"])
                    .size()
                    .unstack(fill_value=0)
                )

            else:  # Gap medio
                heatmap_data = (
                    df_heat[df_heat["Gap%"] >= gap_min]
                    .groupby(["Year", "Month"])["Gap%"]
                    .mean()
                    .unstack()
                    .round(0)
                )

            # Ordino mesi da Gen a Dic
            heatmap_data = heatmap_data.reindex(columns=range(1, 13))

            month_names = {
                1: "Gen", 2: "Feb", 3: "Mar", 4: "Apr",
                5: "Mag", 6: "Giu", 7: "Lug", 8: "Ago",
                9: "Set", 10: "Ott", 11: "Nov", 12: "Dic"
            }

            heatmap_data.rename(columns=month_names, inplace=True)

            heatmap_display = heatmap_data.copy()
            heatmap_display = heatmap_display.astype("Int64")

            # Valori validi (>0)
            valid_values = heatmap_display[heatmap_display > 0]

            vmin = valid_values.min().min()
            vmax = valid_values.max().max()

            # 🔑 CASO LIMITE: se tutti i valori sono uguali (es. solo 1)
            if pd.isna(vmin) or vmin == vmax:
                vmax = vmin + 1

            st.dataframe(
                heatmap_display.style
                    # maschero None e 0 → restano bianchi
                    .background_gradient(
                        cmap="Greens",
                        axis=None,
                        vmin=vmin,
                        vmax=vmax
                    )
                    .apply(
                        lambda x: ["background-color: transparent" if (pd.isna(v) or v == 0) else "" for v in x],
                        axis=1
                    ),
                width="stretch"
            )
    except Exception as e:
        st.error(f"Errore nel recupero dati Yahoo Finance: {e}")
# endregion

# -------------------------------------------------
# region SIDEBAR FILTRI
# -------------------------------------------------
st.sidebar.header("🔍 Filtri")

date_range = st.sidebar.date_input("Intervallo date", [])
min_gap = st.sidebar.number_input("GAP minimo (%)", 0, 1000, 40)

col_mc1, col_mc2 = st.sidebar.columns(2)
mc_min = col_mc1.number_input("MC Min ($M)", 0, 2000, 0, step=10)
mc_max = col_mc2.number_input("MC Max ($M)", 0, 2000, 2000, step=10)

col_f1, col_f2 = st.sidebar.columns(2)
float_min = col_f1.number_input("Float MIN", 0, 1_000_000_000, 0, step=100_000)
float_max = col_f2.number_input("Float MAX", 0, 1_000_000_000, 50_000_000, step=100_000)

min_open_pmh = st.sidebar.number_input("%Open_PMH minimo", -100, 100, -100)

col_o1, col_o2 = st.sidebar.columns(2)
open_min = col_o1.number_input("Open MIN", 0.0, 100.0, 1.0, step=0.1)
open_max = col_o2.number_input("Open MAX", 0.0, 100.0, 100.0, step=0.1)

# -------------------------------------------------
# APPLY FILTERS
# -------------------------------------------------
filtered = df.copy()

if ticker_input:
    filtered = filtered[filtered["Ticker"] == ticker_input]

filtered = filtered[
    (filtered["GAP"] >= min_gap) &
    (filtered["%Open_PMH"] >= min_open_pmh) &
    (filtered["Float"] >= float_min) &
    (filtered["Float"] <= float_max) &
    (filtered["OPEN"] >= open_min) &
    (filtered["OPEN"] <= open_max)
]

if len(date_range) == 2:
    start, end = date_range
    filtered = filtered[(filtered["Date"] >= start) & (filtered["Date"] <= end)]

filtered = filtered[
    (filtered["Market Cap"] >= mc_min * 1_000_000) &
    (filtered["Market Cap"] <= mc_max * 1_000_000)
]

# endregion

# -------------------------------
# region KPI CARD TESTUALE
# -------------------------------

def kpi_card_textual(title, total, red, green, suffix, show_delta=True):
    # formattazione valori
    def fmt(x):
        try:
            return f"{x:.1f}"
        except (ValueError, TypeError):
            return str(x)

    # delta solo se show_delta=True e valori numerici
    delta_html = ""
    if show_delta:
        try:
            delta = float(red) - float(green)
            delta_sign = "+" if delta > 0 else ""
            delta_color = "#2ecc71" if delta < 0 else ("#e74c3c" if delta > 0 else "#f1c40f")
            delta_html = f'<div class="kpi-delta" style="color:{delta_color};">Δ {delta_sign}{delta:.1f}{suffix}</div>'
        except (ValueError, TypeError):
            delta_html = '<div class="kpi-delta">&nbsp;</div>'  # div vuoto ma mantiene spazio
    else:
        delta_html = '<div class="kpi-delta">&nbsp;</div>'      # div vuoto, invisibile ma occupa altezza


    html = f"""
    <div class="kpi-card">
        <div class="kpi-header">
            <div class="kpi-title">{title}</div>
            <div class="kpi-total">{fmt(total)}{suffix}</div>
        </div>
        <div class="kpi-split">
            <div class="red">Red: {fmt(red)}{suffix}</div>
            <div class="green">Green: {fmt(green)}{suffix}</div>
        </div>
        {delta_html}
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)

# endregion

# -------------------------------------------------
# region KPI
# -------------------------------------------------

total = len(filtered)
gap_mean = filtered["GAP"].mean() if total else 0
gap_median = filtered["GAP"].median() if total else 0
red_close = (filtered["Chiusura"] == "RED").mean() * 100 if total else 0

# --- Medie per red e green per GAP (aggiunte) ---
gap_red = (
    filtered.loc[filtered["Chiusura"] == "RED", "GAP"].mean()
    if not filtered.loc[filtered["Chiusura"] == "RED"].empty
    else 0
)
gap_green = (
    filtered.loc[filtered["Chiusura"] == "GREEN", "GAP"].mean()
    if not filtered.loc[filtered["Chiusura"] == "GREEN"].empty
    else 0
)
# Medie per red e green per OPENvsPMH
open_pmh_red = (
    filtered.loc[filtered["Chiusura"] == "RED", "%Open_PMH"].mean()
    if not filtered.loc[filtered["Chiusura"] == "RED"].empty
    else 0
)
open_pmh_green = (
    filtered.loc[filtered["Chiusura"] == "GREEN", "%Open_PMH"].mean()
    if not filtered.loc[filtered["Chiusura"] == "GREEN"].empty
    else 0
)

# Medie per red e green per PMbreak
pmbreak_red = (
    filtered.loc[filtered["Chiusura"] == "RED", "break"].mean()*100
    if not filtered.loc[filtered["Chiusura"] == "RED"].empty
    else 0
)
pmbreak_green = (
    filtered.loc[filtered["Chiusura"] == "GREEN", "break"].mean()*100
    if not filtered.loc[filtered["Chiusura"] == "GREEN"].empty
    else 0
)

# Medie per red e green per Spinta
spinta_red = (
    filtered.loc[filtered["Chiusura"] == "RED", "%OH"].mean()
    if not filtered.loc[filtered["Chiusura"] == "RED"].empty
    else 0
)
spinta_green = (
    filtered.loc[filtered["Chiusura"] == "GREEN", "%OH"].mean()
    if not filtered.loc[filtered["Chiusura"] == "GREEN"].empty
    else 0
)

# Medie per red e green per minimo 

low_red = (
    filtered.loc[filtered["Chiusura"] == "RED", "%OL"].mean()
    if not filtered.loc[filtered["Chiusura"] == "RED"].empty
    else 0
)
low_green = (
    filtered.loc[filtered["Chiusura"] == "GREEN", "%OL"].mean()
    if not filtered.loc[filtered["Chiusura"] == "GREEN"].empty
    else 0
)

# ---- ORARIO HIGH: MEDIA, MEDIANA, FILTRI RED/GREEN ----

def orario_to_minuti(ora_str):
    """Converte '9:31' -> minuti totali (es. 571)"""
    try:
        h, m = map(int, ora_str.split(":"))
        return h * 60 + m
    except:
        return np.nan

def minuti_to_orario(minuti):
    """Converte minuti -> stringa 'HH:MM'"""
    if np.isnan(minuti):
        return "-"
    h = int(minuti // 60)
    m = int(round(minuti % 60))
    return f"{h:02d}:{m:02d}"

# Filtra solo valori validi
orari_validi = df["Orario High"].dropna().apply(orario_to_minuti).dropna()

# Media e mediana globali
media_minuti = orari_validi.mean() if not orari_validi.empty else np.nan
mediana_minuti = orari_validi.median() if not orari_validi.empty else np.nan

media_orario_high = minuti_to_orario(media_minuti)
mediana_orario_high = minuti_to_orario(mediana_minuti)

# --- Filtri per chiusure RED / GREEN ---
red = df[df["Chiusura"] == "RED"]["Orario High"].dropna().apply(orario_to_minuti)
green = df[df["Chiusura"] == "GREEN"]["Orario High"].dropna().apply(orario_to_minuti)

mediaorario_red = minuti_to_orario(red.mean()) if not red.empty else "-"
mediaorario_green = minuti_to_orario(green.mean()) if not green.empty else "-"

# ----------------------------------------------------------------
# --- Top box: I 3 KPI principali in un unico box giustificato ---
# ----------------------------------------------------------------

#st.subheader("📊 KPI principali")

top_html = f"""
<div class='kpi-top-box'>
  <div class='kpi-top'>
    <div class='top-kpi'>
      <div class='top-kpi-value'>{total}</div>
      <div class='top-kpi-label'>Totale record</div>
    </div>
    <div class='top-kpi'>
      <div class='top-kpi-value'>{red_close:.0f}%</div>
      <div class='top-kpi-label'>Chiusure RED</div>
    </div>
    <div class='top-kpi'>
      <div class='top-kpi-value'>{gap_mean:.0f}%</div>
      <div class='top-kpi-label'>GAP medio</div>
    </div>
  </div>
</div>
"""
#st.markdown(top_html, unsafe_allow_html=True)

# Lista dei KPI (label, value, optional color)
kpi_rows = [
    ("GAP - massimo", f"{filtered['GAP'].max():.0f}%", "green"),
    ("GAP - mediana", f"{gap_median:.0f}%", None),
    ("GAP medio", (f"{gap_red:.0f}%", f"{gap_green:.0f}%", f"{gap_mean:.0f}%"), "multi"),
    ("Open / PMH medio", (f"{filtered['%Open_PMH'].mean():.0f}%", f"{open_pmh_green:.0f}%", f"{open_pmh_red:.0f}%"), "multi"),
    ("Open / PMH mediana", f"{filtered['%Open_PMH'].median():.0f}%", None),
    ("Float medio", f"{filtered['Float'].mean():,.0f}", None),
    ("Market Cap medio", f"{filtered['Market Cap'].mean() / 1_000_000:.0f}M", None),
    ("Spinta media",(f"{filtered['%OH'].mean():.0f}%", f"{spinta_green:.0f}%", f"{spinta_red:.0f}%"), "multi"),
    ("Minimo medio",(f"{filtered['%OL'].mean():.0f}%", f"{low_green:.0f}%", f"{low_red:.0f}%"), "multi"),
    ("Break medio", (f"{filtered['break'].mean() * 100:.0f}%",f"{pmbreak_green:.0f}%", f"{pmbreak_red:.0f}%"), "multi"),
    ("Orario High medio",(f"{media_orario_high}", f"{mediaorario_green}", f"{mediaorario_red}"), "multi"),
]


# Divido i KPI in due colonne/box
n = len(kpi_rows)
mid = (n + 1) // 2
left_rows = kpi_rows[:mid]
right_rows = kpi_rows[mid:]

# Funzione render che supporta anche valori multipli (tuple/list) e riusa le classi value-highlight-*
def render_rows_html(rows):
    html = ""
    for label, value, color in rows:
        if isinstance(value, (list, tuple)):
            # ordina: (red, green, totale)
            red_val, green_val, total_val = value
            # testi dei tooltip (personalizzali a piacere)
            red_title = "Valore sui record con chiusura RED"
            green_title = "Valore sui record con chiusura GREEN"
            total_title = "Valoer su tutti i record filtrati"
            value_html = (
                "<div class='kpi-multi'>"
                f"<span class='value-highlight-red' title='{red_title}'>{red_val}</span>"
                f"<span class='value-highlight-green' title='{green_title}'>{green_val}</span>"
                f"<span class='value-highlight' title='{total_title}'>{total_val}</span>"
                "</div>"
            )
        else:
            highlight_cls = "value-highlight-green" if color == "green" else ("value-highlight-red" if color == "red" else "")
            if highlight_cls:
                value_html = f"<span class='{highlight_cls}'>{value}</span>"
            else:
                value_html = f"{value}"
        html += f"<div class='kpi-row'><div class='kpi-label'>{label}</div><div class='kpi-value'>{value_html}</div></div>"
    return html

left_html = render_rows_html(left_rows)
right_html = render_rows_html(right_rows)

container_html = f"""
<div class='kpi-container'>
  <div class='kpi-box left'>
    {left_html}
  </div>
  <div class='kpi-box right'>
    {right_html}
  </div>
</div>
"""

#st.markdown(container_html, unsafe_allow_html=True)


# Creo due colonne principali: sinistra KPI, destra grafico
col_kpi, col_chart = st.columns([3, 2])  # proporzione: KPI 2/5, grafico 3/5

with col_kpi:
    st.subheader("📊 KPI principali")

    # Top box (totale, chiusure RED, GAP medio)
    st.markdown(top_html, unsafe_allow_html=True)

    # Lista dettagliata dei KPI
    st.markdown(container_html, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("🔬 Test nuova card")

    # 1️⃣ Lista KPI
    kpi_list = [
        {"title": "GAP Medio", "total": gap_mean, "red": gap_red, "green": gap_green, "suffix": "%"},
        {"title": "Open / PMH medio", "total": filtered['%Open_PMH'].mean(), "red": open_pmh_red, "green": open_pmh_green, "suffix": "%"},
        {"title": "Break medio", "total": filtered['break'].mean()*100, "red": pmbreak_red, "green": pmbreak_green, "suffix": "%"},
        {"title": "Spinta media", "total": filtered['%OH'].mean(), "red": spinta_red, "green": spinta_green, "suffix": "%"},
        {"title": "Minimo medio", "total": filtered['%OL'].mean(), "red": low_red, "green": low_green, "suffix": "%"},
        {"title": "Orario High medio", "total": media_orario_high, "red": mediaorario_red, "green": mediaorario_green, "suffix": "", "show_delta": False}
    ]

    # 2️⃣ Creo 2 colonne
    col1, col2 = st.columns(2)

    # 3️⃣ Ciclo e metto le card nelle colonne
    for i, kpi in enumerate(kpi_list):
        col = col1 if i % 2 == 0 else col2  # alterna le colonne
        with col:
            kpi_card_textual(
                title=kpi["title"],
                total=kpi["total"],
                red=kpi["red"],
                green=kpi["green"],
                suffix=kpi.get("suffix"),
                show_delta=kpi.get("show_delta", True)  # <- importante
            )





with col_chart:
    # --- Sezione grafico Close vs Open ---
    import plotly.graph_objects as go

    # --- colonne disponibili ---
    timeframes = [
        "1m","5m","15m","30m","45m","60m","90m","120m","240m"
    ]

    close_cols = [f"%Close_{tf}" for tf in timeframes if f"%Close_{tf}" in filtered.columns]

    if close_cols and not filtered.empty:
        mean_values = (
            filtered[close_cols]
            .mean()
            .rename(lambda x: x.replace("%Close_", ""))
            .reindex(timeframes)
        )

        df_plot = mean_values.reset_index()
        df_plot.columns = ["Timeframe", "Mean_pct"]

        df_plot["Color"] = df_plot["Mean_pct"].apply(
            lambda x: "#2ecc71" if x >= 0 else "#e74c3c"
        )

        fig = go.Figure()
        fig.add_bar(
            x=df_plot["Mean_pct"],
            y=df_plot["Timeframe"],
            orientation="h",
            marker_color=df_plot["Color"],
            text=df_plot["Mean_pct"].round(2),
            textposition="outside"
        )

        fig.add_vline(
            x=0,
            line_width=2,
            line_dash="dash",
            line_color="white"
        )

        fig.update_layout(
            title="Variazione media % del Close vs Open",
            xaxis_title="Variazione % vs Open",
            yaxis_title="Timeframe",
            yaxis=dict(categoryorder="array", categoryarray=timeframes),
            template="plotly_dark",
            height=500,
            margin=dict(l=60, r=40, t=60, b=40),
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nessun dato disponibile per il grafico Close vs Open.")













# endregion

# -------------------------------------------------
# region TABELLA
# -------------------------------------------------

st.markdown('<h3 style="font-size:16px; color:#FFFFFF;">📋 Tabella di dettaglio</h3>', unsafe_allow_html=True)

cols_to_drop = [c for c in filtered.columns if "high_v1" in c.lower()]
if cols_to_drop:
    filtered = filtered.drop(columns=cols_to_drop)

filtered_sorted = filtered.sort_values("Date", ascending=False).reset_index(drop=True)

if "Chiusura" in filtered_sorted.columns:
    filtered_sorted["Chiusura"] = filtered_sorted["Chiusura"].replace({
        "RED": "🔴 RED",
        "GREEN": "🟢 GREEN"
    })

def to_millions(x):
    try:
        return f"{x/1_000_000:.2f} M"
    except:
        return "-"

if "Shared Outstanding" in filtered_sorted.columns:
    filtered_sorted["Shared Outstanding"] = filtered_sorted["Shared Outstanding"].apply(to_millions)

if "Market Cap" in filtered_sorted.columns:
    filtered_sorted["Market Cap"] = filtered_sorted["Market Cap"].apply(to_millions)



# --- RIMOZIONE SIMBOLO % NELLA TABELLA PER LE COLONNE PERCENTUALI ---
percent_cols_display = [
    "%Open_PMH", "%OH", "%OL",
    "%OH_30m", "%OL_30m",
    "%OH_1h", "%OL_1h"
]

for col in percent_cols_display:
    if col in filtered_sorted.columns:
        filtered_sorted[col] = pd.to_numeric(
            filtered_sorted[col]
                .astype(str)
                .str.replace("%", "")
                .str.replace(",", ".")   # <<< AGGIUNTO!
                .str.strip(),
            errors="coerce"
        )


for col in percent_cols_display:
    if col in filtered_sorted.columns:
        filtered_sorted[col] = filtered_sorted[col].apply(
            lambda x: f"{x:.0f}" if pd.notna(x) else "-"
        )


st.dataframe(filtered_sorted, use_container_width=True)
st.caption(f"Sto mostrando {len(filtered_sorted)} record filtrati su {len(df)} totali.")



# endregion