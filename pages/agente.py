import streamlit as st
import pandas as pd
import datetime
from google.oauth2.service_account import Credentials
import gspread
from gspread_dataframe import set_with_dataframe
from openai import OpenAI

# ======================================
# 🔐 CONFIGURAZIONE CREDENZIALI
# ======================================
creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
)
gc = gspread.authorize(creds)

# Nome del file Google Sheet dove salverai i risultati
SHEET_NAME = "analisi_agenteAI"

# ID della cartella condivisa su Google Drive (copialo dall’URL)
# Esempio: https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz
FOLDER_ID = "https://drive.google.com/drive/folders/1Kqb-ttIHsKMB3B92vOg0EawkAVgUOKrF"

# Funzione per aprire o creare il file nella cartella condivisa
def open_or_create_sheet(gc, sheet_name, folder_id):
    query = f"name='{sheet_name}' and '{folder_id}' in parents and trashed=false"
    files = gc.list_spreadsheet_files(query=query)
    if files:
        sh = gc.open_by_key(files[0]["id"])
    else:
        sh = gc.create(sheet_name, folder_id=folder_id)
        # opzionale: rendi il file accessibile in sola lettura (pubblico o solo a chi ha link)
        sh.share(None, perm_type='anyone', role='reader')
    return sh

# Crea o apri il foglio
sh = open_or_create_sheet(gc, SHEET_NAME, FOLDER_ID)

worksheet = sh.sheet1


# ======================================
# 🤖 CLIENT OPENAI (usa ChatGPT locale / API)
# ======================================
client = OpenAI()

# ======================================
# 🧩 INTERFACCIA STREAMLIT
# ======================================
st.title("🧠 Agente AI – Analisi News Small Cap NASDAQ")

st.markdown(
    "Inserisci un **ticker** e il **link della news**. L’agente analizzerà automaticamente la notizia, "
    "estrarrà i dati chiave e li salverà su Google Sheets."
)

with st.form("input_form"):
    ticker = st.text_input("Ticker (es. $GNS, $SOUN, $CXAI)", "").upper().strip()
    news_link = st.text_input("Link della news", "")
    note_utente = st.text_area("Note o contesto aggiuntivo (opzionale)", "")
    submitted = st.form_submit_button("🚀 Analizza News")

if submitted:
    if not ticker or not news_link:
        st.warning("⚠️ Inserisci sia il ticker che il link della news.")
    else:
        with st.spinner("Analisi in corso..."):
            prompt = f"""
            Analizza la seguente notizia riguardante il titolo {ticker} (NASDAQ small cap).
            Fornisci un riassunto sintetico e indica in modo chiaro:

            - 🎯 Argomento principale della notizia
            - 💡 Impatto potenziale sul titolo (Positivo / Negativo / Neutro)
            - 🧩 Tipologia della news (es. earnings, diluizione, partnership, FDA, ecc.)
            - 📈 Valutazione qualitativa complessiva (Alta / Media / Bassa rilevanza)

            Link della news: {news_link}

            Contesto aggiuntivo fornito dall’utente: {note_utente}
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sei un analista finanziario esperto in azioni small cap NASDAQ."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
            )

            analisi = response.choices[0].message.content

        # Mostra risultato visivo
        st.success("✅ Analisi completata")
        st.markdown("### 🧾 Risultato dell’analisi")
        st.markdown(analisi)

        # Salva su Google Sheet
        new_row = pd.DataFrame([{
            "Data": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Ticker": ticker,
            "Link News": news_link,
            "Analisi": analisi,
            "Note Utente": note_utente
        }])

        try:
            existing_df = pd.DataFrame(worksheet.get_all_records())
            df_updated = pd.concat([existing_df, new_row], ignore_index=True)
        except Exception:
            df_updated = new_row

        worksheet.clear()
        set_with_dataframe(worksheet, df_updated)

        st.info(f"📊 Analisi salvata su Google Sheet: **{SHEET_NAME}**")


# ======================================
# 📚 STORICO ANALISI
# ======================================
st.divider()
st.subheader("📅 Storico Analisi Recenti")

try:
    df = pd.DataFrame(worksheet.get_all_records())
    if len(df) > 0:
        st.dataframe(df.tail(10), use_container_width=True)
    else:
        st.write("Nessuna analisi presente.")
except Exception as e:
    st.warning(f"Errore nel caricamento del foglio: {e}")
