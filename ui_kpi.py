import streamlit as st

# ===========================
# Funzione builder KPI flessibile
# ===========================
def build_kpi(title, total, red, green, 
              total_med=None, red_med=None, green_med=None, 
              suffix="%", show_bar=True):
    """
    Restituisce un dizionario KPI uniforme, pronto per la dashboard.
    Mediane opzionali: se None, verranno mostrate vuote.
    """
    return {
        "title": title,
        "total": total,
        "total_med": total_med,
        "red": red,
        "red_med": red_med,
        "green": green,
        "green_med": green_med,
        "suffix": suffix,
        "show_bar": show_bar
    }

# -------------------------------
# region KPI CARD 
# crea il layout per le card kpi
# -------------------------------

def kpi_box_statual(kpi, invert_negative=False):
    """KPI box layout verticale con Media/Mediana e confronto Red vs Green"""

    show_bar = kpi.get("show_bar", True)

    def fmt(x):
        try:
            return f"{x:.0f}"
        except (ValueError, TypeError):
            return str(x)

    title = kpi["title"]
    total = kpi["total"]
    red = kpi["red"]
    green = kpi["green"]
    suffix = kpi.get("suffix", "")

    total_med = total if kpi.get("total_med") is None else kpi.get("total_med")
    red_med   = red   if kpi.get("red_med")   is None else kpi.get("red_med")
    green_med = green if kpi.get("green_med") is None else kpi.get("green_med")


    # =========================
    # Calcolo barra
    # =========================
    red_pct = 50
    green_pct = 50
    delta = 0

    if show_bar:
        try:
            red_val = float(red_med)
            green_val = float(green_med)

            if red_val == green_val:
                red_pct = 50
                green_pct = 50
            else:
                delta = red_val - green_val
                if invert_negative:
                    delta = -delta

                total_abs = abs(red_val) + abs(green_val)
                if total_abs != 0:
                    red_pct = max(min(50 + (delta / total_abs) * 50, 100), 0)
                    green_pct = 100 - red_pct
                else:
                    red_pct = 50
                    green_pct = 50

        except (ValueError, TypeError):
            # valori non numerici (es. orari)
            show_bar = False


    # =========================
    # COSTRUZIONE BARRA HTML
    # =========================

    if show_bar:
        bar_html = (
            f'<div style="position:relative; width:100%; height:8px; '
            'background:#eee; border-radius:4px; display:flex; overflow:hidden;">'
            
            # barra rossa
            f'<div style="width:{red_pct}%; background:#E74C3C;"></div>'
            
            # barra verde
            f'<div style="width:{green_pct}%; background:#2ECC71;"></div>'
            
            # linea centrale (zero axis)
            '<div style="position:absolute; left:50%; top:0; bottom:0; '
            'width:3px; background:rgba(255, 255, 255, 1);"></div>'
            
            '</div>'
        )
    else:
        bar_html = '<div style="height:8px;"></div>'

    # ===========
    #    HTML
    # ===========

    html = f"""
    <div class="kpi-card">
        <div style="text-align:center; font-weight:600; margin-bottom:10px;">
            {title}
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="text-align:left;">
                <div style="font-size:22px; font-weight:600; font-variant-numeric: tabular-nums;">
                    {fmt(total)}{suffix}
                </div>
                <div style="font-size:18px; opacity:0.7; font-variant-numeric: tabular-nums;">
                    {fmt(total_med)}{suffix}
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:18px; font-weight:600; color:#E74C3C;">
                    {fmt(red)}{suffix}
                    <span style="font-size:14px; opacity:0.7; font-variant-numeric: tabular-nums;">
                        || {fmt(red_med)}{suffix}
                    </span>
                </div>
                <div style="font-size:18px; font-weight:600; color:#2ECC71;">
                    {fmt(green)}{suffix}
                    <span style="font-size:14px; opacity:0.7; font-variant-numeric: tabular-nums;">
                        || {fmt(green_med)}{suffix}
                    </span>
                </div>
            </div>
        </div>
        <div style="width:100%; margin-top:10px;">
            {bar_html}
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)