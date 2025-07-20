import json
import os
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dateutil import parser
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

TARGET_USERS = os.getenv("TARGET_USERS", "elonmusk").split(",")
MAX_TWEETS = int(os.getenv("MAX_TWEETS", "10"))

def get_replies_from_tweet(page, tweet_url, username):
    replies = []
    page.goto(tweet_url)
    time.sleep(5)
    soup = BeautifulSoup(page.content(), "html.parser")
    items = soup.find_all("article")

    if not items:
        print("⚠️ No tweet content found.")
        return replies

    # 先頭の記事を元ツイートと仮定
    first_item = items[0]
    original_text_elem = first_item.find("div", attrs={"data-testid": "tweetText"})
    original_text = original_text_elem.text.strip() if original_text_elem else "[元ツイート取得失敗]"

    # 残りはリプライと仮定
    for item in items[1:]:
        user_elem = item.find("a", href=True)
        text_elem = item.find("div", attrs={"data-testid": "tweetText"})
        if user_elem and text_elem:
            timestamp = datetime.now().isoformat()
            replies.append({
                "username": user_elem.text.strip(),
                "text": text_elem.text.strip(),
                "timestamp": timestamp,
                "reply_to_id": tweet_url.split("/")[-1],
                "reply_url": tweet_url,
                "collected_at": timestamp,
                "original_text": original_text
            })
    return replies

def get_tweet_urls(page, username):
    page.goto(f"https://twitter.com/{username}")
    time.sleep(5)
    soup = BeautifulSoup(page.content(), "html.parser")
    links = soup.find_all("a", href=True)
    tweets = [f"https://twitter.com{a['href']}" for a in links if "/status/" in a['href']]
    return list(dict.fromkeys(tweets))[:MAX_TWEETS]

def _within_range(timestamp_str, cutoff_dt):
    try:
        parsed = parser.parse(timestamp_str)
        return parsed >= cutoff_dt
    except:
        return False

def save_replies(new_replies):
    try:
        with open('replies.json', 'r', encoding='utf-8') as f:
            existing = json.load(f)
    except:
        existing = []

    existing_keys = {r['text'][:100] for r in existing}
    uniques = [r for r in new_replies if r['text'][:100] not in existing_keys]

    combined = sorted(existing + uniques, key=lambda x: x['collected_at'], reverse=True)[:1000]
    with open('replies.json', 'w', encoding='utf-8') as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    print(f"💾 Saved {len(uniques)} new replies. Total: {len(combined)}")

def main():
    print(f"▶️ Start: {datetime.now().isoformat()}")
    all_replies = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for username in TARGET_USERS:
            tweets = get_tweet_urls(page, username.strip())
            for url in tweets:
                print(f"🔍 {url}")
                replies = get_replies_from_tweet(page, url, username)
                all_replies.extend(replies)
        browser.close()

    cutoff = datetime.now() - timedelta(days=14)
    filtered = [r for r in all_replies if _within_range(r['timestamp'], cutoff)]
    save_replies(filtered)
    print("✅ Done.")

if __name__ == "__main__":
    main()
