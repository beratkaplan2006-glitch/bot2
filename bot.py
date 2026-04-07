import time
import requests
import feedparser
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://www.investing.com/rss/news.rss"
]

KEYWORDS = [
    "bitcoin",
    "ethereum",
    "sec",
    "etf",
    "breaking",
    "approval",
    "partnership"
]

sent_links = set()

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def check_news():
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:5]:
            title = entry.title.lower()
            link = entry.link

            if link in sent_links:
                continue

            if any(k in title for k in KEYWORDS):
                msg = f"🚨 HABER:\n{entry.title}\n{link}"
                send_telegram(msg)
                sent_links.add(link)

while True:
    try:
        check_news()
        time.sleep(60)  # 1 dakikada bir kontrol
    except Exception as e:
        print("Hata:", e)
        time.sleep(30)
