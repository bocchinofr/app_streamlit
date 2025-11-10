import streamlit as st
import textwrap

st.set_page_config(page_title="Insider Trading Compiler", layout="wide")
st.title("📋 Insider Trading — Text Compiler for ChatGPT-4")
st.markdown("Compila i campi e genera il testo formattato da incollare in ChatGPT-4.")

with st.sidebar:
    st.header("Input dati")
    ticker = st.text_input("Ticker (es. PHIO)")
    prezzo_attuale = st.text_input("Prezzo attuale USD (es. 3.47)")
    tabella_input = st.text_area(
        "Incolla qui la tabella (testo, markdown o codice HTML)",
        height=250,
        placeholder="Incolla qui la tabella OpenInsider o il codice HTML corrispondente...",
    )
    generate_button = st.button("Genera testo pronto")

st.markdown("---")

if generate_button:
    table_block = tabella_input.strip() or "<<INCOLLA QUI LA TABELLA OPENINSIDER O IL CODICE HTML DELLA TABELLA>>"

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

    📈 **3. Sintesi complessiva**

    Tabella:  
    Categoria | Totale azioni | Valore stimato ($) | Prezzo medio ($) | Vesting / vendibilità principale  

    ---

    📂 **4. Documenti recenti – offering, warrant, ATM**

    Tabella:  
    Tipo | Dettagli | Implicazione diluitiva  

    ---

    📌 **Conclusioni**

    Breve analisi qualitativa con opinione sul sentiment e sulla possibilità di vendita di azioni, considerando filing SEC, acquisti insider, award e eventuali notizie online recenti di pump, sell-off o eventi rilevanti.
    """)

    st.subheader("✅ Testo generato (pronto da copiare in ChatGPT-4)")
    st.code(template, language="markdown")
    st.download_button("📥 Download .txt", template, file_name=f"insider_{ticker or 'TICKER'}.txt")

else:
    st.info("Inserisci i dati nella sidebar e clicca **Genera testo pronto** per ottenere il testo.")
