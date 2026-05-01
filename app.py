import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(page_title="Stock Radar Pro", layout="wide")

st.title("📈 Stock Radar Pro")
st.caption("股票雷達 + K線 + 成交量 + RSI + 支撐壓力 + 進出場參考")

DEFAULT_TICKERS = [
    "NVDA", "AMD", "AVGO", "TSM", "MSFT", "GOOGL", "AMZN", "META", "AAPL",
    "ETN", "VRT", "PWR", "CEG", "NEE", "GEV", "CAT",
    "LMT", "RTX", "NOC", "GD",
    "LLY", "NVO", "ISRG", "UNH",
    "JPM", "V", "MA", "COST", "WMT",
    "XOM", "CVX", "COP"
]

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def fetch_data(ticker, period="1y"):
    try:
        data = yf.Ticker(ticker).history(period=period, interval="1d")
        return data
    except:
        return pd.DataFrame()

def analyze_one(ticker):
    data = fetch_data(ticker, "1y")
    if data.empty or len(data) < 200:
        return None

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
    vol_ratio = latest["Volume"] / latest["VolAvg20"] if latest["VolAvg20"] > 0 else 0
    high20 = latest["High20"]

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

    if 45 <= rsi <= 65:
        score += 10
        tags.append("RSI健康")
    elif rsi > 75:
        score -= 15
        tags.append("RSI過熱")
    elif rsi < 35:
        score += 5
        tags.append("可能跌深")

    distance_ma50 = (close / ma50 - 1) * 100

    if distance_ma50 > 15:
        score -= 15
        tags.append("離MA50太遠，追高風險")
    elif distance_ma50 < -10:
        tags.append("跌破MA50，偏弱")

    support = data["Low"].tail(20).min()
    resistance = data["High"].tail(20).max()

    stop_loss = support * 0.98
    target_1 = resistance
    target_2 = close + (close - stop_loss) * 2

    if score >= 65 and rsi < 75 and distance_ma50 < 15:
        action = "🔥 可觀察進場"
    elif score >= 45:
        action = "🟡 等回調 / 等突破"
    else:
        action = "⚪ 暫不碰"

    return {
        "Ticker": ticker,
        "Close": round(close, 2),
        "Score": score,
        "Action": action,
        "RSI": round(rsi, 1),
        "Vol_Ratio": round(vol_ratio, 2),
        "Distance_MA50_%": round(distance_ma50, 2),
        "Support": round(support, 2),
        "Resistance": round(resistance, 2),
        "Stop_Loss": round(stop_loss, 2),
        "Target_1": round(target_1, 2),
        "Target_2": round(target_2, 2),
        "Tags": ", ".join(tags)
    }

def make_chart(ticker):
    data = fetch_data(ticker, "1y")

    if data.empty:
        st.warning("抓不到K線資料")
        return

    data["MA20"] = data["Close"].rolling(20).mean()
    data["MA50"] = data["Close"].rolling(50).mean()
    data["MA200"] = data["Close"].rolling(200).mean()
    data["RSI"] = calc_rsi(data["Close"])

    support = data["Low"].tail(20).min()
    resistance = data["High"].tail(20).max()
    latest_close = data["Close"].iloc[-1]

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f"{ticker} K線圖", "成交量", "RSI")
    )

    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data["Open"],
        high=data["High"],
        low=data["Low"],
        close=data["Close"],
        name="K線"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["MA20"],
        mode="lines",
        name="MA20"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["MA50"],
        mode="lines",
        name="MA50"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["MA200"],
        mode="lines",
        name="MA200"
    ), row=1, col=1)

    fig.add_hline(y=support, line_dash="dash", annotation_text="支撐", row=1, col=1)
    fig.add_hline(y=resistance, line_dash="dash", annotation_text="壓力", row=1, col=1)

    fig.add_trace(go.Bar(
        x=data.index,
        y=data["Volume"],
        name="成交量"
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["RSI"],
        mode="lines",
        name="RSI"
    ), row=3, col=1)

    fig.add_hline(y=70, line_dash="dot", annotation_text="RSI 70 過熱", row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", annotation_text="RSI 30 跌深", row=3, col=1)

    fig.update_layout(
        height=850,
        xaxis_rangeslider_visible=False,
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

    stop_loss = support * 0.98
    target_1 = resistance
    risk = latest_close - stop_loss
    reward = target_1 - latest_close
    rr = reward / risk if risk > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("現價", round(latest_close, 2))
    col2.metric("支撐", round(support, 2))
    col3.metric("壓力", round(resistance, 2))
    col4.metric("風險報酬比", round(rr, 2))

    st.markdown("### 🎯 交易參考")
    st.write(f"停損參考：**{round(stop_loss, 2)}**")
    st.write(f"第一目標：**{round(target_1, 2)}**")
    st.write(f"第二目標：**{round(latest_close + risk * 2, 2)}**")

    if rr >= 1.5:
        st.success("風險報酬比不錯，可以列入觀察。")
    elif rr > 0:
        st.warning("風險報酬比普通，建議等更好的進場點。")
    else:
        st.error("目前不適合追，可能離壓力太近。")

with st.sidebar:
    st.header("設定")
    ticker_input = st.text_area("股票清單，用逗號分隔", ",".join(DEFAULT_TICKERS), height=160)
    tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]
    selected = st.selectbox("選股票看K線", tickers)

st.header("📊 股票雷達")

results = []
for t in tickers:
    item = analyze_one(t)
    if item:
        results.append(item)

df = pd.DataFrame(results)

if df.empty:
    st.warning("目前沒有抓到股票資料，可能是 Yahoo Finance 暫時擋資料，稍後再重新整理。")
else:
    df = df.sort_values("Score", ascending=False)
    st.dataframe(df, use_container_width=True)

    st.subheader("🔥 今日前10名")
    for _, row in df.head(10).iterrows():
        st.markdown(
            f"""
            **{row['Ticker']}**｜{row['Action']}｜Score: **{row['Score']}**  
            現價：{row['Close']}｜RSI：{row['RSI']}｜距離MA50：{row['Distance_MA50_%']}%  
            支撐：{row['Support']}｜壓力：{row['Resistance']}｜停損：{row['Stop_Loss']}  
            目標1：{row['Target_1']}｜目標2：{row['Target_2']}  
            `{row['Tags']}`
            ---
            """
        )

st.header("📉 K線看盤區")
make_chart(selected)

st.header("📰 即時新聞雷達")
st.info("新聞AI分析下一版再接 NewsAPI / Finnhub。這版先把K線交易功能做好。")

st.caption(f"最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
