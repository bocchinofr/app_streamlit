# streamlit_app.py

import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import datetime
import altair as alt

st.set_page_config(page_title="Analisi Vendite Insider", layout="wide")
st.title("Analisi Probabilità Vendita Insider (US)")

# --- Input utente ---
ticker = st.text_input("Inserisci ticker (es. AAPL):")
pre_market_price = st.number_input("Prezzo pre-market ($):", min_value=0.0, format="%.2f")

# Funzione per ottenere il CIK da ticker
def get_cik(ticker):
    ticker = ticker.upper()
    url = "https://www.sec.gov/files/company_tickers.json"
    r = requests.get(url)
    data = r.json()
    for k in data:
        if data[k]["ticker"] == ticker:
            return str(data[k]["cik_str"]).zfill(10)
    return None

# Funzione per scaricare ultimi Form 4
def get_form4_filings(cik, count=10):
    base_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&owner=include&count={count}&output=atom"
    r = requests.get(base_url, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code != 200:
        return None
    root = ET.fromstring(r.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall("atom:entry", ns)
    filings = []
    for e in entries:
        title = e.find("atom:title", ns).text
        updated = e.find("atom:updated", ns).text
        link = e.find("atom:link", ns).attrib["href"]
        filings.append({"title": title, "updated": updated, "link": link})
    return filings

# Funzione euristica per calcolare probabilità
def calculate_probability(filings, pre_market_price):
    if not filings:
        return 0
    prob = 0
    for f in filings:
        title = f["title"].lower()
        if "sale" in title:
            prob += 15
        elif "grant" in title:
            prob += 10
        elif "purchase" in title:
            prob += 5
    # Normalizzazione
    prob = min(prob, 100)
    return prob

if st.button("Analizza"):
    if not ticker:
        st.warning("Inserisci un ticker valido!")
    else:
        st.info("Scaricando dati SEC...")
        cik = get_cik(ticker)
        if not cik:
            st.error("Ticker non trovato su SEC!")
        else:
            filings = get_form4_filings(cik)
            if not filings:
                st.warning("Nessun Form 4 recente trovato.")
            else:
                # Calcolo probabilità
                prob = calculate_probability(filings, pre_market_price)
                
                st.success(f"Probabilità vendita insider oggi: **{prob}%**")
                
                # Tabella
                df_filings = pd.DataFrame(filings)
                df_filings["updated"] = pd.to_datetime(df_filings["updated"])
                st.subheader("Ultimi Form 4")
                st.dataframe(df_filings[["updated", "title", "link"]].sort_values(by="updated", ascending=False))
                
                # Grafico numero transazioni per giorno
                df_filings['date'] = df_filings['updated'].dt.date
                chart = alt.Chart(df_filings).mark_bar().encode(
                    x='date:T',
                    y='count()',
                    tooltip=['date', 'count()']
                ).properties(
                    title="Numero di Form 4 pubblicati per giorno"
                )
                st.altair_chart(chart, use_container_width=True)
