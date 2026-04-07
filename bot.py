import snscrape.modules.twitter as sntwitter
import time
import requests
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ACCOUNTS = [
    "JohnZidar",
    "OsamaStocks",
    "trooper_trading",
    "MorningMadness4",
    "thejet_king",
    "DarkpoolAI",
    "mtm_trader",
    "ticker_guru",
    "NuntioBot",
    "WatcherGuru"
    
]

THRESHOLD = 1
TIME_WINDOW_MINUTES = 5

seen = set()
mentions = defaultdict(list)

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def get_words(text):
    words = re.findall(r"\b[A-Z]{2,5}\b", text)
    return words

def fetch_tweets():
    tweets = []
    for acc in ACCOUNTS:
        for tweet in sntwitter.TwitterUserScraper(acc).get_items():
            tweets.append(tweet)
            break  # sadece son tweet
    return tweets

while True:
    try:
        tweets = fetch_tweets()
        now = datetime.utcnow()

        for tweet in tweets:
            if tweet.id in seen:
                continue

            seen.add(tweet.id)
            words = get_words(tweet.content)

            for word in words:
                mentions[word].append(now)

                mentions[word] = [
                    t for t in mentions[word]
                    if now - t < timedelta(minutes=TIME_WINDOW_MINUTES)
                ]

                if len(mentions[word]) >= THRESHOLD:
                    msg = f"🚨 ALARM\n{word}\n{len(mentions[word])} hesap\nSon {TIME_WINDOW_MINUTES} dk"
                    send_telegram(msg)
                    mentions[word] = []

        time.sleep(30)

    except Exception as e:
        print("HATA:", e)
        time.sleep(60)
