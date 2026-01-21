import os
import streamlit as st
import pandas as pd
import numpy as np
from dateutil import parser
import numpy as np
import yfinance as yf

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Usa il file theme.css
local_css("theme.css")  # o "assets/theme.css" se lo metti in una cartella

if "show_filters" not in st.session_state:
    st.session_state.show_filters = False


# ---- CONFIGURAZIONE ----
st.set_page_config(page_title="Dashboard Analisi", layout="wide", initial_sidebar_state="expanded")
st.title("📈 Dashboard Analisi Small Cap")

ticker_input = st.text_input(
    "Inserisci un ticker (es. MARA, TSLA, AAPL)",
    placeholder="Lascia vuoto per usare solo i dati intraday"
).upper().strip()

# ---- CARICAMENTO DATI ----
SHEET_URL = "https://docs.google.com/spreadsheets/d/15ev2l8av7iil_-HsXMZihKxV-B5MgTVO-LnK1y_f2-o/export?format=csv"
df = pd.read_csv(SHEET_URL)

# region ---- PULIZIA DATI ----
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
 
# endregion

# region ---- CONTROLLO DATI ----

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


# ---- SLIDER SEZIONE STORICA (solo se ticker valorizzato) ----
if ticker_input:
    st.markdown(f"### 📊 Gap giornaliero per - {ticker_input}")

    col1, spacer, col2 = st.columns([4, 1, 4])  # proporzioni: slider1=4, spazio=1, slider2=4

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

    st.write(f"Record filtrati: {len(historical_filtered)}")

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
            "Ticker", "Date", "Gap%", "Open $", "High $", "Low $", "Close $",
            "% High", "% Low", "% Close", "Chiusura", "Volume"
        ]

        left_col, right_col = st.columns([1, 4])
        with left_col:
            st.markdown("### 🔁 Reverse split")
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

        with right_col:
            st.dataframe(df_filtered[display_cols], width="stretch")
            st.caption(f"Record filtrati: {len(df_filtered)} su {len(df_yf)} totali")

            

        # HEAT MAP  
        st.markdown("### 🔥 Heatmap gap per anno / mese")

        metric_choice = st.selectbox(
            "Metrica heatmap",
            ["Conteggio gap", "Gap medio (%)"]
        )
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








# region ---- FILTRI ----

with st.sidebar:

    # ICONA FILTRI (sempre visibile)
    if st.button("🔍", help="Mostra / nascondi filtri"):
        st.session_state.show_filters = not st.session_state.show_filters

    st.markdown("---")

    # FILTRI VERI (collassabili)
    if st.session_state.show_filters:
        st.markdown("### Filtri")

        date_range = st.date_input("Intervallo date", [])
        min_gap = st.number_input("GAP minimo (%)", 0, 1000, 0)

        # ====== MARKET CAP: DUE BOX (IN MILIONI) ======
        # Valori fissi di default in Milioni
        default_mc_min_M = 0
        default_mc_max_M = 2000

        col_mc_min, col_mc_max = st.columns(2)

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

        # filtro flottante
        col_float_min, col_float_max = st.columns(2)

        float_min = col_float_min.number_input(
            "Float MIN", 
            value=0, 
            step=100000,
            min_value=0,
            max_value=1000000000,
            help="Valore minimo di Flottante"

        )

        float_max = col_float_max.number_input(
            "Float MAX", 
            value=5000000, 
            step=100000,
            min_value=0,
            max_value=1000000000,
            help="Valore massimo di Flottante"

        )

        min_open_pmh = st.number_input("%Open_PMH minimo", -100, 100, -100)

        # filtro OPEN price
        col_open_min, col_open_max = st.columns(2)

        open_min = col_open_min.number_input(
            "Open MIN", 
            value=1.0, 
            step=0.1,
            min_value=0.0,
            max_value=100.0,
            help="Valore minimo di Open rispetto a PMH in %"

        )

        open_max = col_open_max.number_input(
            "Open MAX", 
            value=100.0, 
            step=0.1,
            min_value=0.0,
            max_value=100.0,
            help="Valore massimo di Open rispetto a PMH in %"

        )





filtered = df.copy()
if ticker_input:
    filtered = filtered[filtered["Ticker"] == ticker_input]
if ticker_input and ticker_input not in df["Ticker"].unique():
    st.warning(f"⚠️ Il ticker {ticker_input} non è presente nei dati intraday.")

filtered = filtered[(filtered["GAP"] >= min_gap)]
filtered = filtered[(filtered["%Open_PMH"] >= min_open_pmh)]

filtered = filtered[
    (filtered["Float"] >= float_min) &
    (filtered["Float"] <= float_max)
]

filtered = filtered[
    (filtered["OPEN"] >= open_min) &
    (filtered["OPEN"] <= open_max)
]

if len(date_range) == 2:
    start, end = date_range
    filtered = filtered[(filtered["Date"] >= start) & (filtered["Date"] <= end)]

filtered = filtered[
    (filtered["Market Cap"] >= marketcap_min) &
    (filtered["Market Cap"] <= marketcap_max)
]

# ---- DATE FILTRATE (con tema scuro) ----
if not filtered.empty:
    min_date = filtered["Date"].min()
    max_date = filtered["Date"].max()
    if pd.notna(min_date) and pd.notna(max_date):
        st.markdown(
            f"""
            <div style='font-size:16px; font-weight:400; margin-bottom:15px; color:#FFFFFF;'>
                📅 Dati filtrati dal 
                <span style='font-size:20px; color:#1E90FF; font-weight:bold;'>{min_date.strftime('%d-%m-%Y')}</span> 
                al 
                <span style='font-size:20px; color:#1E90FF; font-weight:bold;'>{max_date.strftime('%d-%m-%Y')}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.info("⚠️ Nessun dato disponibile dopo i filtri.")

# endregion

# region ---- KPI BOX ----
total = len(filtered)
red_close = np.mean(filtered["Chiusura"].eq("RED")) * 100 if total > 0 else 0
gap_mean = filtered["GAP"].mean() if total > 0 else 0
gap_median = filtered["GAP"].median() if total > 0 else 0
open_pmh_mean = filtered["%Open_PMH"].mean() if total > 0 else 0
open_pmh_median = filtered["%Open_PMH"].median() if total > 0 else 0
spinta_mean = filtered["%OH"].mean() if total > 0 else 0
spinta_median = filtered["%OH"].median() if total > 0 else 0
pmbreak = filtered["break"].mean() *100 if total > 0 else 0
low_mean = filtered["%OL"].mean() if total > 0 else 0
low_median = filtered["%OL"].median() if total > 0 else 0

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

# Medie per red e green per GAP
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

# endregion

# region ---- KPI BOX  ----

# ---- KPI BOX COMPATTO ----
st.markdown("### 📊 KPI principali")

# Primo livello: due box principali affiancati
col1, col2 = st.columns(2)

with col1:
    st.metric("Totale titoli", total)

with col2:
    st.metric("GAP medio (%)", f"{gap_mean:.0f}%")

# Secondo livello: elenco verticale delle altre metriche
st.markdown("### Altre metriche")

# Lista delle metriche secondarie
other_metrics = {
    "Chiusura RED (%)": f"{red_close:.0f}%",
    "Mediana GAP (%)": f"{gap_median:.0f}%",
    "Open vs PMH medio (%)": f"{open_pmh_mean:.0f}%",
    "Mediana Open vs PMH (%)": f"{open_pmh_median:.0f}%",
    "Orario High medio": media_orario_high,
    "Mediana Orario High": mediana_orario_high,
    "%PMbreak medio": f"{pmbreak:.0f}%",
    "Spinta media (%)": f"{spinta_mean:.0f}%",
    "Low medio (%)": f"{low_mean:.0f}%"
}

# Visualizzazione a due colonne con evidenziazione selettiva
for label, value in other_metrics.items():
    left_col, right_col = st.columns([2,1])  # titolo più largo
    with left_col:
        st.write(f"**{label}**")
    with right_col:
        # Applichiamo colore solo ad alcune metriche
        if label == "Chiusura RED (%)":
            st.markdown(f'<div class="value-highlight-red">{value}</div>', unsafe_allow_html=True)
        elif label == "Spinta media (%)":
            st.markdown(f'<div class="value-highlight-green">{value}</div>', unsafe_allow_html=True)
        else:
            st.write(f"{value}")


# endregion


# ---- TAB E TABELLA ----
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
    "%OH_10-11", "%OL_10-11"
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
