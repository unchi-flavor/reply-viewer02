import json
from datetime import datetime, timedelta, timezone
import os
from collections import defaultdict

def load_replies():
    try:
        with open("replies.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

JST = timezone(timedelta(hours=9))

def format_timestamp(ts_str):
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(JST)
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return ts_str or "不明"

def escape_html(text):
    if not text:
        return ""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#x27;"))

def group_by_tweet(replies):
    grouped = defaultdict(list)
    for r in replies:
        key = r.get("reply_url") or "unknown"
        grouped[key].append(r)
    return grouped

def generate_html():
    replies = load_replies()
    grouped = group_by_tweet(replies)

    html = [
        "<!DOCTYPE html>",
        "<html lang='ja'>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<title>リプライ一覧</title>",
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        "<style>",
        "body { font-family: sans-serif; background: #f5f5f5; padding: 20px; }",
        ".group { background: white; padding: 20px; margin-bottom: 30px; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }",
        ".group .original { font-size: 0.9em; color: #666; margin-bottom: 10px; }",
        ".reply { border-left: 4px solid #1da1f2; padding: 10px 15px; margin-bottom: 10px; background: #fefefe; border-radius: 4px; }",
        ".reply-text { margin-bottom: 5px; }",
        ".meta { font-size: 0.85em; color: #666; }",
        ".meta a { color: #1da1f2; text-decoration: none; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>📬 最近のリプライ（2週間以内）</h1>"
    ]

    if not replies:
        html.append("<p>リプライデータが見つかりません。</p>")
    else:
        for tweet_url, reply_list in grouped.items():
            html.append("<div class='group'>")

            # 一番古いリプを元ツイートと仮定
            base = reply_list[-1]
            base_text = escape_html(base.get("text", "（元ツイート不明）"))
            html.append(f"<div class='original'>🧵 元ツイート: {base_text}</div>")

            for reply in reply_list:
                if reply == base:
                    continue
                username = escape_html(reply.get("username", "unknown"))
                text = escape_html(reply.get("text", ""))
                time_str = format_timestamp(reply.get("timestamp"))
                link = reply.get("reply_url", "#")

                html.append("<div class='reply'>")
                html.append(f"<div class='reply-text'>{text}</div>")
                html.append(f"<div class='meta'>by @{username} / {time_str} / <a href='{link}' target='_blank'>🔗 リプ元へ</a></div>")
                html.append("</div>")

            html.append("</div>")  # group end

    html.append("<p style='text-align:center;color:#888;font-size:0.9em;'>最終更新: " + format_timestamp(datetime.now(timezone.utc).isoformat()) + "</p>")
    html.append("</body></html>")

    with open("index.html", "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    print("✅ index.html を生成しました。")

def main():
    generate_html()

if __name__ == "__main__":
    main()
