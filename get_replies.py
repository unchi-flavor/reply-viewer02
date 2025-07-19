import requests
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
import os
from dotenv import load_dotenv

load_dotenv()

class NitterRepliesCollector:
    def __init__(self):
        self.nitter_instances = [
            "https://nitter.poast.org",
            "https://nitter.privacydev.net",
            "https://nitter.net",
            "https://n.opnxng.com",
            "https://nitter.it"
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        }
        self.target_users = os.getenv('TARGET_USERS', 'elonmusk').split(',')
        self.max_tweets_per_user = int(os.getenv('MAX_TWEETS', '50'))

    def find_working_instance(self):
        for instance in self.nitter_instances:
            try:
                test_url = f"{instance}/search?f=tweets&q=test"
                response = requests.get(test_url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    print(f"✅ Using nitter instance: {instance}")
                    return instance
            except requests.RequestException:
                continue
        raise Exception("❌ No working nitter instances available")

    def get_user_timeline(self, username, instance):
        try:
            url = f"{instance}/{username}"
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"❌ Error fetching timeline for {username}: {e}")
            return None

    def parse_timeline(self, html, username):
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        containers = soup.find_all('div', class_='timeline-item')
        replies = []

        for container in containers[:self.max_tweets_per_user]:
            try:
                tweet = self.extract_tweet_data(container, username)
                if tweet and tweet['is_reply']:
                    replies.append(tweet)
            except Exception as e:
                print(f"⚠️ Tweet parse error: {e}")
        return replies

    def extract_tweet_data(self, container, username):
        content = container.find('div', class_='tweet-content')
        if not content:
            return None
        text_elem = content.find('div', class_='tweet-text')
        if not text_elem:
            return None
        text = text_elem.get_text(strip=True)

        date_elem = container.find('span', class_='tweet-date')
        timestamp = date_elem.get('title') if date_elem else None

        tweet_link = container.find('a', class_='tweet-link')
        tweet_id = None
        reply_to_id = None
        if tweet_link:
            href = tweet_link.get('href', '')
            match = re.search(r'/status/(\d+)', href)
            if match:
                tweet_id = match.group(1)
            # reply_to_id は取れない場合が多いため今は保留
            # 取得したい場合はツイート本文中の "@xxxx" を元に処理が必要

        reply_url = f"https://twitter.com/{username}/status/{tweet_id}" if tweet_id else None

        return {
            'id': tweet_id,
            'username': username,
            'text': text,
            'timestamp': timestamp,
            'collected_at': datetime.now().isoformat(),
            'reply_to_id': reply_to_id,
            'reply_url': reply_url,
            'is_reply': self.is_reply(text)
        }

    def is_reply(self, text):
        return text.strip().startswith('@') and not text.strip().lower().startswith('rt')

    def collect_all_replies(self):
        try:
            instance = self.find_working_instance()
        except Exception as e:
            print(e)
            return []

        all_replies = []
        for username in self.target_users:
            username = username.strip()
            if not username:
                continue
            print(f"📥 Collecting replies for @{username}")
            html = self.get_user_timeline(username, instance)
            replies = self.parse_timeline(html, username)
            all_replies.extend(replies)
            time.sleep(random.uniform(5, 10))

        # ✅ ここで「2週間以内」のみにフィルタ
        cutoff = datetime.now() - timedelta(days=14)
        recent_replies = [
            r for r in all_replies
            if r.get("timestamp") and self._within_range(r["timestamp"], cutoff)
        ]
        print(f"📦 {len(recent_replies)} replies kept (within 2 weeks)")
        return recent_replies

    def _within_range(self, timestamp_str, cutoff_dt):
        try:
            ts = datetime.fromisoformat(timestamp_str)
            return ts >= cutoff_dt
        except:
            return False

    def save_replies(self, new_replies):
        if not new_replies:
            print("No new replies to save.")
            return

        try:
            with open('replies.json', 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except FileNotFoundError:
            existing = []

        existing_keys = {f"{r['username']}-{r['text'][:50]}" for r in existing}
        uniques = []
        for r in new_replies:
            key = f"{r['username']}-{r['text'][:50]}"
            if key not in existing_keys:
                uniques.append(r)
                existing_keys.add(key)

        if uniques:
            combined = sorted(existing + uniques, key=lambda x: x['collected_at'], reverse=True)[:1000]
            with open('replies.json', 'w', encoding='utf-8') as f:
                json.dump(combined, f, ensure_ascii=False, indent=2)
            print(f"💾 Saved {len(uniques)} new replies. Total: {len(combined)}")
        else:
            print("No new unique replies found.")

def main():
    print(f"▶️ Start: {datetime.now().isoformat()}")
    collector = NitterRepliesCollector()
    try:
        replies = collector.collect_all_replies()
        collector.save_replies(replies)
        print("✅ Done.")
    except Exception as e:
        print(f"❌ Failed: {e}")
        raise

if __name__ == "__main__":
    main()
