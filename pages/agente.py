import streamlit as st
import textwrap
import urllib.parse

st.set_page_config(page_title="Insider Trading Compiler", layout="centered")
st.title("📋 Insider Trading — Text Compiler for ChatGPT-4")

with st.sidebar:
    st.header("Input dati")
    ticker = st.text_input("Ticker (es. PHIO)")
    prezzo_attuale = st.text_input("Prezzo attuale USD (es. 3.47)")
    tabella_input = st.text_area(
        "Incolla qui la tabella (testo, markdown o codice HTML)",
        height=200,
        placeholder="Incolla qui la tabella OpenInsider o il codice HTML..."
    )
    news_link = st.text_input("🔗 Link news (opzionale)")

    # Pulsante cerca su Finviz
    if ticker.strip():
        finviz_url = f"https://finviz.com/quote.ashx?t={urllib.parse.quote(ticker.strip())}"
        st.markdown(f"[🔍 Cerca su Finviz]({finviz_url})", unsafe_allow_html=True)

    generate_button = st.button("Genera testo pronto")

st.markdown ("inserire i parametri a lato per visualizzare il testo")

if generate_button:
    table_block = tabella_input.strip() or "<<INCOLLA QUI LA TABELLA OPENINSIDER O IL CODICE HTML>>"
    news_block = news_link.strip() or "<<INSERISCI LINK NEWS o lascia vuoto se deve essere ricercata>>"

    template = textwrap.dedent(f"""\
    📊 **Analisi insider trading sintetica per ticker**

    ticker : {ticker or '<<INSERISCI TICKER>>'}  
    prezzo_attuale : {prezzo_attuale or '<<INSERISCI PREZZO ATTUALE USD>>'}  
    tabella :  
    ```
    {table_block}
    ```

    ---

    🧮 **1. Prezzo medio ponderato per insider (solo acquisti “P – Purchase”)**

    Tabella:  
    Insider | Quantità totale | Valore totale ($) | Prezzo medio ponderato ($)  

    ---

    🎁 **2. Award (“A – Grant”) per anno**

    Tabella:  
    Anno | Totale award (RSU) | Data grant principale | Prezzo stimato alla data ($) | Valore stimato ($) | Data vendibilità stimata  

    ---

    📰 **3. Analisi della notizia correlata**

    News: {news_block}  

    Analizza la notizia in ottica di **impatto reale sul business** e distingui tra **catalizzatore concreto** e **pump speculativo**.  
    Valuta:
    - Presenza di **partner o nomi rilevanti**  
    - Presenza di **numeri o dati economici misurabili**  
    - Connessione diretta al **fatturato o pipeline operativa**  
    - Tono **promozionale o vago** → possibile notizia “aria fritta”  

    Concludi con una **valutazione sintetica**:  
    > ✅ Notizia concreta e positiva  
    > ⚠️ Notizia debole ma da monitorare  
    > 🚨 Pump speculativo / aria fritta  

    Se non è fornito alcun link, **ricerca autonomamente la notizia più recente e significativa sul ticker da fonti affidabili come Finviz, Yahoo Finance o MarketWatch**.

    ---

    📈 **4. Sintesi complessiva**

    Tabella:  
    Categoria | Totale azioni | Valore stimato ($) | Prezzo medio ($) | Vesting / vendibilità principale  

    ---

    📂 **5. Documenti recenti – offering, warrant, ATM**

    Tabella:  
    Tipo | Dettagli | Implicazione diluitiva  

    ---

    📌 **6. Conclusioni**

    Breve analisi qualitativa con opinione sul sentiment e sulla possibilità di vendita di azioni, considerando filing SEC, acquisti insider, award e eventuali notizie online recenti di pump, sell-off o eventi rilevanti.
    """)

    st.subheader("✅ Testo generato (pronto da copiare in ChatGPT-4)")
    st.code(template, language="markdown")
    st.download_button("📥 Download .txt", template, file_name=f"insider_{ticker or 'TICKER'}.txt")
