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

THRESHOLD_RATIO = 0.2
TIME_WINDOW = 10
SCAN_INTERVAL = 10
AI_THRESHOLD = 10

sent_alerts = set()

# 🔥 NASDAQ + şirket adı
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

            simple = name.split(" inc")[0].split(" corp")[0]
            name_map[simple] = ticker

    return tickers, name_map

VALID_TICKERS, COMPANY_MAP = load_data()
print(f"{len(VALID_TICKERS)} ticker yüklendi")

def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# 🔥 GELİŞTİRİLMİŞ TICKER BULMA
def extract_tickers(text):
    found = set()

    words = re.findall(r'\b[A-Z]{2,5}\b', text)
    for w in words:
        if w in VALID_TICKERS:
            found.add(w)

    lower_text = text.lower()

    for name, ticker in COMPANY_MAP.items():
        if name in lower_text or name.split()[0] in lower_text:
            found.add(ticker)

    return list(found)

# 🧠 AI SKOR
def ai_score(text):
    text = text.lower()
    score = 0

    if "approval" in text:
        score += 25
    if "acquisition" in text or "merger" in text:
        score += 30
    if "partnership" in text:
        score += 20
    if "contract" in text:
        score += 20
    if "earnings" in text:
        score += 25
    if "upgrade" in text:
        score += 15

    if "offering" in text or "dilution" in text:
        score -= 40

    return max(0, min(score, 100))

def check():
    ticker_sources = defaultdict(set)
    ticker_texts = {}

    now = datetime.utcnow()

    for i, url in enumerate(RSS_FEEDS):
        feed = feedparser.parse(url)

        for entry in feed.entries[:10]:

            text = entry.title
            print("HABER:", text)  # DEBUG

            if hasattr(entry, "published_parsed"):
                published = datetime(*entry.published_parsed[:6])
                if now - published > timedelta(minutes=TIME_WINDOW):
                    continue

            tickers = extract_tickers(text)

            if not tickers:
                print("TICKER YOK:", text)  # DEBUG

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
${ticker}
Skor: {score}/100
Kaynak: {len(sources)}/{total}

{ticker_texts[ticker]}"""

        send(msg)
        print("GÖNDERİLDİ:", ticker)  # DEBUG

        sent_alerts.add(ticker)

while True:
    try:
        check()
        time.sleep(SCAN_INTERVAL)
    except Exception as e:
        print("HATA:", e)
        time.sleep(20)