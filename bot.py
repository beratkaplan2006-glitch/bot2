import requests
import time
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta

# ENV
BEARER_TOKEN = os.getenv("AAAAAAAAAAAAAAAAAAAAAAM108wEAAAAAA
RvBp1bcjGKdZEn0uхM1c2Np0WBg%3DYRSj
5Fu0J3zUrRPnBBQqAGWr63UleL0Xp9CB2v
NImXuNsAp014")
TELEGRAM_TOKEN = os.getenv("8490901735:AAHmEvwjOfv7flUWzm3DN10x52IaI9ci-wg")
CHAT_ID = os.getenv("6947368351")

# Hesaplar
ACCOUNTS = [
    "JohnZidar","OsamaStocks","trooper_trading","MorningMadness4",
    "thejet_king","DarkpoolAI","mtm_trader","ticker_guru","NuntioBot"
]

# Ayarlar
THRESHOLD = 2  # test için (sonra 5 yap)
TIME_WINDOW_MINUTES = 3
COOLDOWN_MINUTES = 10

last_alert_time = {}

# Telegram gönder
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# User ID al
def get_user_id(username):
    url = f"https://api.twitter.com/2/users/by/username/{username}"
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    r = requests.get(url, headers=headers).json()
    return r["data"]["id"]

# Tweet al
def get_tweets(user_id):
    url = f"https://api.twitter.com/2/users/{user_id}/tweets"
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    params = {
        "max_results": 5,
        "tweet.fields": "created_at"
    }
    return requests.get(url, headers=headers, params=params).json()

# Ticker yakala
def extract_words(text):
    return re.findall(r'\b[A-Z]{3,6}\b', text)

# ID'leri çek
user_ids = {acc: get_user_id(acc) for acc in ACCOUNTS}

# Ana döngü
while True:
    word_map = defaultdict(set)
    now = datetime.utcnow()

    for acc, uid in user_ids.items():
        data = get_tweets(uid)

        if "data" not in data:
            continue

        for tweet in data["data"]:
            tweet_time = datetime.strptime(tweet["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ")

            if now - tweet_time > timedelta(minutes=TIME_WINDOW_MINUTES):
                continue

            text = tweet["text"]

            for w in extract_words(text):
                word_map[w].add(acc)

    for word, users in word_map.items():
        if len(users) >= THRESHOLD:
            last_time = last_alert_time.get(word)

            if last_time and (now - last_time < timedelta(minutes=COOLDOWN_MINUTES)):
                continue

            msg = f"🚨 ALARM\n{word}\n{len(users)} hesap\nSon {TIME_WINDOW_MINUTES} dk"
            send_telegram(msg)

            last_alert_time[word] = now

    time.sleep(60)
