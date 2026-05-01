import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime

st.set_page_config(page_title="Stock Radar", layout="wide")
st.title("📈 Stock Radar Dashboard")
st.caption("股票雷達 + 即時新聞雷達｜手機可用版")

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

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=900)
def analyze_stocks(tickers):
    results = []
    for ticker in tickers:
        try:
            data = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
            if data.empty or len(data) < 200:
                continue

            data["MA20"] = data["Close"].rolling(20).mean()
            data["MA50"] = data["Close"].rolling(50).mean()
            data["MA200"] = data["Close"].rolling(200).mean()
            data["RSI"] = calculate_rsi(data["Close"])
            data["Vol_Avg20"] = data["Volume"].rolling(20).mean()
            data["High_20"] = data["High"].rolling(20).max()

            latest = data.iloc[-1]
            close = float(latest["Close"])
            ma20 = float(latest["MA20"])
            ma50 = float(latest["MA50"])
            ma200 = float(latest["MA200"])
            rsi = float(latest["RSI"])
            volume = float(latest["Volume"])
            vol_avg20 = float(latest["Vol_Avg20"])
            high20 = float(latest["High_20"])

            change_5d = (close / float(data["Close"].iloc[-6]) - 1) * 100
            change_20d = (close / float(data["Close"].iloc[-21]) - 1) * 100
            distance_ma50 = (close / ma50 - 1) * 100
            volume_ratio = volume / vol_avg20 if vol_avg20 > 0 else 0

            score = 0
            tags = []

            if close > ma20:
                score += 10; tags.append("站上MA20")
            if close > ma50:
                score += 15; tags.append("站上MA50")
            if close > ma200:
                score += 15; tags.append("站上MA200")
            if close >= high20 * 0.995:
                score += 20; tags.append("接近20日新高")
            if volume_ratio > 1.5:
                score += 15; tags.append("成交量放大")

            if 45 <= rsi <= 65:
                score += 10; tags.append("RSI健康")
            elif rsi > 75:
                score -= 15; tags.append("RSI過熱")
            elif rsi < 35:
                score += 5; tags.append("可能跌深")

            if distance_ma50 > 15:
                score -= 15; tags.append("追高風險")
            elif distance_ma50 < -10:
                tags.append("跌破MA50偏弱")

            if change_5d > 3:
                score += 5; tags.append("短線轉強")
            if change_20d > 8:
                score += 5; tags.append("月線動能強")

            if score >= 65:
                action = "🔥 Buy Watch"
            elif score >= 45:
                action = "🟡 Wait"
            else:
                action = "⚪ Avoid Now"

            # 粗略停損參考：MA20/MA50 之中較接近下方支撐
            stop_loss = min(ma20, ma50) * 0.98

            results.append({
                "Ticker": ticker,
                "Close": round(close, 2),
                "Score": score,
                "Action": action,
                "RSI": round(rsi, 1),
                "5D_%": round(change_5d, 2),
                "20D_%": round(change_20d, 2),
                "Vol_Ratio": round(volume_ratio, 2),
                "Distance_MA50_%": round(distance_ma50, 2),
                "Stop_Loss_Ref": round(stop_loss, 2),
                "Tags": ", ".join(tags)
            })
        except Exception:
            pass

    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values("Score", ascending=False)
    return df

@st.cache_data(ttl=300)
def fetch_news():
    api_key = ""
    try:
        api_key = st.secrets.get("NEWS_API_KEY", "")
    except Exception:
        pass

    if not api_key:
        return []

    query = " OR ".join(NEWS_KEYWORDS)
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 20,
        "apiKey": api_key
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json().get("articles", [])
    except Exception:
        return []

def simple_news_impact(title):
    title_lower = title.lower()
    bearish_words = ["tariff", "ban", "sanction", "war", "inflation", "rate hike", "export restriction"]
    bullish_words = ["rate cut", "deal", "approval", "contract", "stimulus", "record", "beats estimates"]

    if any(w in title_lower for w in bearish_words):
        return "🔴 偏利空 / 風險新聞"
    if any(w in title_lower for w in bullish_words):
        return "🟢 偏利多 / 正面新聞"
    return "🟡 中性 / 需觀察"

with st.sidebar:
    st.header("設定")
    tickers_input = st.text_area("股票清單，用逗號分隔", ",".join(DEFAULT_TICKERS), height=150)
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    st.caption("資料每 15 分鐘快取一次；新聞每 5 分鐘快取一次。")
    st.button("重新整理")

left, right = st.columns([2, 1])

with left:
    st.subheader("📊 股票雷達")
    df = analyze_stocks(tickers)

    if df.empty:
        st.warning("目前沒有抓到股票資料。")
    else:
        st.metric("掃描股票數", len(df))
        st.dataframe(df.head(30), use_container_width=True)

        st.subheader("🔥 今日最值得關注")
        for _, row in df.head(10).iterrows():
            st.markdown(f"""
**{row['Ticker']}**｜{row['Action']}｜Score: **{row['Score']}**  
價格: {row['Close']}｜RSI: {row['RSI']}｜距離MA50: {row['Distance_MA50_%']}%｜參考停損: {row['Stop_Loss_Ref']}  
`{row['Tags']}`
---
""")

        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("下載完整 CSV 報告", csv, "stock_radar_report.csv", "text/csv")

with right:
    st.subheader("📰 即時新聞雷達")
    articles = fetch_news()
    if not articles:
        st.info("尚未設定 NewsAPI key，或目前抓不到新聞。先跑股票雷達也可以。")
    else:
        for a in articles[:15]:
            title = a.get("title", "")
            source = a.get("source", {}).get("name", "")
            url = a.get("url", "")
            published = a.get("publishedAt", "")
            impact = simple_news_impact(title)
            st.markdown(f"""
**{impact}**  
[{title}]({url})  
來源：{source}  
時間：{published}
---
""")

st.caption(f"最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
