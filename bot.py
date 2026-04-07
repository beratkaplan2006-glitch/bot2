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

THRESHOLD_RATIO = 0.0
TIME_WINDOW = 5  # dakika
SCAN_INTERVAL = 15  # saniye
AI_THRESHOLD = 0

sent_alerts = set()

def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def extract_tickers(text):
    words = re.findall(r'\b[A-Z]{2,5}\b', text)

    blacklist = {
        "THE","AND","FOR","WITH","FROM","THIS","THAT","WILL","ARE","HAS",
        "INC","LTD","LLC","PLC","NEW","CEO","USA","USD","NOT","BUT","ALL",
        "OUT","NOW","ONE","TWO","BUY","SELL","TOP","LOW","HIGH","OVER",
        "UNDER","AFTER","BEFORE","INTO","ONTO","ABOUT","OF","IN","TO","BY"
    }

    return [w for w in words if w not in blacklist]

# 🧠 AI SKOR FONKSİYONU
def ai_score(text):
    text = text.lower()
    score = 0

    positive = {
        "fda approval": 40,
        "approval": 25,
        "acquisition": 30,
        "merger": 30,
        "partnership": 20,
        "contract": 20,
        "agreement": 15,
        "investment": 15,
        "buyout": 30,
        "award": 15,
        "launch": 10,
        "expansion": 15,
        "breakthrough": 25,
        "earnings beat": 30,
        "guidance raised": 25,
        "upgrade": 20
    }

    negative = {
        "offering": -30,
        "dilution": -40,
        "bankruptcy": -50,
        "downgrade": -25,
        "lawsuit": -20,
        "delay": -15
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

            # ⏱️ zaman filtresi
            if hasattr(entry, "published_parsed"):
                published = datetime(*entry.published_parsed[:6])
                if now - published > timedelta(minutes=TIME_WINDOW):
                    continue

            text = entry.title
            upper = text.upper()

            tickers = extract_tickers(upper)

            for t in tickers:
                ticker_sources[t].add(i)
                ticker_texts[t] = text

    total_sources = len(RSS_FEEDS)

    for ticker, sources in ticker_sources.items():
        ratio = len(sources) / total_sources

        if ratio >= THRESHOLD_RATIO:

            score = ai_score(ticker_texts[ticker])

            if score < AI_THRESHOLD:
                continue

            if ticker in sent_alerts:
                continue

            msg = f"🚨 STRONG SIGNAL\n${ticker}\nSkor: {score}/100\nKaynak: {len(sources)}/{total_sources}"
            send(msg)

            sent_alerts.add(ticker)

while True:
    try:
        check()
        time.sleep(SCAN_INTERVAL)
    except Exception as e:
        print("Hata:", e)
        time.sleep(30)
