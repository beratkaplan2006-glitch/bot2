import time
import requests
import feedparser
import os
import re
from collections import defaultdict

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

RSS_FEEDS = [
    # SENİN İSTEDİKLER
    "https://www.globenewswire.com/RssFeed/orgclass/1/feedTitle/GlobeNewswire%20-%20News%20by%20Organization",
    "https://www.prnewswire.com/rss/news-releases-list.rss",
    "https://feeds.businesswire.com/rss/home/?rss=G1QFDERJXkJeEFJQV1Q=",

    # EK KAYNAKLAR
    "https://www.investing.com/rss/news_25.rss",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=market&region=US&lang=en-US"
]

THRESHOLD_RATIO = 0.5  # %50

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

    filtered = [w for w in words if w not in blacklist]

    return filtered

def check():
    ticker_sources = defaultdict(set)

    for i, url in enumerate(RSS_FEEDS):
        feed = feedparser.parse(url)

        for entry in feed.entries[:10]:
            text = entry.title.upper()

            tickers = extract_tickers(text)

            for t in tickers:
                ticker_sources[t].add(i)

    total_sources = len(RSS_FEEDS)

    for ticker, sources in ticker_sources.items():
        ratio = len(sources) / total_sources

        if ratio >= THRESHOLD_RATIO:
            if ticker in sent_alerts:
                continue

            msg = f"🚨 STRONG SIGNAL\n${ticker}\nKaynak: {len(sources)}/{total_sources}"
            send(msg)

            sent_alerts.add(ticker)

while True:
    try:
        check()
        time.sleep(30)
    except Exception as e:
        print(e)
        time.sleep(60)
