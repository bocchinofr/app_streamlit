import streamlit as st
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# -------------------------------
# 🔐 CONFIGURAZIONE
# -------------------------------

st.set_page_config(page_title="Analizzatore News Small Cap", page_icon="📊", layout="wide")
st.title("📊 Agente AI")

# Imposta chiavi (usa .streamlit/secrets.toml in produzione)
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
GOOGLE_SHEET_URL = st.secrets["GOOGLE_SHEET_URL"]

# Connessione a OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Connessione a Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_url(GOOGLE_SHEET_URL).sheet1

# -------------------------------
# 🧠 INTERFACCIA STREAMLIT
# -------------------------------

st.title("📊 Analizzatore News Small Cap NASDAQ")
st.markdown("Inserisci il **ticker** e il **link della notizia** per generare un’analisi strutturata automatica.")

col1, col2 = st.columns(2)
ticker = col1.text_input("Ticker", placeholder="es. KITT")
news_url = col2.text_input("Link della notizia", placeholder="https://finviz.com/news/...")

if st.button("🔍 Analizza notizia"):
    if not ticker or not news_url:
        st.warning("⚠️ Inserisci sia il ticker che il link della notizia.")
    else:
        with st.spinner("Analisi in corso... ⏳"):
            prompt = f"""
            Analizza la notizia relativa a {ticker}, disponibile al link seguente:
            {news_url}

            Fornisci una risposta in italiano e con la seguente struttura chiara:

            1️⃣ **Score totale e classificazione** (es. 6/15 - DUBBIA)
            2️⃣ **Dettagli Notizia** (Data/Ora, Fonte, Link, Freschezza)
            3️⃣ **Dati chiave** (riassunto sintetico dei numeri e delle informazioni principali)
            4️⃣ **Elementi sostanziali identificati**
            5️⃣ **Rischi principali**
            6️⃣ **Impatto atteso** (specifico per small cap Nasdaq)
            7️⃣ **Verdetto finale** (valutazione complessiva e tono della notizia)
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )

            output = response.choices[0].message.content

        # Mostra il risultato a schermo
        st.success("✅ Analisi completata!")
        st.markdown("### 📋 Risultato dell’analisi")
        st.markdown(output)

        # Salva su Google Sheet
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, ticker, news_url, output]
        sheet.append_row(row)
        st.info("📁 Analisi salvata su Google Sheet con successo!")

        # Mostra anche un estratto breve
        with st.expander("👁️ Anteprima sintetica"):
            st.markdown(output.split("\n")[0])  # prima riga come riassunto
