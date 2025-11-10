import streamlit as st
import pandas as pd
from io import StringIO

st.set_page_config(page_title="Insider Analysis Compiler", layout="wide")
st.title("📋 Insider Trading — Text Compiler for ChatGPT-4")
st.markdown("Usa questa pagina per compilare rapidamente un testo formattato da incollare in ChatGPT-4.")

with st.sidebar:
    st.header("Input")
    ticker = st.text_input("Ticker (es. AAPL)")
    prezzo_attuale = st.text_input("Prezzo attuale USD (es. 145.23)")
    upload = st.file_uploader("Carica tabella (CSV / HTML)", type=["csv", "htm", "html"])
    paste_table = st.text_area("Oppure incolla qui la tabella (testo, CSV o codice HTML)", height=200)
    generate_button = st.button("Genera testo pronto")

st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Anteprima tabella importata")
    parsed_table = None
    file_bytes = None

    if upload is not None:
        file_bytes = upload.read()
        try:
            if upload.name.lower().endswith(".csv"):
                parsed_table = pd.read_csv(StringIO(file_bytes.decode("utf-8")))
            else:
                parsed = pd.read_html(file_bytes.decode("utf-8"))
                if parsed:
                    parsed_table = parsed[0]
        except Exception as e:
            st.error(f"Errore nel parsing del file: {e}")

    elif paste_table.strip():
        try:
            if "<table" in paste_table.lower():
                parsed = pd.read_html(paste_table)
                if parsed:
                    parsed_table = parsed[0]
            else:
                parsed_table = pd.read_csv(StringIO(paste_table))
        except Exception:
            parsed_table = None

    if parsed_table is not None:
        st.dataframe(parsed_table)
    else:
        st.write("Nessuna tabella valida importata — verrà inserito il testo raw incollato nel campo `tabella` del template.")

with col2:
    st.subheader("Istruzioni rapide")
    st.markdown(
        """
- Inserisci **Ticker** e **Prezzo attuale** nella sidebar.
- Incolla o carica la tabella OpenInsider.
- Clicca **Genera testo pronto** per ottenere il blocco formattato.
- Puoi scaricarlo o copiarlo manualmente.
"""
    )

st.markdown("---")

if generate_button:
    # Usa la tabella grezza o quella caricata
    if upload is not None:
        if upload.name.lower().endswith(".csv"):
            table_block = parsed_table.to_csv(index=False)
        else:
            try:
                table_block = file_bytes.decode("utf-8")
            except Exception:
                table_block = parsed_table.to_html(index=False) if parsed_table is not None else upload.name
    elif paste_table.strip():
        table_block = paste_table
    else:
        table_block = "<<INCOLLA QUI LA TABELLA OPENINSIDER O IL CODICE HTML DELLA TABELLA>>"

    template = f"""
📊 **Analisi insider trading sintetica per ticker**

ticker : {ticker or '<<INSERISCI TICKER>>'}  
prezzo_attuale : {prezzo_attuale or '<<INSERISCI PREZZO ATTUALE USD>>'}  
tabella :  

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
"""

    st.subheader("Testo generato (pronto da copiare)")
    st.code(template, language="markdown")
    st.download_button("📥 Download .txt", template, file_name=f"insider_{ticker or 'TICKER'}.txt")

else:
    st.info("Compila i campi nella sidebar e clicca **Genera testo pronto** per creare il testo.")
