import time
import requests
import feedparser
import os
import re
from collections import defaultdict, Counter
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

THRESHOLD_RATIO = 0
TIME_WINDOW = 15
SCAN_INTERVAL = 10
AI_THRESHOLD = 10

sent_alerts = set()

# 🔥 NASDAQ veri
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

            clean_name = name.split(" inc")[0].split(" corp")[0]
            name_map[clean_name] = ticker

    return tickers, name_map

VALID_TICKERS, COMPANY_MAP = load_data()

def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# 🔥 GELİŞMİŞ TICKER SEÇİMİ
def extract_best_ticker(text):
    words = re.findall(r'\b[A-Z]{2,5}\b', text)
    lower = text.lower()

    candidates = []

    # ticker yakala
    for w in words:
        if w in VALID_TICKERS:
            candidates.append(w)

    # şirket adı yakala
    for name, ticker in COMPANY_MAP.items():
        if name in lower or name.split()[0] in lower:
            candidates.append(ticker)

    if not candidates:
        return None

    # en çok geçen ticker seç
    counter = Counter(candidates)
    return counter.most_common(1)[0][0]

# 🧠 AI skor
def ai_score(text):
    text = text.lower()
    score = 0

    if "approval" in text:
        score += 25
    if "acquisition" in text or "merger" in text:
        score += 30
    if "partnership" in text:
        score += 25
    if "contract" in text:
        score += 20
    if "investment" in text:
        score += 20
    if "earnings" in text:
        score += 30
    if "upgrade" in text:
        score += 20
    if "guidance" in text:
        score += 25

    if "offering" in text or "dilution" in text:
        score -= 50
    if "bankruptcy" in text:
        score -= 60

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

            ticker = extract_best_ticker(text)

            if not ticker:
                continue

            ticker_sources[ticker].add(i)
            ticker_texts[ticker] = text

    total = len(RSS_FEEDS)

    for ticker, sources in ticker_sources.items():

        # 🔥 minimum 1 kaynak şartı
        if len(sources) < 1:
            continue

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

📰 {ticker_texts[ticker]}"""

        send(msg)
        sent_alerts.add(ticker)

while True:
    try:
        check()
        time.sleep(SCAN_INTERVAL)
    except Exception as e:
        print("HATA:", e)
        time.sleep(20)