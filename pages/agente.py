# app_phio_insiders.py
import streamlit as st
import requests, re, datetime, math, xml.etree.ElementTree as ET
import pandas as pd
from io import StringIO

st.set_page_config(layout="wide")
st.title("PHIO — Analisi Grants / Insider (exercisable today)")

# CONFIG
USER_AGENT = "FrancescoApp/1.0 (mailto:tuo-email@example.com)"
TODAY = datetime.date.today()

# --- helper: get CIK via ticker.txt (SEC) ---
def get_cik_from_sec(ticker):
    url = "https://www.sec.gov/include/ticker.txt"
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text), sep="\t", header=None, names=["ticker", "cik"])
    df["ticker"] = df["ticker"].str.upper()
    match = df[df["ticker"] == ticker.upper()]
    if match.empty:
        return None
    return str(match.iloc[0]["cik"]).zfill(10)

# --- helper: get list of Form 4 filing pages (atom feed) ---
def get_form4_filing_pages(cik, count=200):
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&owner=include&count={count}&output=atom"
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    # parse as XML to extract entry links
    root = ET.fromstring(r.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall("atom:entry", ns)
    links = []
    for e in entries:
        link_el = e.find("atom:link", ns)
        if link_el is not None and "href" in link_el.attrib:
            links.append(link_el.attrib["href"])
    return links

# --- helper: from filing page find the form4 xml url ---
def find_form4_xml_url(filing_page_url):
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(filing_page_url, headers=headers, timeout=20)
    r.raise_for_status()
    html = r.text
    # heuristic: find href to .xml (doc4.xml or ownership.xml), prefer form4 xml
    m = re.search(r'href="(.*?\.xml)"', html, flags=re.IGNORECASE)
    if not m:
        return None
    xml_url = m.group(1)
    if xml_url.startswith("/"):
        xml_url = "https://www.sec.gov" + xml_url
    return xml_url

# --- parse form4 xml: extract nonDerivative and derivative rows ---
def parse_form4_xml(xml_url):
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(xml_url, headers=headers, timeout=20)
    r.raise_for_status()
    try:
        root = ET.fromstring(r.text)
    except Exception:
        # try to remove potential namespace garbage
        root = ET.fromstring(r.content.decode('utf-8', errors='ignore'))
    # reporting owner
    owner_name_el = root.find(".//reportingOwner/reportingOwnerId/rptOwnerName")
    owner_name = owner_name_el.text.strip() if owner_name_el is not None else "UNKNOWN"
    rows = []
    # non-derivative
    for node in root.findall(".//nonDerivativeTable/nonDerivativeTransaction"):
        code = node.findtext("transactionCoding/transactionCode")
        date = node.findtext("transactionDate/value")
        shares = node.findtext("transactionAmounts/transactionShares/value")
        price = node.findtext("transactionAmounts/transactionPricePerShare/value")
        rows.append({
            "owner": owner_name, "sect_type":"non-derivative", "code": code, "date": date, "shares": shares, "price": price,
            "date_exercisable": None, "expiration": None, "underlying": None
        })
    # derivative
    for node in root.findall(".//derivativeTable/derivativeTransaction"):
        code = node.findtext("transactionCoding/transactionCode")
        date = node.findtext("transactionDate/value")
        shares = node.findtext("transactionAmounts/transactionShares/value")
        price = node.findtext("transactionAmounts/transactionPricePerShare/value")
        date_ex = node.findtext("derivativeSecurityDetails/dateExercisable/value")
        exp = node.findtext("derivativeSecurityDetails/expirationDate/value")
        underlying = node.findtext("derivativeSecurityDetails/underlyingSecurity/underlyingSecurityTitle")
        rows.append({
            "owner": owner_name, "sect_type":"derivative", "code": code, "date": date, "shares": shares, "price": price,
            "date_exercisable": date_ex, "expiration": exp, "underlying": underlying
        })
    return rows

# --- analysis pipeline ---
def analyze_ticker(ticker, pre_market_price, max_filings=200):
    out_rows = []
    cik = get_cik_from_sec(ticker)
    if not cik:
        st.error("CIK non trovato su SEC per ticker " + ticker)
        return None, None, None
    filing_pages = get_form4_filing_pages(cik, count=max_filings)
    if not filing_pages:
        st.warning("Nessun Form 4 trovato nell'index per questo CIK.")
        return cik, None, None

    for fp in filing_pages:
        try:
            xml_url = find_form4_xml_url(fp)
            if not xml_url:
                continue
            rows = parse_form4_xml(xml_url)
            for r in rows:
                out_rows.append(r)
        except Exception as e:
            # log and continue
            print("skip filing", fp, e)
            continue

    df = pd.DataFrame(out_rows)
    if df.empty:
        return cik, df, None

    # normalize dates and numeric
    def to_date_safe(s):
        try:
            return datetime.datetime.strptime(s, "%Y-%m-%d").date()
        except:
            return None
    df["date_parsed"] = df["date"].apply(to_date_safe)
    df["date_exercisable_parsed"] = df["date_exercisable"].apply(to_date_safe)
    df["shares_num"] = pd.to_numeric(df["shares"], errors="coerce").fillna(0)
    df["price_num"] = pd.to_numeric(df["price"], errors="coerce").replace({0: math.nan})

    # flag exercisable today
    df["exercisable_today"] = df["date_exercisable_parsed"].apply(lambda d: d is not None and d <= TODAY)

    # summary per owner
    owners = []
    for owner, group in df.groupby("owner"):
        tot_ex = group[group["exercisable_today"]]["shares_num"].sum()
        # avg cost from non-derivative purchases (transaction code P or other buy codes)
        buys = group[(group["sect_type"]=="non-derivative") & (group["code"] != None) & (group["code"].str.upper().isin(["P","A"])) ]
        avg_cost = buys["price_num"].mean() if not buys.empty else float("nan")
        owners.append({"owner": owner, "shares_exercisable_today": tot_ex, "avg_cost": avg_cost, "num_rows": group.shape[0]})
    summary = pd.DataFrame(owners).sort_values(by="shares_exercisable_today", ascending=False)

    # simple heuristic probability score
    score = 0.0
    # weight by total exercisable shares
    total_ex_all = summary["shares_exercisable_today"].sum() if not summary.empty else 0
    if total_ex_all > 0:
        score += min(50, (total_ex_all / 10000) * 5)   # example scaling; adjust thresholds
    # price delta
    # if any owner avg_cost significantly < pre_market_price add weight
    if not summary.empty:
        cheap = summary[summary["avg_cost"] < (pre_market_price * 0.85)]
        if not cheap.empty:
            score += min(40, (cheap["shares_exercisable_today"].sum() / max(1, total_ex_all)) * 40)
    # presence of many filings / offerings -> extra flag
    if len(filing_pages) > 20:
        score += 5

    final_prob = min(100, round(score,1))
    return cik, df, summary.assign(probability_percent=final_prob)

# --- UI ---
ticker = st.text_input("Ticker (es. PHIO):", value="PHIO").upper()
pre_price = st.number_input("Prezzo pre-market ($):", value=3.47, format="%.4f")
run = st.button("Esegui Analisi")

if run and ticker:
    with st.spinner("Analisi in corso (scarico Form 4, parsing XML)..."):
        try:
            cik, df, summary = analyze_ticker(ticker, pre_price, max_filings=200)
        except Exception as e:
            st.error("Errore durante l'analisi: " + str(e))
            raise

        st.write("CIK:", cik)
        if df is None or df.empty:
            st.warning("Nessun record Form 4 parsabile trovato.")
        else:
            st.subheader("Summary per reporting owner (shares exercisable oggi)")
            st.dataframe(summary)
            st.subheader("Tutte le transazioni parsate (es. Table I e II)")
            st.dataframe(df.sort_values(by=["date_parsed"], ascending=False))

            # highlight likely sellers
            if summary is not None and not summary.empty:
                likely = summary[(summary["shares_exercisable_today"]>0) & (summary["avg_cost"] < pre_price * 0.85)]
                st.subheader("Reporting owner con shares esercitabili oggi e avg_cost << prezzo attuale")
                if not likely.empty:
                    st.dataframe(likely)
                else:
                    st.info("Nessun owner corrispondente al filtro (avg_cost << prezzo).")
