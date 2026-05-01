import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import requests
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Stock Radar Pro v2", layout="wide")
st_autorefresh(interval=60000, key="refresh")

st.markdown("""
<style>
.block-container { padding-top: 1rem; padding-bottom: 1rem; }
[data-testid="stMetricValue"] { font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

DEFAULT_TICKERS = [
    "NVDA", "AMD", "AVGO", "TSM", "MSFT", "GOOGL", "AMZN", "META", "AAPL",
    "ETN", "VRT", "PWR", "CEG", "NEE", "GEV", "CAT",
    "LMT", "RTX", "NOC", "GD",
    "LLY", "NVO", "ISRG", "UNH",
    "JPM", "V", "MA", "COST", "WMT",
    "XOM", "CVX", "COP"
]

NEWS_KEYWORDS = [
    "Trump", "tariff", "Fed", "interest rate", "China",
    "Nvidia", "AI chip", "export ban", "war", "sanctions",
    "oil", "Taiwan", "Middle East", "inflation"
]

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_period_interval(mode):
    if mode == "日K":
        return "1y", "1d"
    if mode == "30分鐘":
        return "60d", "30m"
    if mode == "5分鐘":
        return "5d", "5m"
    return "1y", "1d"

@st.cache_data(ttl=60)
def fetch_price_data(ticker, period, interval):
    try:
        return yf.Ticker(ticker).history(period=period, interval=interval)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def scan_stocks(tickers):
    results = []

    for ticker in tickers:
        try:
            data = yf.Ticker(ticker).history(period="1y", interval="1d")

            if data.empty or len(data) < 200:
                continue

            data["MA20"] = data["Close"].rolling(20).mean()
            data["MA50"] = data["Close"].rolling(50).mean()
            data["MA200"] = data["Close"].rolling(200).mean()
            data["RSI"] = calc_rsi(data["Close"])
            data["VolAvg20"] = data["Volume"].rolling(20).mean()
            data["High20"] = data["High"].rolling(20).max()
            data["Low20"] = data["Low"].rolling(20).min()

            latest = data.iloc[-1]

            close = latest["Close"]
            ma20 = latest["MA20"]
            ma50 = latest["MA50"]
            ma200 = latest["MA200"]
            rsi = latest["RSI"]
            high20 = latest["High20"]
            vol_ratio = latest["Volume"] / latest["VolAvg20"] if latest["VolAvg20"] > 0 else 0
            distance_ma50 = (close / ma50 - 1) * 100

            score = 0
            tags = []

            if close > ma20:
                score += 10
                tags.append("MA20↑")
            if close > ma50:
                score += 15
                tags.append("MA50↑")
            if close > ma200:
                score += 15
                tags.append("MA200↑")
            if close >= high20 * 0.995:
                score += 20
                tags.append("20日新高")
            if vol_ratio > 1.5:
                score += 15
                tags.append("量增")

            if 45 <= rsi <= 65:
                score += 10
                tags.append("RSI健康")
            elif rsi > 75:
                score -= 15
                tags.append("過熱")
            elif rsi < 35:
                score += 5
                tags.append("跌深")

            if distance_ma50 > 15:
                score -= 15
                tags.append("追高")
            elif distance_ma50 < -10:
                tags.append("偏弱")

            support = data["Low"].tail(20).min()
            resistance = data["High"].tail(20).max()
            stop_loss = support * 0.98

            if score >= 65 and rsi < 75 and distance_ma50 < 15:
                action = "🔥 Watch"
            elif score >= 45:
                action = "🟡 Wait"
            else:
                action = "⚪ Avoid"

            results.append({
                "Ticker": ticker,
                "Close": round(close, 2),
                "Score": score,
                "Action": action,
                "RSI": round(rsi, 1),
                "Vol": round(vol_ratio, 2),
                "MA50%": round(distance_ma50, 1),
                "Support": round(support, 2),
                "Resist": round(resistance, 2),
                "Stop": round(stop_loss, 2),
                "Tags": ", ".join(tags)
            })

        except Exception:
            pass

    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values("Score", ascending=False)
    return df

def make_chart(ticker, mode):
    period, interval = get_period_interval(mode)
    data = fetch_price_data(ticker, period, interval)

    if data.empty or len(data) < 50:
        st.warning(f"抓不到 {ticker} 的K線資料，可能代碼錯誤或資料源暫時失敗。")
        return

    data["MA20"] = data["Close"].rolling(20).mean()
    data["MA50"] = data["Close"].rolling(50).mean()
    data["RSI"] = calc_rsi(data["Close"])

    support = data["Low"].tail(40).min()
    resistance = data["High"].tail(40).max()
    latest_close = data["Close"].iloc[-1]
    stop_loss = support * 0.98
    risk = latest_close - stop_loss
    reward = resistance - latest_close
    rr = reward / risk if risk > 0 else 0

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.68, 0.16, 0.16],
        subplot_titles=(f"{ticker}｜{mode}", "Volume", "RSI")
    )

    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data["Open"],
        high=data["High"],
        low=data["Low"],
        close=data["Close"],
        name="K"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=data.index, y=data["MA20"], name="MA20", mode="lines"), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data["MA50"], name="MA50", mode="lines"), row=1, col=1)

    fig.add_hline(y=support, line_dash="dash", annotation_text="支撐", row=1, col=1)
    fig.add_hline(y=resistance, line_dash="dash", annotation_text="壓力", row=1, col=1)

    fig.add_trace(go.Bar(x=data.index, y=data["Volume"], name="Vol"), row=2, col=1)

    fig.add_trace(go.Scatter(x=data.index, y=data["RSI"], name="RSI", mode="lines"), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", annotation_text="70", row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", annotation_text="30", row=3, col=1)

    fig.update_layout(
        height=760,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_rangeslider_visible=False,
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("現價", round(latest_close, 2))
    c2.metric("支撐", round(support, 2))
    c3.metric("壓力", round(resistance, 2))
    c4.metric("停損", round(stop_loss, 2))
    c5.metric("R/R", round(rr, 2))

    if rr >= 1.5:
        st.success("風險報酬比不錯，可列入觀察。")
    elif rr > 0:
        st.warning("風險報酬比普通，等更好的進場點。")
    else:
        st.error("目前離壓力太近，不適合追。")

def fetch_news():
    try:
        api_key = st.secrets.get("NEWS_API_KEY", "")
    except Exception:
        api_key = ""

    if not api_key:
        return []

    query = " OR ".join(NEWS_KEYWORDS)
    url = "https://newsapi.org/v2/everything"

    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 10,
        "apiKey": api_key
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json().get("articles", [])
    except Exception:
        return []

def judge_news(title):
    t = title.lower()

    bearish = ["tariff", "ban", "sanction", "war", "inflation", "rate hike", "selloff"]
    bullish = ["deal", "approval", "contract", "stimulus", "record", "cut"]

    if any(w in t for w in bearish):
        return "🔴 利空/風險"
    if any(w in t for w in bullish):
        return "🟢 利多"
    return "🟡 觀察"

with st.sidebar:
    st.header("設定")

    tickers_text = st.text_area(
        "股票雷達清單（用逗號分隔，可自己加）",
        ",".join(DEFAULT_TICKERS),
        height=120
    )

    tickers = [x.strip().upper() for x in tickers_text.split(",") if x.strip()]

    search_ticker = st.text_input(
        "搜尋股票代碼",
        placeholder="例如 TSLA / PLTR / SOFI / RKLB"
    ).strip().upper()

    if search_ticker:
        if search_ticker not in tickers:
            tickers.append(search_ticker)
        selected_ticker = search_ticker
    else:
        selected_ticker = st.selectbox("選股票看K線", tickers)

    chart_mode = st.radio("K線週期", ["日K", "30分鐘", "5分鐘"], horizontal=True)

st.title("📈 Stock Radar Pro v2")
st.caption("左邊看盤｜右邊雷達與新聞｜可搜尋任意美股代碼｜每60秒自動刷新")

left, right = st.columns([7, 3])

with left:
    make_chart(selected_ticker, chart_mode)

with right:
    st.subheader("📊 股票雷達")
    df = scan_stocks(tickers)

    if df.empty:
        st.warning("目前抓不到股票資料。")
    else:
        st.dataframe(
            df[["Ticker", "Score", "Action", "RSI", "MA50%", "Tags"]].head(15),
            use_container_width=True,
            height=330
        )

        st.subheader("🔥 Top 5")
        for _, row in df.head(5).iterrows():
            st.markdown(
                f"""
                **{row['Ticker']}**｜{row['Action']}｜Score {row['Score']}  
                現價 {row['Close']}｜RSI {row['RSI']}｜MA50 {row['MA50%']}%  
                `{row['Tags']}`
                ---
                """
            )

    st.subheader("📰 即時新聞")
    articles = fetch_news()

    if not articles:
        st.info("尚未設定 NewsAPI key。先使用股票/K線功能。")
    else:
        for a in articles[:8]:
            title = a.get("title", "")
            source = a.get("source", {}).get("name", "")
            url = a.get("url", "")
            impact = judge_news(title)

            st.markdown(
                f"""
                **{impact}**  
                [{title}]({url})  
                `{source}`
                ---
                """
            )

st.caption(f"最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
