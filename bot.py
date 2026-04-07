import time
import requests
import feedparser
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

RSS_FEEDS = [
    "https://www.globenewswire.com/RssFeed/orgclass/1/feedTitle/GlobeNewswire%20-%20News%20by%20Organization",
    "https://www.prnewswire.com/rss/news-releases-list.rss",
    "https://feeds.businesswire.com/rss/home/?rss=G1QFDERJXkJeEFJQV1Q=",
    "https://www.investing.com/rss/news_25.rss",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=market&region=US&lang=en-US"
]

THRESHOLD_RATIO = 0.25
TIME_WINDOW = 5
SCAN_INTERVAL = 10
AI_THRESHOLD = 50

sent_alerts = set()

# 🔥 NASDAQ çek
def load_data():
    url = "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"
    r = requests.get(url)
    lines = r.text.split("\n")[1:]

    tickers = set()
    name_map = {}

    for line in lines:
        parts = line.split(",")
        if len(parts) > 1:
            ticker = parts[0].strip()
            name = parts[1].lower()

            tickers.add(ticker)

            # şirket adı parçalama (daha güçlü eşleşme)
            simple_name = name.split(" inc")[0].split(" corp")[0]
            name_map[simple_name] = ticker

    return tickers, name_map

VALID_TICKERS, COMPANY_MAP = load_data()

def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# 🔥 TICKER + ŞİRKET ADI
def extract_tickers(text):
    found = set()

    # ticker yakalama
    words = re.findall(r'\b[A-Z]{2,5}\b', text)
    for w in words:
        if w in VALID_TICKERS:
            found.add(w)

    # şirket adı yakalama
    lower_text = text.lower()
    for name, ticker in COMPANY_MAP.items():
        if name in lower_text:
            found.add(ticker)

    return list(found)

# 🔥 AI SKOR
def ai_score(text):
    text = text.lower()
    score = 0

    positive = {
        "fda approval": 40,
        "approval": 25,
        "acquisition": 30,
        "merger": 30,
        "partnership": 25,
        "contract": 20,
        "investment": 20,
        "buyout": 30,
        "earnings beat": 35,
        "guidance raised": 30,
        "upgrade": 25,
        "expansion": 20
    }

    negative = {
        "offering": -40,
        "dilution": -50,
        "bankruptcy": -60,
        "downgrade": -30,
        "lawsuit": -25
    }

    for k, v in positive.items():
        if k in text:
            score += v

    for k, v in negative.items():
        if k in text:
            score += v

    return max(0, min(score, 100))

def check():
    ticker_sources = defaultdict(set)
    ticker_texts = {}

    now = datetime.utcnow()

    for i, url in enumerate(RSS_FEEDS):
        feed = feedparser.parse(url)

        for entry in feed.entries[:10]:

            if hasattr(entry, "published_parsed"):
                published = datetime(*entry.published_parsed[:6])
                if now - published > timedelta(minutes=TIME_WINDOW):
                    continue

            text = entry.title

            tickers = extract_tickers(text)

            for t in tickers:
                ticker_sources[t].add(i)
                ticker_texts[t] = text

    total = len(RSS_FEEDS)

    for ticker, sources in ticker_sources.items():
        ratio = len(sources) / total

        if ratio < THRESHOLD_RATIO:
            continue

        score = ai_score(ticker_texts[ticker])

        if score < AI_THRESHOLD:
            continue

        if ticker in sent_alerts:
            continue

        msg = f"""🚨 STRONG SIGNAL
💰 ${ticker}
🧠 Skor: {score}/100
📡 Kaynak: {len(sources)}/{total}

📰 {ticker_texts[ticker]}
"""

        send(msg)
        sent_alerts.add(ticker)

send("bot aktif")

while True:
    try:
        check()
        time.sleep(SCAN_INTERVAL)
    except Exception as e:
        print("Hata:", e)
        time.sleep(20)
