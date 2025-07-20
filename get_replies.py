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
MAX_REPLIES = int(os.getenv("MAX_REPLIES", "100"))
DAYS_LIMIT = int(os.getenv("DAYS_LIMIT", "7"))

def get_mentions_for_user(page, username):
    replies = []
    search_url = f"https://twitter.com/search?q=to%3A{username}&f=live"
    page.goto(search_url)
    time.sleep(5)
    soup = BeautifulSoup(page.content(), "html.parser")
    articles = soup.find_all("article")

    for article in articles:
        text_elem = article.find("div", attrs={"data-testid": "tweetText"})
        if not text_elem:
            continue
        text = text_elem.text.strip()

        # ユーザー名（表示名とID）取得
        user_block = article.find("div", attrs={"data-testid": "User-Name"})
        if user_block:
            username_reply = user_block.get_text(strip=True)
        else:
            username_reply = "unknown"

        # ツイートリンク
        tweet_link = article.find("a", href=True)
        tweet_url = "https://twitter.com" + tweet_link["href"] if tweet_link else ""

        now = datetime.now().isoformat()
        replies.append({
            "username": username_reply,
            "text": text,
            "timestamp": now,
            "reply_url": tweet_url,
            "reply_to_id": "",  # 現時点では不明
            "collected_at": now,
            "original_text": f"@{username} 宛ての投稿"
        })

        if len(replies) >= MAX_REPLIES:
            break

    return replies

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
            replies = get_mentions_for_user(page, username.strip())
            all_replies.extend(replies)
        browser.close()

    cutoff = datetime.now() - timedelta(days=DAYS_LIMIT)
    filtered = [r for r in all_replies if _within_range(r['timestamp'], cutoff)]
    save_replies(filtered)
    print("✅ Done.")

if __name__ == "__main__":
    main()
