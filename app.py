import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Stock Radar", layout="wide")

st.title("📈 Stock Radar Dashboard")
st.caption("股票雷達 + 即時新聞雷達｜手機可用版")

tickers = [
    "NVDA", "AMD", "AVGO", "TSM", "MSFT", "GOOGL", "AMZN", "META", "AAPL",
    "ETN", "VRT", "PWR", "CEG", "NEE", "GEV", "CAT",
    "LMT", "RTX", "NOC", "GD",
    "LLY", "NVO", "ISRG", "UNH",
    "JPM", "V", "MA", "COST", "WMT",
    "XOM", "CVX", "COP"
]

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

results = []

for ticker in tickers:
    try:
        data = yf.Ticker(ticker).history(period="1y", interval="1d")

        if data.empty or len(data) < 200:
            continue

        data["MA20"] = data["Close"].rolling(20).mean()
        data["MA50"] = data["Close"].rolling(50).mean()
        data["MA200"] = data["Close"].rolling(200).mean()
        data["RSI"] = rsi(data["Close"])
        data["High20"] = data["High"].rolling(20).max()
        data["VolAvg20"] = data["Volume"].rolling(20).mean()

        latest = data.iloc[-1]

        close = latest["Close"]
        ma20 = latest["MA20"]
        ma50 = latest["MA50"]
        ma200 = latest["MA200"]
        latest_rsi = latest["RSI"]
        high20 = latest["High20"]
        vol_ratio = latest["Volume"] / latest["VolAvg20"]

        score = 0
        tags = []

        if close > ma20:
            score += 10
            tags.append("站上MA20")
        if close > ma50:
            score += 15
            tags.append("站上MA50")
        if close > ma200:
            score += 15
            tags.append("站上MA200")
        if close >= high20 * 0.995:
            score += 20
            tags.append("接近20日新高")
        if vol_ratio > 1.5:
            score += 15
            tags.append("成交量放大")

        if 45 <= latest_rsi <= 65:
            score += 10
            tags.append("RSI健康")
        elif latest_rsi > 75:
            score -= 15
            tags.append("RSI過熱")
        elif latest_rsi < 35:
            score += 5
            tags.append("可能跌深")

        distance_ma50 = (close / ma50 - 1) * 100
        if distance_ma50 > 15:
            score -= 15
            tags.append("追高風險")

        if score >= 65:
            action = "🔥 Buy Watch"
        elif score >= 45:
            action = "🟡 Wait"
        else:
            action = "⚪ Avoid Now"

        results.append({
            "Ticker": ticker,
            "Close": round(close, 2),
            "Score": score,
            "Action": action,
            "RSI": round(latest_rsi, 1),
            "Vol_Ratio": round(vol_ratio, 2),
            "Distance_MA50_%": round(distance_ma50, 2),
            "Tags": ", ".join(tags)
        })

    except Exception as e:
        st.write(f"{ticker} error: {e}")

df = pd.DataFrame(results)

st.header("📊 股票雷達")

if df.empty:
    st.warning("目前沒有抓到股票資料，可能是 Yahoo Finance 暫時擋資料，稍後重新整理。")
else:
    df = df.sort_values("Score", ascending=False)
    st.dataframe(df, use_container_width=True)

    st.subheader("🔥 今日前10名")
    for _, row in df.head(10).iterrows():
        st.markdown(
            f"""
            **{row['Ticker']}**｜{row['Action']}｜Score: **{row['Score']}**  
            價格：{row['Close']}｜RSI：{row['RSI']}｜距離MA50：{row['Distance_MA50_%']}%  
            `{row['Tags']}`
            ---
            """
        )

st.header("📰 即時新聞雷達")
st.info("新聞功能下一步再接 NewsAPI key。")

st.caption(f"最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
