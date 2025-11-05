import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup

st.title("📈 Analisi Insider (OpenInsider)")

ticker = st.text_input("Inserisci ticker (es. TSLA, NVDA, AAPL):", "").upper()

def get_openinsider_data(ticker):
    url = f"https://openinsider.com/screener?s={ticker}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        st.error(f"Errore HTTP {response.status_code} durante la richiesta.")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"class": "tinytable"})

    if not table:
        st.warning("Nessuna tabella trovata per questo ticker.")
        return None

    rows = []
    for tr in table.find_all("tr")[1:]:  # salta intestazione
        cols = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cols) >= 10:
            rows.append(cols[:10])  # prendi solo le prime 10 colonne principali

    df = pd.DataFrame(rows, columns=[
        "Filing Date", "Trade Date", "Ticker", "Company Name", "Insider Name",
        "Title", "Trade Type", "Price", "Qty", "Owned"
    ])
    return df

if ticker:
    with st.spinner("Scaricando dati insider..."):
        df_insider = get_openinsider_data(ticker)
        if df_insider is not None and not df_insider.empty:
            st.success(f"Trovate {len(df_insider)} operazioni insider recenti per {ticker}")
            st.dataframe(df_insider)
        else:
            st.warning("Nessuna operazione insider recente trovata.")
