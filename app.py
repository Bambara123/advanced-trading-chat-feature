import streamlit as st
import streamlit.components.v1 as components
import finnhub
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Finnhub client
# ---------------------------------------------------------------------------
FINNHUB_API_KEY = st.secrets["FINNHUB_API_KEY"]

@st.cache_resource
def get_client():
    return finnhub.Client(api_key=FINNHUB_API_KEY)

fc = get_client()

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Market Explorer", layout="wide", initial_sidebar_state="collapsed")

# ---------------------------------------------------------------------------
# CSS: lock page, flex layout — top fixed, middle scrolls, bottom fixed
# ---------------------------------------------------------------------------
TOP_HEIGHT_EXPANDED = 300   # px – charts visible
TOP_HEIGHT_COLLAPSED = 55   # px – just the toggle button
BOTTOM_BAR_HEIGHT = 70      # px – chat input

show_graphs = st.session_state.get("show_graphs", True)
top_h = TOP_HEIGHT_EXPANDED if show_graphs else TOP_HEIGHT_COLLAPSED
mid_top = top_h + 8

st.markdown(f"""
<style>
/* ---- hide default Streamlit header/footer for a clean app look ---- */

header[data-testid="stHeader"] {{ display: none !important; }}
div[data-testid="stDecoration"] {{ display: none !important; }}


/* ---- page base ---- */
section.main > div.block-container {{
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}}

/* ===== TOP PANEL — fixed to top of viewport ===== */

.st-key-top_panel_header {{
    position: fixed !important;
    top: 0;
    left: 0;
    right: 0;
    z-index: 999;
    background: var(--background-color);
    height: {top_h}px;
    max-height: {top_h}px;
    overflow-x: auto;
    overflow-y: hidden;
    padding: 0.4rem 1rem 0.25rem 1rem;
    border-bottom: 1px solid var(--secondary-background-color);
}}

.st-key-top_panel {{
    position: fixed !important;
    top: 55px;
    left: 0;
    right: 0;
    z-index: 999;
    background: var(--background-color);
    height: {top_h}px;
    max-height: {top_h}px;
    overflow-x: auto;
    overflow-y: hidden;
    padding-left: 20px;
    padding-right: 20px;
    border-bottom: 1px solid var(--secondary-background-color);
}}

/* force chart columns into a single non-wrapping row */
.st-key-top_panel div[data-testid="stHorizontalBlock"] {{
    flex-wrap: nowrap !important;
    overflow-x: visible;
}}
/* each chart column gets a minimum width so they don't squish */
.st-key-top_panel div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {{
    min-width: 380px;
    flex: 0 0 auto !important;
}}

/* ---- scroll arrow buttons (injected via component) ---- */

/* ===== MIDDLE PANEL — between fixed top and fixed bottom, scrolls ===== */
.st-key-mid_panel {{
    position: fixed !important;
    top: {mid_top}px;
    bottom: {BOTTOM_BAR_HEIGHT}px;
    left: 0;
    right: 0;
    overflow-y: auto !important;
    overflow-x: hidden;
    padding: 0.5rem 1rem {BOTTOM_BAR_HEIGHT}px 1rem;
    z-index: 1;
}}

/* ---- chat input styling (bottom bar) ---- */
div[data-testid="stChatInput"] {{
    background-color: transparent;
}}
div[data-testid="stChatInput"] textarea {{
    border-radius: 24px !important;
}}
</style>
""", unsafe_allow_html=True)

if show_graphs:
    _arrow_mid = 55 + (TOP_HEIGHT_EXPANDED - 55) // 2
    components.html(f"""
    <script>
    (function() {{
      var doc = window.parent.document;

      var old1 = doc.getElementById('scroll-left-btn');
      var old2 = doc.getElementById('scroll-right-btn');
      if (old1) old1.remove();
      if (old2) old2.remove();

      if (!doc.getElementById('tp-scroll-style')) {{
        var style = doc.createElement('style');
        style.id = 'tp-scroll-style';
        style.textContent = `
          .tp-scroll-btn {{
            position: fixed;
            top: {_arrow_mid}px;
            transform: translateY(-50%);
            width: 36px; height: 36px;
            border-radius: 50%;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(40,40,40,0.8);
            color: #fff;
            font-size: 1rem;
            cursor: pointer;
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0.1;
          }}
          .tp-scroll-btn:hover {{ opacity: 0.5; background: rgba(70,70,70,0.95); }}
        `;
        doc.head.appendChild(style);
      }}

      function getScrollTarget() {{
        var panel = doc.querySelector('.st-key-top_panel');
        if (!panel) return null;
        if (panel.scrollWidth > panel.clientWidth) return panel;
        var children = panel.querySelectorAll('div');
        for (var i = 0; i < children.length; i++) {{
          if (children[i].scrollWidth > children[i].clientWidth) return children[i];
        }}
        return panel;
      }}

      var btnL = doc.createElement('button');
      btnL.id = 'scroll-left-btn';
      btnL.className = 'tp-scroll-btn';
      btnL.style.left = '8px';
      btnL.addEventListener('click', function() {{
        var t = getScrollTarget();
        if (t) t.scrollBy({{ left: -400, behavior: 'smooth' }});
      }});
      btnL.innerHTML = '&#9664;';

      var btnR = doc.createElement('button');
      btnR.id = 'scroll-right-btn';
      btnR.className = 'tp-scroll-btn';
      btnR.style.right = '8px';
      btnR.addEventListener('click', function() {{
        var t = getScrollTarget();
        if (t) t.scrollBy({{ left: 400, behavior: 'smooth' }});
      }});
      btnR.innerHTML = '&#9654;';

      doc.body.appendChild(btnL);
      doc.body.appendChild(btnR);
    }})();
    </script>
    """, height=0)
else:
    components.html("""
    <script>
    (function() {
      var doc = window.parent.document;
      var old1 = doc.getElementById('scroll-left-btn');
      var old2 = doc.getElementById('scroll-right-btn');
      if (old1) old1.remove();
      if (old2) old2.remove();
    })();
    </script>
    """, height=0)

# ---------------------------------------------------------------------------
# Data-fetching helpers (from FH_Check_0_Uthsara.ipynb)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def fetch_basic_financials(symbol: str):
    return fc.company_basic_financials(symbol, "all")

@st.cache_data(ttl=300, show_spinner=False)
def fetch_recommendation_trends(symbol: str):
    return fc.recommendation_trends(symbol)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_price_target(symbol: str):
    return fc.price_target(symbol)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_company_earnings(symbol: str, limit: int = 20):
    return fc.company_earnings(symbol, limit=limit)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_earnings_calendar(symbol: str):
    today = datetime.now()
    return fc.earnings_calendar(
        _from=(today - timedelta(days=365)).strftime("%Y-%m-%d"),
        to=(today + timedelta(days=180)).strftime("%Y-%m-%d"),
        symbol=symbol,
    )

@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock_splits(symbol: str):
    return fc.stock_splits(symbol, _from="2000-01-01", to=datetime.now().strftime("%Y-%m-%d"))

@st.cache_data(ttl=300, show_spinner=False)
def fetch_basic_dividends(symbol: str):
    return fc.stock_basic_dividends(symbol)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_upgrade_downgrade(symbol: str):
    today = datetime.now()
    return fc.upgrade_downgrade(
        symbol=symbol,
        _from=(today - timedelta(days=730)).strftime("%Y-%m-%d"),
        to=today.strftime("%Y-%m-%d"),
    )

@st.cache_data(ttl=300, show_spinner=False)
def fetch_revenue_estimates(symbol: str, freq: str = "quarterly"):
    return fc.company_revenue_estimates(symbol, freq=freq)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_eps_estimates(symbol: str, freq: str = "quarterly"):
    return fc.company_eps_estimates(symbol, freq=freq)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_etf_profile(symbol: str):
    return fc.etfs_profile(symbol=symbol)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_etf_holdings(symbol: str, top_n: int = 20):
    return fc.etfs_holdings(symbol=symbol)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_etf_sector_exposure(symbol: str):
    return fc.etfs_sector_exp(symbol=symbol)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_etf_country_exposure(symbol: str):
    return fc.etfs_country_exp(symbol=symbol)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_index_constituents(symbol: str):
    return fc.indices_const(symbol=symbol)


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------
template_theme = "plotly_dark"

def build_recommendation_chart(symbol: str):
    data = fetch_recommendation_trends(symbol)
    if not data:
        return None
    df = pd.DataFrame(data)
    if df.empty:
        return None
    df = df.sort_values("period")
    fig = go.Figure()
    for col, color in [("strongBuy", "#22c55e"), ("buy", "#86efac"),
                        ("hold", "#fbbf24"), ("sell", "#f87171"), ("strongSell", "#dc2626")]:
        if col in df.columns:
            fig.add_trace(go.Bar(x=df["period"], y=df[col], name=col, marker_color=color))
    fig.update_layout(
        barmode="stack", title=f"{symbol} Recommendations",
        template=template_theme, height=260, margin=dict(l=30, r=10, t=35, b=25),
        legend=dict(orientation="h", y=-0.2, font=dict(size=9)),
    )
    return fig


def build_eps_surprise_chart(symbol: str):
    data = fetch_company_earnings(symbol, limit=12)
    if not data:
        return None
    df = pd.DataFrame(data)
    if df.empty or "actual" not in df.columns:
        return None
    df = df.sort_values("period")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["period"], y=df["estimate"], name="Estimate", marker_color="#64748b"))
    fig.add_trace(go.Bar(x=df["period"], y=df["actual"], name="Actual", marker_color="#3b82f6"))
    fig.update_layout(
        barmode="group", title=f"{symbol} EPS: Actual vs Est",
        template=template_theme, height=260, margin=dict(l=30, r=10, t=35, b=25),
        legend=dict(orientation="h", y=-0.2, font=dict(size=9)),
    )
    return fig


def build_revenue_estimates_chart(symbol: str):
    res = fetch_revenue_estimates(symbol, freq="quarterly")
    data = res.get("data", []) if res else []
    if not data:
        return None
    df = pd.DataFrame(data)
    if df.empty or "revenueAvg" not in df.columns:
        return None
    df = df.sort_values("period")
    df["revenueAvg_B"] = df["revenueAvg"] / 1e9
    fig = px.bar(
        df, x="period", y="revenueAvg_B",
        title=f"{symbol} Revenue Est ($B)",
        template=template_theme, color_discrete_sequence=["#8b5cf6"],
    )
    fig.update_layout(height=260, margin=dict(l=30, r=10, t=35, b=25), yaxis_title="$B")
    return fig


def build_price_target_chart(symbol: str):
    data = fetch_price_target(symbol)
    if not data or "targetMean" not in data:
        return None
    vals = {k: data[k] for k in ["targetLow", "targetMean", "targetMedian", "targetHigh"] if k in data}
    if not vals:
        return None
    fig = go.Figure(go.Bar(
        x=list(vals.keys()), y=list(vals.values()),
        marker_color=["#f87171", "#3b82f6", "#a78bfa", "#22c55e"],
        text=[f"${v:,.1f}" for v in vals.values()], textposition="outside",
    ))
    analysts = data.get("numberAnalysts", "?")
    fig.update_layout(
        title=f"{symbol} Price Targets ({analysts} analysts)",
        template=template_theme, height=260, margin=dict(l=30, r=10, t=35, b=25),
    )
    return fig


def build_etf_sector_chart(symbol: str):
    res = fetch_etf_sector_exposure(symbol)
    sectors = res.get("sectorExposure", []) if res else []
    if not sectors:
        return None
    df = pd.DataFrame(sectors).sort_values("exposure", ascending=False)
    fig = px.pie(
        df, values="exposure", names="industry",
        title=f"{symbol} Sector Exposure", template=template_theme, hole=0.35,
    )
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=35, b=10))
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return fig


def build_etf_holdings_chart(symbol: str, top_n: int = 15):
    res = fetch_etf_holdings(symbol)
    holdings = res.get("holdings", []) if res else []
    if not holdings:
        return None
    df = pd.DataFrame(holdings)
    if "percent" not in df.columns:
        return None
    df = df.sort_values("percent", ascending=False).head(top_n)
    fig = px.bar(
        df, x="symbol", y="percent",
        title=f"{symbol} Top Holdings (%)", template=template_theme,
        color="percent", color_continuous_scale="Blues",
    )
    fig.update_layout(height=260, margin=dict(l=30, r=10, t=35, b=25))
    return fig


# ---------------------------------------------------------------------------
# Detect symbol type
# ---------------------------------------------------------------------------

def detect_symbol_type(symbol: str) -> str:
    s = symbol.upper().strip()
    if s.startswith("^"):
        return "index"
    try:
        etf_res = fetch_etf_profile(s)
        profile = etf_res.get("profile", {}) if etf_res else {}
        if isinstance(profile, list) and len(profile) > 0:
            profile = profile[0]
        if profile and profile.get("name"):
            return "etf"
    except Exception:
        pass
    return "stock"


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "symbol" not in st.session_state:
    st.session_state.symbol = ""
if "show_graphs" not in st.session_state:
    st.session_state.show_graphs = True


# ===================================================================
# LAYER 3 — BOTTOM SEARCH BAR  (st.chat_input — natively fixed)
# ===================================================================
search_input = st.chat_input(
    placeholder="Search a symbol, ETF, or index  (e.g. AAPL, SPY, ^GSPC)",
)
if search_input:
    st.session_state.symbol = search_input.strip().upper()

symbol = st.session_state.symbol

# ---------------------------------------------------------------------------
# No symbol yet → welcome screen
# ---------------------------------------------------------------------------
if not symbol:
    st.markdown(
        '<div style="display:flex;flex-direction:column;align-items:center;'
        'justify-content:center;height:70vh;opacity:0.45;">'
        '<h1 style="font-size:2.8rem;font-weight:300;letter-spacing:3px;">Market Explorer</h1>'
        '<p style="font-size:1.1rem;">Type a symbol in the search bar below to begin</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.stop()

# ---------------------------------------------------------------------------
# Determine type
# ---------------------------------------------------------------------------
sym_type = detect_symbol_type(symbol)

# ===================================================================
# LAYER 1 — TOP PANEL (fixed to top, shrinks when hidden)
# ===================================================================

top_panel_header = st.container(key="top_panel_header")

with top_panel_header:
    toggle_label = "Hide Charts" if st.session_state.show_graphs else "Show Charts"
    if st.button(toggle_label, key="toggle_graphs", type="secondary"):
        st.session_state.show_graphs = not st.session_state.show_graphs
        st.rerun()

top_panel = st.container(key="top_panel")

with top_panel:

    if st.session_state.show_graphs:
        charts = []
        if sym_type in ("stock", "etf"):
            for builder in [build_recommendation_chart, build_eps_surprise_chart,
                            build_revenue_estimates_chart, build_price_target_chart]:
                try:
                    fig = builder(symbol)
                    if fig:
                        charts.append(fig)
                except Exception:
                    pass

        if sym_type == "etf":
            for builder in [build_etf_sector_chart, build_etf_holdings_chart]:
                try:
                    fig = builder(symbol)
                    if fig:
                        charts.append(fig)
                except Exception:
                    pass

        if charts:
            cols = st.columns(len(charts))
            for col, fig in zip(cols, charts):
                col.plotly_chart(fig, use_container_width=True, key=f"tc_{id(fig)}")
        else:
            st.caption("No chart data available for this symbol.")

# ===================================================================
# LAYER 2 — MIDDLE PANEL (fills remaining space, scrolls internally)
# ===================================================================

middle = st.container(key="mid_panel")

with middle:
    st.subheader(f"{symbol}  —  {'Stock' if sym_type == 'stock' else 'ETF' if sym_type == 'etf' else 'Index'}")

    # ------------------------------------------------------------------
    # INDEX
    # ------------------------------------------------------------------
    if sym_type == "index":
        tab_constituents, tab_details = st.tabs(["Constituents", "Details"])

        with tab_constituents:
            try:
                res = fetch_index_constituents(symbol)
                constit = res.get("constituents", [])
                breakdown = res.get("constituentsBreakdown", [])
                st.metric("Total Constituents", len(constit))
                if breakdown:
                    df = pd.DataFrame(breakdown)
                    display_cols = [c for c in ["symbol", "name", "weight", "isin", "cusip"] if c in df.columns]
                    if display_cols:
                        df = df[display_cols]
                    if "weight" in df.columns:
                        df = df.sort_values("weight", ascending=False)
                        df["weight"] = df["weight"].apply(lambda x: f"{x:.4f}%")
                    st.dataframe(df, use_container_width=True, height=350)
                elif constit:
                    st.write(", ".join(constit))
            except Exception as e:
                st.error(f"Could not load constituents: {e}")

        with tab_details:
            st.write(f"Index symbol: **{symbol}**")
            try:
                res = fetch_index_constituents(symbol)
                st.json({"symbol": symbol, "totalConstituents": len(res.get("constituents", []))})
            except Exception:
                pass

    # ------------------------------------------------------------------
    # ETF
    # ------------------------------------------------------------------
    elif sym_type == "etf":
        tab_profile, tab_holdings, tab_sector, tab_country, tab_earnings, tab_recs = st.tabs(
            ["Profile", "Holdings", "Sector", "Country", "Earnings", "Analysts"]
        )

        with tab_profile:
            try:
                res = fetch_etf_profile(symbol)
                profile = res.get("profile", {})
                if isinstance(profile, list) and len(profile) > 0:
                    profile = profile[0]
                if profile:
                    c1, c2 = st.columns(2)
                    c1.metric("Name", profile.get("name", "N/A"))
                    c1.metric("Asset Class", profile.get("assetClass", "N/A"))
                    c1.metric("Expense Ratio", f"{profile.get('expenseRatio', 'N/A')}%")
                    c2.metric("AUM", f"${profile.get('aum', 0):,.0f}")
                    c2.metric("NAV", f"${profile.get('nav', 0):,.2f}")
                    c2.metric("Inception", profile.get("inceptionDate", "N/A"))
                    st.write(profile.get("description", ""))
                else:
                    st.warning("No profile data.")
            except Exception as e:
                st.error(str(e))

        with tab_holdings:
            try:
                res = fetch_etf_holdings(symbol)
                holdings = res.get("holdings", [])
                if holdings:
                    df = pd.DataFrame(holdings)
                    if "percent" in df.columns:
                        df = df.sort_values("percent", ascending=False).reset_index(drop=True)
                    st.dataframe(df, use_container_width=True, height=350)
                else:
                    st.info("No holdings data.")
            except Exception as e:
                st.error(str(e))

        with tab_sector:
            try:
                res = fetch_etf_sector_exposure(symbol)
                sectors = res.get("sectorExposure", [])
                if sectors:
                    st.dataframe(
                        pd.DataFrame(sectors).sort_values("exposure", ascending=False).reset_index(drop=True),
                        use_container_width=True,
                    )
                else:
                    st.info("No sector data.")
            except Exception as e:
                st.error(str(e))

        with tab_country:
            try:
                res = fetch_etf_country_exposure(symbol)
                countries = res.get("countryExposure", [])
                if countries:
                    st.dataframe(
                        pd.DataFrame(countries).sort_values("exposure", ascending=False).reset_index(drop=True),
                        use_container_width=True,
                    )
                else:
                    st.info("No country data.")
            except Exception as e:
                st.error(str(e))

        with tab_earnings:
            try:
                data = fetch_company_earnings(symbol, limit=20)
                if data:
                    st.dataframe(
                        pd.DataFrame(data).sort_values("period", ascending=False).reset_index(drop=True),
                        use_container_width=True, height=350,
                    )
                else:
                    st.info("No earnings data.")
            except Exception as e:
                st.error(str(e))

        with tab_recs:
            try:
                data = fetch_recommendation_trends(symbol)
                if data:
                    st.dataframe(
                        pd.DataFrame(data).sort_values("period", ascending=False).reset_index(drop=True),
                        use_container_width=True,
                    )
                else:
                    st.info("No recommendation data.")
            except Exception as e:
                st.error(str(e))

    # ------------------------------------------------------------------
    # STOCK (default)
    # ------------------------------------------------------------------
    else:
        tab_overview, tab_earnings, tab_estimates, tab_recs, tab_upgrades, tab_divs, tab_splits = st.tabs(
            ["Overview", "Earnings", "Estimates", "Analysts", "Upgrades", "Dividends", "Splits"]
        )

        with tab_overview:
            try:
                res = fetch_basic_financials(symbol)
                metric = res.get("metric", {})
                if metric:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("52-Wk High", f"${metric.get('52WeekHigh', 'N/A')}")
                    c2.metric("52-Wk Low", f"${metric.get('52WeekLow', 'N/A')}")
                    c3.metric("Beta", f"{metric.get('beta', 'N/A')}")
                    c4.metric("P/E (TTM)", f"{metric.get('peTTM', 'N/A')}")

                    c5, c6, c7, c8 = st.columns(4)
                    c5.metric("P/B (Annual)", f"{metric.get('pbAnnual', 'N/A')}")
                    c6.metric("Div Yield TTM", f"{metric.get('currentDividendYieldTTM', 'N/A')}%")
                    c7.metric("ROE TTM", f"{metric.get('roeTTM', 'N/A')}%")
                    c8.metric("EPS TTM", f"${metric.get('epsTTM', 'N/A')}")

                    display_keys = [
                        "marketCapitalization", "revenuePerShareTTM", "netIncomePerShareTTM",
                        "operatingMarginTTM", "grossMarginTTM", "debtEquityTTM",
                        "currentRatioQuarterly", "quickRatioQuarterly",
                        "10DayAverageTradingVolume", "3MonthAverageTradingVolume",
                    ]
                    rows = [{k: metric.get(k, "N/A") for k in display_keys}]
                    st.dataframe(pd.DataFrame(rows).T.rename(columns={0: "Value"}), use_container_width=True)
                else:
                    st.warning("No financial data.")
            except Exception as e:
                st.error(str(e))

            try:
                pt = fetch_price_target(symbol)
                if pt and "targetMean" in pt:
                    st.markdown("**Price Target Consensus**")
                    pc1, pc2, pc3, pc4 = st.columns(4)
                    pc1.metric("Low", f"${pt.get('targetLow', 'N/A')}")
                    pc2.metric("Mean", f"${pt.get('targetMean', 'N/A'):,.2f}")
                    pc3.metric("Median", f"${pt.get('targetMedian', 'N/A')}")
                    pc4.metric("High", f"${pt.get('targetHigh', 'N/A')}")
            except Exception:
                pass

        with tab_earnings:
            try:
                data = fetch_company_earnings(symbol, limit=40)
                if data:
                    st.dataframe(
                        pd.DataFrame(data).sort_values("period", ascending=False).reset_index(drop=True),
                        use_container_width=True, height=350,
                    )
                else:
                    st.info("No earnings data.")
            except Exception as e:
                st.error(str(e))

        with tab_estimates:
            est_sub = st.radio("Type", ["Revenue", "EPS"], horizontal=True, key="est_type")
            freq = st.radio("Frequency", ["quarterly", "annual"], horizontal=True, key="est_freq")
            try:
                if est_sub == "Revenue":
                    res = fetch_revenue_estimates(symbol, freq=freq)
                else:
                    res = fetch_eps_estimates(symbol, freq=freq)
                est_rows = res.get("data", []) if res else []
                if est_rows:
                    st.dataframe(
                        pd.DataFrame(est_rows).sort_values("period", ascending=False).reset_index(drop=True),
                        use_container_width=True, height=350,
                    )
                else:
                    st.info("No estimate data.")
            except Exception as e:
                st.error(str(e))

        with tab_recs:
            try:
                data = fetch_recommendation_trends(symbol)
                if data:
                    st.dataframe(
                        pd.DataFrame(data).sort_values("period", ascending=False).reset_index(drop=True),
                        use_container_width=True,
                    )
                else:
                    st.info("No recommendation data.")
            except Exception as e:
                st.error(str(e))

        with tab_upgrades:
            try:
                data = fetch_upgrade_downgrade(symbol)
                if data:
                    df = pd.DataFrame(data)
                    if "gradeTime" in df.columns:
                        df["gradeTime"] = pd.to_datetime(df["gradeTime"], unit="s")
                    df = df.sort_values("gradeTime", ascending=False).reset_index(drop=True)
                    st.dataframe(df, use_container_width=True, height=350)
                else:
                    st.info("No upgrade/downgrade data.")
            except Exception as e:
                st.error(str(e))

        with tab_divs:
            try:
                res = fetch_basic_dividends(symbol)
                divs = res.get("data", []) if res else []
                if divs:
                    df = pd.DataFrame(divs)
                    if "exDate" in df.columns:
                        df = df.sort_values("exDate", ascending=False).reset_index(drop=True)
                    st.dataframe(df, use_container_width=True, height=350)
                else:
                    st.info("No dividend data.")
            except Exception as e:
                st.error(str(e))

        with tab_splits:
            try:
                splits = fetch_stock_splits(symbol)
                if splits:
                    df = pd.DataFrame(splits)
                    if "date" in df.columns:
                        df = df.sort_values("date", ascending=False).reset_index(drop=True)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No split data.")
            except Exception as e:
                st.error(str(e))
