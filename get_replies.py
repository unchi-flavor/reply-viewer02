import requests
from requests.exceptions import SSLError, ConnectionError
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
import os
from dotenv import load_dotenv
import cloudscraper
from dateutil import parser  # ← NEW: 自由な日付フォーマット対応

load_dotenv()

class NitterRepliesCollector:
    def __init__(self):
        try:
            with open("nitter_instances.json", "r", encoding="utf-8") as f:
                self.nitter_instances = json.load(f)
        except:
            self.nitter_instances = [
                "https://nitter.poast.org",
                "https://nitter.catsarch.com",
                "https://nitter.zapashcanon.fr",
                "https://nitter.kavin.rocks",
                "https://nitter.salastil.com"
            ]
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.target_users = os.getenv('TARGET_USERS', 'elonmusk').split(',')
        self.max_tweets_per_user = int(os.getenv('MAX_TWEETS', '10'))
        self.scraper = cloudscraper.create_scraper()

    def find_working_instance(self):
        for instance in self.nitter_instances:
            try:
                test_url = f"{instance}/search?q=test"
                res = self.scraper.get(test_url, headers=self.headers, timeout=10)
                if res.status_code == 200 and "timeline" in res.text.lower():
                    return instance
            except SSLError as e:
                print(f"⚠️ SSLエラー: {instance} をスキップします ({e})")
                continue
            except ConnectionError as e:
                print(f"⚠️ 接続エラー: {instance} をスキップします ({e})")
                continue
            except Exception as e:
                print(f"⚠️ その他のエラー: {instance} ({e})")
                continue
        raise Exception("No working Nitter instance found.")    
    def get_user_tweet_urls(self, username, instance):
        url = f"{instance}/{username}"
        res = self.scraper.get(url, headers=self.headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        links = soup.select("a.tweet-link")
        tweet_urls = [instance + a['href'] for a in links[:self.max_tweets_per_user]]
        return tweet_urls

    def get_replies_to_tweet(self, tweet_url, username):
        print(f"🔍 Fetching replies for: {tweet_url}")
        res = self.scraper.get(tweet_url, headers=self.headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        replies = []

        for item in soup.find_all("div", class_="timeline-item"):
            user_elem = item.find("a", class_="username")
            if not user_elem or username.lower() in user_elem.text.lower():
                continue  # 自分のリプは除外

            text_elem = item.find("div", class_="tweet-content")
            date_elem = item.find("span", class_="tweet-date")
            if not text_elem or not date_elem:
                continue

            text = text_elem.get_text(strip=True)
            timestamp = date_elem.get("title") or date_elem.text.strip()
            replies.append({
                "username": user_elem.text.strip().lstrip('@'),
                "text": text,
                "timestamp": timestamp,
                "reply_to_id": tweet_url.split("/")[-1],  # ← NEW: 元ツイID
                "reply_url": tweet_url,
                "collected_at": datetime.now().isoformat()
            })
        return replies

    def collect_all_replies(self):
        instance = self.find_working_instance()
        all_replies = []
        for username in self.target_users:
            tweet_urls = self.get_user_tweet_urls(username.strip(), instance)
            for tweet_url in tweet_urls:
                replies = self.get_replies_to_tweet(tweet_url, username)
                all_replies.extend(replies)
                time.sleep(random.uniform(2, 4))
        cutoff = datetime.now() - timedelta(days=14)
        return [r for r in all_replies if self._within_range(r['timestamp'], cutoff)]

    def _within_range(self, timestamp_str, cutoff_dt):
        try:
            parsed = parser.parse(timestamp_str)
            return parsed >= cutoff_dt
        except:
            return False

    def save_replies(self, new_replies):
        if not new_replies:
            print("📭 No new replies to save.")
            return
        try:
            with open('replies.json', 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except FileNotFoundError:
            existing = []

        existing_keys = {r['text'][:100] for r in existing}
        uniques = [r for r in new_replies if r['text'][:100] not in existing_keys]

        combined = sorted(existing + uniques, key=lambda x: x['collected_at'], reverse=True)[:1000]
        with open('replies.json', 'w', encoding='utf-8') as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved {len(uniques)} new replies. Total: {len(combined)}")

def main():
    print(f"▶️ Start: {datetime.now().isoformat()}")
    collector = NitterRepliesCollector()
    try:
        replies = collector.collect_all_replies()
        collector.save_replies(replies)
        print("✅ Done.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
