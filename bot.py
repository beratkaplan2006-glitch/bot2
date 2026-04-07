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

TWITTER_ACCOUNTS = [
    "unusual_whales",
    "DeItaone",
    "zerohedge",
    "BreakingStocks",
    "StockMKTNewz"
]

TIME_WINDOW = 10
SCAN_INTERVAL = 15
AI_THRESHOLD = 40

sent_alerts = set()

# 🔥 NASDAQ verisi
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

    if "fda approval" in text:
        score += 60
    if "acquisition" in text or "buyout" in text:
        score += 50
    if "merger" in text:
        score += 45
    if "partnership" in text:
        score += 30
    if "contract" in text:
        score += 30
    if "earnings" in text:
        score += 40
    if "upgrade" in text:
        score += 25

    if "million" in text:
        score += 10
    if "billion" in text:
        score += 20

    if "offering" in text or "dilution" in text:
        score -= 60

    return max(0, min(score, 100))

# 📊 pump ihtimali
def pump_probability(score, sources):
    prob = score
    if sources >= 2:
        prob += 10
    if sources >= 3:
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

        prob = pump_probability(score, len(sources))

        if ticker in sent_alerts:
            continue

        msg = f"""🚨 ONAYLI (News)
💰 ${ticker}
🧠 Skor: {score}
📊 Pump: %{prob}
📡 Kaynak: {len(sources)}

📰 {ticker_texts[ticker]}"""

        send(msg)
        sent_alerts.add(ticker)

# 🔥 TWITTER (CRASH PROTECTION)
def check_twitter():
    try:
        import snscrape.modules.twitter as sntwitter
    except:
        print("Twitter modülü yok")
        return

    ticker_count = defaultdict(int)

    for user in TWITTER_ACCOUNTS:
        try:
            tweets = sntwitter.TwitterUserScraper(user).get_items()

            for i, tweet in enumerate(tweets):
                if i > 0:
                    break

                text = tweet.content
                tickers = re.findall(r'\$([A-Z]{2,5})', text)

                for t in tickers:
                    ticker_count[t] += 1

        except Exception as e:
            print("Twitter hata:", e)
            continue

    for ticker, count in ticker_count.items():
        if count >= 2:
            send(f"""⚠️ ERKEN (Twitter)
💰 ${ticker}
📊 {count} hesapta geçti""")

# 🔁 LOOP
while True:
    try:
        check_news()
        check_twitter()
        time.sleep(SCAN_INTERVAL)
    except Exception as e:
        print("GENEL HATA:", e)
        time.sleep(20)