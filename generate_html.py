# generate_html.py
import json
from datetime import datetime
import os

def load_replies_data():
    """リプライデータを読み込み"""
    try:
        with open('replies.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def load_grouped_data():
    """グループ化データを読み込み"""
    try:
        with open('replies_grouped.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def generate_stats(replies):
    """統計情報を生成"""
    if not replies:
        return {
            'total_replies': 0,
            'total_users': 0,
            'last_updated': 'Never',
            'users_stats': {}
        }
    
    users_stats = {}
    for reply in replies:
        username = reply.get('username', 'unknown')
        if username not in users_stats:
            users_stats[username] = {
                'count': 0,
                'latest': None
            }
        users_stats[username]['count'] += 1
        if not users_stats[username]['latest'] or reply.get('collected_at', '') > users_stats[username]['latest']:
            users_stats[username]['latest'] = reply.get('collected_at', '')
    
    return {
        'total_replies': len(replies),
        'total_users': len(users_stats),
        'last_updated': max([r.get('collected_at', '') for r in replies] + ['']),
        'users_stats': users_stats
    }

def format_timestamp(timestamp_str):
    """タイムスタンプを読みやすい形式に変換"""
    try:
        if timestamp_str:
            dt = datetime.fromisoformat(timestamp_str)
            return dt.strftime('%Y-%m-%d %H:%M')
        return 'Unknown'
    except:
        return str(timestamp_str) if timestamp_str else 'Unknown'

def escape_html(text):
    """HTMLエスケープ"""
    if not text:
        return ''
    return (text.replace('&', '&amp;')
               .replace('<', '&lt;')
               .replace('>', '&gt;')
               .replace('"', '&quot;')
               .replace("'", '&#x27;'))

def truncate_text(text, max_length=200):
    """テキストを指定長で切り詰め"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + '...'

def generate_index_html():
    """メインページのHTML生成"""
    replies = load_replies_data()
    grouped_data = load_grouped_data()
    stats = generate_stats(replies)
    
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Twitter Replies Monitor</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1da1f2, #0d8bd9);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #1da1f2;
            margin-bottom: 5px;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .content {{
            padding: 30px;
        }}
        .reply-item {{
            background: #fafafa;
            border-left: 4px solid #1da1f2;
            margin-bottom: 20px;
            padding: 20px;
            border-radius: 0 8px 8px 0;
            transition: all 0.3s ease;
        }}
        .reply-item:hover {{
            background: #f0f8ff;
            transform: translateX(5px);
        }}
        .reply-user {{
            font-weight: bold;
            color: #1da1f2;
            margin-bottom: 10px;
            font-size: 1.1em;
        }}
        .reply-text {{
            font-size: 1.05em;
            margin-bottom: 15px;
            word-wrap: break-word;
        }}
        .reply-meta {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.9em;
            color: #666;
        }}
        .reply-stats {{
            display: flex;
            gap: 15px;
        }}
        .reply-stat {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .filter-section {{
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .filter-section h3 {{
            margin-top: 0;
        }}
        .filter-controls {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }}
        select, input {{
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }}
        .last-updated {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-style: italic;
            background: #f8f9fa;
        }}
        .no-data {{
            text-align: center;
            padding: 50px;
            color: #666;
            font-size: 1.2em;
        }}
        @media (max-width: 768px) {{
            body {{ padding: 10px; }}
            .stats {{ grid-template-columns: 1fr 1fr; gap: 15px; padding: 20px; }}
            .content {{ padding: 20px; }}
            .reply-meta {{ flex-direction: column; align-items: flex-start; gap: 10px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐦 Twitter Replies Monitor</h1>
            <p>リアルタイムでTwitterのリプライを監視・収集</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{stats['total_replies']}</div>
                <div class="stat-label">総リプライ数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['total_users']}</div>
                <div class="stat-label">監視ユーザー数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(grouped_data)}</div>
                <div class="stat-label">収集時間帯数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{'自動更新' if stats['last_updated'] else 'N/A'}</div>
                <div class="stat-label">更新状況</div>
            </div>
        </div>
        
        <div class="content">"""

    if not replies:
        html_content += """
            <div class="no-data">
                <h3>📭 データがありません</h3>
                <p>まだリプライが収集されていません。しばらくお待ちください。</p>
            </div>"""
    else:
        html_content += f"""
            <div class="filter-section">
                <h3>📊 収集されたリプライ一覧</h3>
                <div class="filter-controls">
                    <select id="userFilter">
                        <option value="">すべてのユーザー</option>"""
        
        # ユーザー選択オプション
        for username in stats['users_stats'].keys():
            count = stats['users_stats'][username]['count']
            html_content += f'<option value="{escape_html(username)}">@{escape_html(username)} ({count}件)</option>'
        
        html_content += """
                    </select>
                    <input type="text" id="textFilter" placeholder="テキストで検索...">
                </div>
            </div>
            
            <div id="repliesList">"""
        
        # リプライ一覧表示
        for i, reply in enumerate(replies[:100]):  # 最新100件
            username = escape_html(reply.get('username', 'unknown'))
            text = escape_html(truncate_text(reply.get('text', '')))
            timestamp = format_timestamp(reply.get('timestamp'))
            collected_at = format_timestamp(reply.get('collected_at'))
            stats_data = reply.get('stats', {})
            
            html_content += f"""
                <div class="reply-item" data-user="{username}">
                    <div class="reply-user">@{username}</div>
                    <div class="reply-text">{text}</div>
                    <div class="reply-meta">
                        <div class="reply-stats">
                            <span class="reply-stat">💬 {stats_data.get('replies', 0)}</span>
                            <span class="reply-stat">🔄 {stats_data.get('retweets', 0)}</span>
                            <span class="reply-stat">❤️ {stats_data.get('likes', 0)}</span>
                        </div>
                        <div>
                            <div>投稿: {timestamp}</div>
                            <div>収集: {collected_at}</div>
                        </div>
                    </div>
                </div>"""
        
        html_content += "</div>"

    html_content += f"""
        </div>
        
        <div class="last-updated">
            最終更新: {format_timestamp(stats['last_updated'])} | 
            次回更新: 約3時間後 | 
            <a href="https://github.com/{os.getenv('GITHUB_REPOSITORY', 'your-repo')}" target="_blank">GitHub</a>
        </div>
    </div>
    
    <script>
        // フィルタリング機能
        document.getElementById('userFilter').addEventListener('change', filterReplies);
        document.getElementById('textFilter').addEventListener('input', filterReplies);
        
        function filterReplies() {{
            const userFilter = document.getElementById('userFilter').value.toLowerCase();
            const textFilter = document.getElementById('textFilter').value.toLowerCase();
            const replyItems = document.querySelectorAll('.reply-item');
            
            replyItems.forEach(item => {{
                const username = item.dataset.user.toLowerCase();
                const text = item.querySelector('.reply-text').textContent.toLowerCase();
                
                const userMatch = !userFilter || username.includes(userFilter);
                const textMatch = !textFilter || text.includes(textFilter);
                
                if (userMatch && textMatch) {{
                    item.style.display = 'block';
                }} else {{
                    item.style.display = 'none';
                }}
            }});
        }}
        
        // 自動リロード（30分間隔）
        setTimeout(() => {{
            location.reload();
        }}, 30 * 60 * 1000);
    </script>
</body>
</html>"""
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("Generated index.html successfully!")

def main():
    generate_index_html()

if __name__ == "__main__":
    main()
