import os
import requests
import json
from collections import defaultdict

# あなたのBearer Tokenをここに貼ってね（" " の中に！）
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
if not BEARER_TOKEN:
    raise ValueError("❌ BEARER_TOKEN が環境変数に設定されていません")

def create_headers():
    return {
        "Authorization": f"Bearer {BEARER_TOKEN}"
    }

# ここにWebhookのURLを貼ってね（Discordで取得したやつ）
WEBHOOK_URL = "https://discord.com/api/webhooks/1394287381909078187/hwY1mL89rhtqxcKATOQWcLP9Xd6mrMhWfZmm13lgArvrtcUFNvDeCKVBiKLYwO7EypbO"

def send_discord_message(content):
    data = {
        "content": content
    }
    response = requests.post(WEBHOOK_URL, json=data)
    if response.status_code == 204:
        print("✅ 通知を送信しました")
    else:
        print("❌ 通知に失敗しました:", response.status_code, response.text)

def get_tweet_by_id(tweet_id, cache):
    if tweet_id in cache:
        return cache[tweet_id]

    url = f"https://api.twitter.com/2/tweets/{tweet_id}"
    params = {"tweet.fields": "text"}
    response = requests.get(url, headers=create_headers(), params=params)

    # デバッグ用
    print("元ツイ取得中:", tweet_id)
    print("ステータスコード:", response.status_code)
    print("レスポンス内容:", response.text)

    if response.status_code == 200:
        data = response.json().get("data", {})
        cache[tweet_id] = data
        return data
    else:
        cache[tweet_id] = {"text": "(元ツイート取得失敗)", "id": tweet_id}
        return cache[tweet_id]

def search_recent_replies(username, max_pages=5):
    url = "https://api.twitter.com/2/tweets/search/recent"
    query = f"to:{username} -is:retweet"
    headers = create_headers()
    next_token = None
    grouped = defaultdict(lambda: {"original_text": "", "original_id": "", "replies": []})
    original_cache = {}

    for _ in range(max_pages):
        params = {
            "query": query,
            "tweet.fields": "author_id,created_at,referenced_tweets",
            "max_results": 100
        }
        if next_token:
            params["next_token"] = next_token

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print("Error:", response.status_code)
            print(response.text)
            break

        tweets = response.json().get("data", [])
        for tweet in tweets:
            referenced = tweet.get("referenced_tweets", [])
            original_id = next((ref["id"] for ref in referenced if ref["type"] == "replied_to"), None)
            if not original_id:
                continue

            original = get_tweet_by_id(original_id, original_cache)
            group = grouped[original_id]
            group["original_text"] = original.get("text", "(取得できません)")
            group["original_id"] = original_id
            group["replies"].append({
                "reply_text": tweet["text"],
                "reply_time": tweet["created_at"],
                "reply_user": tweet["author_id"],
                "reply_id": tweet["id"]
            })
            
            message = f"新しいリプがあるよん：\n{tweet['text']}\nhttps://x.com/i/web/status/{tweet['id']}"
            send_discord_message(message)

        next_token = response.json().get("meta", {}).get("next_token")
        if not next_token:
            break  # もう次がなければ終了

    grouped_list = list(grouped.values())
    with open("replies_grouped.json", "w", encoding="utf-8") as f:
        json.dump(grouped_list, f, ensure_ascii=False, indent=2)
    print("✅ replies_grouped.json に保存しました（元ツイートごとにグループ化）")

# 実行テスト
search_recent_replies("UKIUKI_step", max_pages=5)
