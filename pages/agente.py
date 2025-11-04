import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(page_title="Strategia Intraday", layout="wide")
st.title("Insider & Institutional Sell Risk Dashboard")

# -----------------------------
# INPUT
# -----------------------------
ticker = st.text_input("Inserisci il ticker", "PHIO")
current_price = st.number_input("Inserisci il prezzo attuale", min_value=0.0, value=3.47)

# -----------------------------
# FUNZIONI MODULARI
# -----------------------------
def get_openinsider_data(ticker):
    url = f"https://openinsider.com/search?q={ticker}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select("table.tinytable tr")[1:]
    insider_prices = []
    grants = []
    for row in rows:
        cols = [c.get_text(strip=True) for c in row.select("td")]
        if len(cols) > 6:
            trade_type = cols[5]
            price = cols[6]
            if trade_type == "P" and price.replace('.', '', 1).isdigit():
                insider_prices.append(float(price))
            if trade_type == "G":
                grants.append(cols[2])  # Trade Date
    avg_price = sum(insider_prices) / len(insider_prices) if insider_prices else 0
    return avg_price, grants

def calculate_vesting_score(grant_dates):
    vesting_score = 0
    bonus_vesting = 0
    for date in grant_dates:
        try:
            grant_date = datetime.strptime(date, "%Y-%m-%d")
            months_diff = (datetime.now().year - grant_date.year) * 12 + (datetime.now().month - grant_date.month)
            if months_diff >= 12:
                vesting_score = 100
                bonus_vesting = 20
            elif months_diff >= 6:
                vesting_score = 50
            elif months_diff >= 3:
                vesting_score = 80
        except:
            continue
    return vesting_score, bonus_vesting

def get_fintel_data(ticker):
    url = f"https://fintel.io/so/us/{ticker}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    trend_score = 0
    for row in soup.select("table tr"):
        cols = [c.get_text(strip=True) for c in row.select("td")]
        if len(cols) >= 3 and "%" in cols[-1]:
            change = cols[-1].replace("%", "").replace("+", "")
            try:
                change_val = float(change)
                if change_val < 0:
                    trend_score += 20
            except:
                continue
    trend_score = min(trend_score, 100)
    return trend_score

def get_dilution_tracker_data(ticker):
    # Placeholder: Dilution Tracker richiede login/API
    return {"rating": "High", "score": 100, "bonus": 20}

# -----------------------------
# CALCOLO SCORE
# -----------------------------
if st.button("Calcola Sell Risk Score"):
    insider_avg_price, grant_dates = get_openinsider_data(ticker)
    vesting_score, bonus_vesting = calculate_vesting_score(grant_dates)
    institutional_trend_score = get_fintel_data(ticker)
    dilution_data = get_dilution_tracker_data(ticker)

    price_gap_percent = ((current_price - insider_avg_price) / insider_avg_price) * 100 if insider_avg_price > 0 else 0
    price_gap_score = 100 if price_gap_percent > 50 else price_gap_percent
    bonus_gap = 10 if price_gap_percent > 50 else 0

    score = (
        price_gap_score * 0.30 +
        vesting_score * 0.35 +
        100 * 0.10 +  # ΔOwn placeholder
        0 * 0.05 +    # Pattern vendite
        institutional_trend_score * 0.10 +
        dilution_data["score"] * 0.10 +
        bonus_vesting + bonus_gap + dilution_data["bonus"]
    )
    score = min(score, 100)

    explanation = f"""
    **Ticker:** {ticker}
    **Prezzo attuale:** ${current_price}
    **Prezzo medio insider:** ${insider_avg_price:.2f}
    **Gap:** {price_gap_percent:.2f}% → Score: {price_gap_score}
    **Grant Vesting Score:** {vesting_score}
    **Institutional Trend Score:** {institutional_trend_score}
    **Dilution Tracker Rating:** {dilution_data['rating']}
    **Bonus:** Vesting({bonus_vesting}) + Gap({bonus_gap}) + Dilution({dilution_data['bonus']})
    **Sell Risk Score:** {score}
    """

    st.subheader("Risultato")
    st.success(f"Sell Risk Score: {score}")
    st.write(explanation)
    if score > 80:
        st.warning("⚠ ALERT: Alto rischio di vendita insider/istituzionali!")