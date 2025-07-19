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
            'Accept': 'text/html',
            'Accept-Language': 'en-US,en;q=0.9,ja;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self.target_users = os.getenv('TARGET_USERS', 'elonmusk').split(',')
        self.max_tweets_per_user = int(os.getenv('MAX_TWEETS', '50'))

    def find_working_instance(self):
        for instance in self.nitter_instances:
            try:
                test_url = f"{instance}/search?f=tweets&q=test"
                response = requests.get(test_url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    print(f"Using nitter instance: {instance}")
                    return instance
            except requests.RequestException as e:
                print(f"Failed to connect to {instance}: {e}")
        raise Exception("No working nitter instances available")

    def get_user_timeline(self, username, instance):
        try:
            url = f"{instance}/{username}"
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching timeline for {username}: {e}")
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
                print(f"Tweet parse error: {e}")
                print(f"Problematic container: {container}")
        return replies

    def extract_tweet_data(self, container, username):
        text_elem = container.find('div', class_='tweet-content')
        if not text_elem:
            raise ValueError("No tweet content")

        inner = text_elem.find('div', class_='tweet-text')
        if not inner:
            raise ValueError("No tweet-text")
        text = inner.get_text(strip=True)

        date_elem = container.find('span', class_='tweet-date')
        timestamp = date_elem.get('title') if date_elem else None

        tweet_link = container.find('a', class_='tweet-link')
        tweet_id = None
        if tweet_link:
            match = re.search(r'/status/(\d+)', tweet_link.get('href', ''))
            if match:
                tweet_id = match.group(1)

        # fallback id if missing
        if not tweet_id:
            tweet_id = f"{text[:20]}_{timestamp}"

        return {
            'id': tweet_id,
            'username': username,
            'text': text,
            'timestamp': timestamp,
            'stats': self.extract_tweet_stats(container),
            'collected_at': datetime.now().isoformat(),
            'is_reply': self.is_reply(text)
        }

    def extract_tweet_stats(self, container):
        stats = {'replies': 0, 'retweets': 0, 'likes': 0, 'quotes': 0}
        try:
            statbox = container.find('div', class_='tweet-stats')
            if statbox:
                for icon in statbox.find_all('div', class_='icon-container'):
                    text = icon.get_text(strip=True)
                    val = self.extract_number_from_text(text)
                    html = str(icon)
                    if 'comment' in html:
                        stats['replies'] = val
                    elif 'retweet' in html:
                        stats['retweets'] = val
                    elif 'heart' in html:
                        stats['likes'] = val
                    elif 'quote' in html:
                        stats['quotes'] = val
        except Exception as e:
            print(f"Stats extract error: {e}")
        return stats

    def extract_number_from_text(self, text):
        text = text.upper().strip()
        multiplier = 1
        if 'K' in text:
            multiplier = 1000
            text = text.replace('K', '')
        elif 'M' in text:
            multiplier = 1000000
            text = text.replace('M', '')
        numbers = re.findall(r'[\d.]+', text)
        return int(float(numbers[0]) * multiplier) if numbers else 0

    def is_reply(self, text):
        if not text:
            return False
        return text.strip().startswith('@') and not text.strip().startswith('RT')

    def collect_all_replies(self):
        try:
            instance = self.find_working_instance()
        except Exception as e:
            print(f"No instance available: {e}")
            return []
        all_replies = []
        for username in self.target_users:
            username = username.strip()
            if not username:
                continue
            print(f"Collecting replies for @{username}")
            html = self.get_user_timeline(username, instance)
            replies = self.parse_timeline(html, username)
            print(f"→ {len(replies)} replies")
            all_replies.extend(replies)
            time.sleep(random.uniform(5, 10))
        return all_replies

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
            self.update_grouped_data(combined)
            print(f"Saved {len(uniques)} new replies. Total: {len(combined)}")
        else:
            print("No new unique replies found.")

    def update_grouped_data(self, replies):
        from collections import defaultdict
        grouped = defaultdict(list)
        for r in replies:
            try:
                dt = datetime.fromisoformat(r['collected_at'])
                key = dt.strftime('%Y-%m-%d %H:00')
                grouped[key].append(r)
            except:
                grouped['unknown'].append(r)
        with open('replies_grouped.json', 'w', encoding='utf-8') as f:
            json.dump(dict(sorted(grouped.items(), reverse=True)), f, ensure_ascii=False, indent=2)

def main():
    print(f"Collecting started: {datetime.now().isoformat()}")
    collector = NitterRepliesCollector()
    try:
        replies = collector.collect_all_replies()
        collector.save_replies(replies)
        print("Done.")
    except Exception as e:
        print(f"Failed: {e}")
        raise

if __name__ == "__main__":
    main()
