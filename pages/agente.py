
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
