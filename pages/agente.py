import streamlit as st
import pandas as pd
from io import StringIO

st.set_page_config(page_title="Insider Analysis Compiler", layout="wide")
st.title("📋 Insider Trading — Text Compiler for ChatGPT-4")
st.markdown("Use this page to fill inputs and generate a ready-to-copy text block to paste into ChatGPT-4.")

with st.sidebar:
    st.header("Input options")
    ticker = st.text_input("Ticker (es. AAPL)")
    prezzo_attuale = st.text_input("Prezzo attuale USD (es. 145.23)")
    upload = st.file_uploader("Carica tabella (CSV / HTML) opzionale", type=["csv", "htm", "html"])
    paste_table = st.text_area("Oppure incolla qui la tabella (testo, CSV, o codice HTML)", height=200)
    generate_button = st.button("Genera testo pronto")

st.markdown("---")

col1, col2 = st.columns([1,1])
with col1:
    st.subheader("Anteprima tabella importata")
    parsed_table = None
    table_raw = ""
    if upload is not None:
        file_bytes = upload.read()
        try:
            # try csv first
            if upload.name.lower().endswith('.csv'):
                parsed_table = pd.read_csv(StringIO(file_bytes.decode('utf-8')))
            else:
                # try reading html tables
                parsed = pd.read_html(file_bytes.decode('utf-8'))
                if len(parsed) > 0:
                    parsed_table = parsed[0]
        except Exception as e:
            st.error(f"Errore parsing file: {e}")
    elif paste_table.strip() != "":
        table_raw = paste_table
        # attempt to parse as CSV or HTML for preview
        try:
            if "<table" in paste_table.lower():
                parsed = pd.read_html(paste_table)
                if len(parsed) > 0:
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
- Incolla la tabella OpenInsider (o il codice HTML della tabella) nel campo di testo, oppure carica un CSV/HTML.
- Clicca **Genera testo pronto** per ottenere il blocco formattato da copiare.
- Puoi scaricare il risultato con il bottone "Download" o copiarlo manualmente.
"""
    )

st.markdown("---")

if generate_button:
    # decide what to use for the table block
    if upload is not None:
        # prefer raw uploaded text if html, else recreate CSV
        if upload.name.lower().endswith('.csv'):
            table_block = parsed_table.to_csv(index=False)
        else:
            # try to show original uploaded bytes as string
            try:
                table_block = file_bytes.decode('utf-8')
            except Exception:
                table_block = parsed_table.to_html(index=False) if parsed_table is not None else upload.name
    elif paste_table.strip() != "":
        table_block = paste_table
    else:
        table_block = "<<INCOLLA QUI LA TABELLA OPENINSIDER O IL CODICE HTML DELLA TABELLA>>"

    # Build the template
    template = f"""📊 **Analisi insider trading sintetica per ticker**

ticker : {ticker or '<<INSERISCI TICKER>>'}  
prezzo_attuale : {prezzo_attuale or '<<INSERISCI PREZZO ATTUALE USD>>'}  
tabella :  
```\n{table_block}\n```

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

    st.subheader("Testo generato (pronto da copiare in ChatGPT-4)")
    st.code(template, language='markdown')

    # provide download
    st.download_button("Download .txt", template, file_name=f"insider_{ticker or 'TICKER'}.txt")

    # also show small copy-to-clipboard helper using JS (works when running as Streamlit app in browser)
    st.markdown("""
<button id="copy-btn">Copia negli appunti</button>
<script>
const btn = document.getElementById('copy-btn');
btn.addEventListener('click', async () => {
  const text = `"""""`;
});
</script>
""", unsafe_allow_html=True)

else:
    st.info("Completa i campi nella sidebar e clicca 'Genera testo pronto' quando sei pronto.")

st.markdown("---")
st.caption("Developed for quick compile of structured insider-analysis prompts — paste result into ChatGPT-4 for expanded analysis.")
