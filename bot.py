import time
import requests
import feedparser
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

RSS_FEEDS = [
    "https://financialjuice.com/feed",
    "https://www.investing.com/rss/news.rss",
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/"
]

KEYWORDS = [
    "breaking",
    "sec",
    "etf",
    "bitcoin",
    "ethereum",
    "approval",
    "fed",
    "interest rate"
]

sent = set()

def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def check():
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)

        for entry in feed.entries[:5]:
            title = entry.title.lower()
            link = entry.link

            if link in sent:
                continue

            if any(k in title for k in KEYWORDS):
                msg = f"🚨 {entry.title}\n{link}"
                send(msg)
                sent.add(link)

while True:
    try:
        check()
        time.sleep(30)
    except Exception as e:
        print(e)
        time.sleep(60)
