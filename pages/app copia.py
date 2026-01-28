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
            "Volume_adj": "Volume"
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
            "Ticker", "Date", "Gap%", "Open $","Close $",
            "% High", "% Low", "% Close", "Chiusura", "Volume"
        ]

        left_col, center_col, right_col = st.columns([1, 4, 3])

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
min_gap = st.sidebar.number_input("GAP minimo (%)", 0, 1000, 0)

col_mc1, col_mc2 = st.sidebar.columns(2)
mc_min = col_mc1.number_input("MC Min ($M)", 0, 2000, 0, step=10)
mc_max = col_mc2.number_input("MC Max ($M)", 0, 2000, 2000, step=10)

col_f1, col_f2 = st.sidebar.columns(2)
float_min = col_f1.number_input("Float MIN", 0, 1_000_000_000, 0, step=100_000)
float_max = col_f2.number_input("Float MAX", 0, 1_000_000_000, 5_000_000, step=100_000)

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

# -------------------------------------------------
# region KPI
# -------------------------------------------------
st.subheader("📊 KPI principali")

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

# --- Top box: I 3 KPI principali in un unico box giustificato ---
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
st.markdown(top_html, unsafe_allow_html=True)

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

st.markdown(container_html, unsafe_allow_html=True)

# endregion

# -------------------------------------------------
# TABELLA
# -------------------------------------------------
st.subheader("📋 Tabella di dettaglio")

filtered_sorted = filtered.sort_values("Date", ascending=False)

st.dataframe(
    filtered_sorted,
    use_container_width=True
)

st.caption(f"Record mostrati: {len(filtered_sorted)} su {len(df)}")