# Stock Radar Dashboard

這是一個 Streamlit 股票看盤 Dashboard：
- 股票雷達：分數、RSI、均線、成交量、參考停損
- 新聞雷達：可接 NewsAPI

## Streamlit Cloud 部署
1. 建 GitHub repo
2. 上傳 app.py 和 requirements.txt
3. 到 Streamlit Community Cloud 建立 App
4. Main file path 填 app.py

## NewsAPI
如果要啟用新聞：
在 Streamlit App 的 Settings > Secrets 加入：
NEWS_API_KEY = "你的NewsAPI_KEY"
