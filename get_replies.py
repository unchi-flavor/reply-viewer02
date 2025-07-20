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
    print(f"[INFO] アクセスURL: {search_url}")
    page.goto(search_url)
    time.sleep(5)

    # デバッグ: ページ内容を保存してみる
    with open(f"debug_{username}.html", "w", encoding="utf-8") as f:
        f.write(page.content())
    print(f"[INFO] debug_{username}.html にHTMLを保存しました")

    # スクロールしてできるだけ多く取得する
    for i in range(3):
        page.keyboard.press("PageDown")
        time.sleep(1)
        print(f"[DEBUG] PageDown {i+1}回目")

    soup = BeautifulSoup(page.content(), "html.parser")
    articles = soup.find_all("article")
    print(f"[INFO] 見つかったarticleタグ数: {len(articles)}")

    for idx, article in enumerate(articles):
        text_elem = article.find("div", attrs={"data-testid": "tweetText"})
        if not text_elem:
            continue
        text = text_elem.text.strip()
        print(f"[DEBUG] {idx+1}件目リプ本文: {text[:60]}...")

        # ユーザー名（表示名とID）取得
        user_block = article.find("div", attrs={"data-testid": "User-Name"})
        if user_block:
            username_reply = user_block.get_text(strip=True)
        else:
            username_reply = "unknown"
        print(f"[DEBUG] {idx+1}件目リプユーザー: {username_reply}")

        # ツイートリンク
        tweet_link = article.find("a", href=True)
        tweet_url = "https://twitter.com" + tweet_link["href"] if tweet_link else ""
        print(f"[DEBUG] {idx+1}件目ツイートURL: {tweet_url}")

        # 投稿時刻を取得
        time_elem = article.find("time")
        if time_elem and time_elem.has_attr("datetime"):
            tweet_time = time_elem["datetime"]
        else:
            tweet_time = datetime.now().isoformat()
        print(f"[DEBUG] {idx+1}件目投稿時刻: {tweet_time}")

        now = datetime.now().isoformat()
        replies.append({
            "username": username_reply,
            "text": text,
            "timestamp": tweet_time,
            "reply_url": tweet_url,
            "reply_to_id": "",
            "collected_at": now,
            "original_text": f"@{username} 宛ての投稿"
        })

        if len(replies) >= MAX_REPLIES:
            print(f"[INFO] MAX_REPLIES({MAX_REPLIES})に到達したのでbreak")
            break

    print(f"[INFO] ユーザー「{username}」についてリプ収集完了: {len(replies)}件")
    return replies

def _within_range(timestamp_str, cutoff_dt):
    try:
        parsed = parser.parse(timestamp_str)
        result = parsed >= cutoff_dt
        print(f"[DEBUG] フィルタ判定: {timestamp_str} >= {cutoff_dt} → {result}")
        return result
    except Exception as e:
        print(f"[ERROR] 日付パース失敗: {timestamp_str} ({e})")
        return False

def save_replies(new_replies):
    try:
        with open('replies.json', 'r', encoding='utf-8') as f:
            existing = json.load(f)
    except Exception:
        existing = []
        print("[WARN] replies.jsonが存在しないか読み込み失敗、空リストで継続")

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
            print(f"[INFO] ユーザー「{username.strip()}」のリプ収集開始")
            replies = get_mentions_for_user(page, username.strip())
            all_replies.extend(replies)
        browser.close()

    cutoff = datetime.now() - timedelta(days=DAYS_LIMIT)
    print(f"[INFO] {DAYS_LIMIT}日前の {cutoff} 以降のみフィルタ")
    filtered = [r for r in all_replies if _within_range(r['timestamp'], cutoff)]
    print(f"[INFO] フィルタ後の件数: {len(filtered)}")
    save_replies(filtered)
    print("✅ Done.")

if __name__ == "__main__":
    main()
