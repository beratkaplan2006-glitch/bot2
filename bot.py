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
    "https://feeds.businesswire.com/rss/home/?rss=G1QFDERJXkJeEFJQV1Q="
]

SEC_FEED = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&count=20&output=atom"

TIME_WINDOW = 10
SCAN_INTERVAL = 15
AI_THRESHOLD = 40

sent_alerts = set()
sent_sec = set()

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

            clean = name.split(" inc")[0].split(" corp")[0]
            name_map[clean] = ticker

    return tickers, name_map

VALID_TICKERS, COMPANY_MAP = load_data()

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        print("Telegram hata")

# 🔥 ticker bul
def extract_best_ticker(text):
    words = re.findall(r'\b[A-Z]{2,5}\b', text)
    lower = text.lower()

    candidates = []

    for w in words:
        if w in VALID_TICKERS:
            candidates.append(w)

    for name, ticker in COMPANY_MAP.items():
        if name in lower:
            candidates.append(ticker)

    for name, ticker in COMPANY_MAP.items():
        for part in name.split():
            if part in lower:
                candidates.append(ticker)

    if not candidates:
        return None

    return Counter(candidates).most_common(1)[0][0]

# 🧠 AI skor
def ai_score(text):
    text = text.lower()
    score = 0

    if "acquisition" in text or "merger" in text:
        score += 50
    if "agreement" in text:
        score += 30
    if "contract" in text:
        score += 30
    if "earnings" in text:
        score += 40
    if "upgrade" in text:
        score += 25

    if "bankruptcy" in text:
        score -= 80
    if "offering" in text:
        score -= 50

    return max(0, min(score, 100))

# 📊 pump ihtimali
def pump_probability(score, sources):
    prob = score
    if sources >= 2:
        prob += 10
    return min(prob, 100)

# 🔥 NEWS
def check_news():
    ticker_sources = defaultdict(set)
    ticker_texts = {}

    now = datetime.utcnow()

    for i, url in enumerate(RSS_FEEDS):
        try:
            feed = feedparser.parse(url)
        except:
            continue

        for entry in feed.entries[:10]:

            try:
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
            except:
                continue

    for ticker, sources in ticker_sources.items():

        if len(sources) < 2:
            continue

        score = ai_score(ticker_texts[ticker])
        if score < AI_THRESHOLD:
            continue

        if ticker in sent_alerts:
            continue

        prob = pump_probability(score, len(sources))

        msg = f"""🚨 ONAYLI (NEWS)
💰 ${ticker}
🧠 Skor: {score}
📊 Pump: %{prob}
📡 Kaynak: {len(sources)}

📰 {ticker_texts[ticker]}"""

        send(msg)
        sent_alerts.add(ticker)

# 🔥 SEC (ERKEN)
def check_sec():
    try:
        feed = feedparser.parse(SEC_FEED)
    except:
        return

    for entry in feed.entries[:10]:

        title = entry.title

        if title in sent_sec:
            continue

        ticker = extract_best_ticker(title)

        if not ticker:
            continue

        msg = f"""⚠️ ERKEN (SEC)
💰 ${ticker}

📄 {title}"""

        send(msg)
        sent_sec.add(title)

# 🔁 LOOP
while True:
    try:
        try:
            check_news()
        except Exception as e:
            print("News hata:", e)

        try:
            check_sec()
        except Exception as e:
            print("SEC hata:", e)

        time.sleep(SCAN_INTERVAL)

    except Exception as e:
        print("GENEL HATA:", e)
        time.sleep(20)