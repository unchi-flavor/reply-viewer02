# get_replies.py - nitter版に更新
import requests
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
import os

class NitterRepliesCollector:
    def __init__(self):
        # 複数のnitterインスタンスを用意（冗長性確保）
        self.nitter_instances = [
            "https://nitter.poast.org",
            "https://nitter.privacydev.net", 
            "https://nitter.net",
            "https://n.opnxng.com",
            "https://nitter.it"
        ]
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ja;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 設定（環境変数 or デフォルト値）
        self.target_users = os.getenv('TARGET_USERS', 'elonmusk').split(',')
        self.max_tweets_per_user = int(os.getenv('MAX_TWEETS', '50'))
        
    def find_working_instance(self):
        """動作するnitterインスタンスを見つける"""
        for instance in self.nitter_instances:
            try:
                # テスト用の軽いリクエスト
                test_url = f"{instance}/search?f=tweets&q=test"
                response = requests.get(test_url, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    print(f"Using nitter instance: {instance}")
                    return instance
                    
            except requests.RequestException as e:
                print(f"Failed to connect to {instance}: {e}")
                continue
                
        raise Exception("No working nitter instances available")
    
    def get_user_timeline(self, username, instance):
        """ユーザーのタイムラインを取得"""
        url = f"{instance}/{username}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return response.text
            
        except requests.RequestException as e:
            print(f"Error fetching timeline for {username}: {e}")
            return None
    
    def parse_timeline(self, html_content, username):
        """HTMLからツイート情報を抽出"""
        if not html_content:
            return []
            
        soup = BeautifulSoup(html_content, 'html.parser')
        tweets = []
        
        # nitterのツイート構造を解析
        tweet_containers = soup.find_all('div', class_='timeline-item')
        
        for container in tweet_containers[:self.max_tweets_per_user]:
            try:
                tweet_data = self.extract_tweet_data(container, username)
                if tweet_data and self.is_reply(tweet_data['text']):
                    tweets.append(tweet_data)
                    
            except Exception as e:
                print(f"Error parsing tweet: {e}")
                continue
                
        return tweets
    
    def extract_tweet_data(self, container, username):
        """個別のツイートデータを抽出"""
        try:
            # ツイート本文
            tweet_text_elem = container.find('div', class_='tweet-content')
            if not tweet_text_elem:
                return None
                
            text_elem = tweet_text_elem.find('div', class_='tweet-text')
            if not text_elem:
                return None
                
            text = text_elem.get_text(strip=True)
            
            # 時間情報
            date_elem = container.find('span', class_='tweet-date')
            timestamp = None
            if date_elem:
                timestamp = date_elem.get('title', date_elem.get_text(strip=True))
            
            # 統計情報
            stats = self.extract_tweet_stats(container)
            
            # ツイートID（可能であれば）
            tweet_link = container.find('a', class_='tweet-link')
            tweet_id = None
            if tweet_link:
                href = tweet_link.get('href', '')
                tweet_id_match = re.search(r'/status/(\d+)', href)
                if tweet_id_match:
                    tweet_id = tweet_id_match.group(1)
            
            return {
                'id': tweet_id,
                'username': username,
                'text': text,
                'timestamp': timestamp,
                'stats': stats,
                'collected_at': datetime.now().isoformat(),
                'is_reply': self.is_reply(text)
            }
            
        except Exception as e:
            print(f"Error extracting tweet data: {e}")
            return None
    
    def extract_tweet_stats(self, container):
        """ツイートの統計情報を抽出"""
        stats = {
            'replies': 0,
            'retweets': 0, 
            'likes': 0,
            'quotes': 0
        }
        
        try:
            # nitterの統計表示要素を探す
            stats_container = container.find('div', class_='tweet-stats')
            if stats_container:
                for icon_container in stats_container.find_all('div', class_='icon-container'):
                    text = icon_container.get_text(strip=True)
                    number = self.extract_number_from_text(text)
                    
                    # アイコンクラスから種別を判定
                    if 'comment' in str(icon_container) or 'reply' in text.lower():
                        stats['replies'] = number
                    elif 'retweet' in str(icon_container) or 'retweet' in text.lower():
                        stats['retweets'] = number
                    elif 'heart' in str(icon_container) or 'like' in text.lower():
                        stats['likes'] = number
                    elif 'quote' in str(icon_container) or 'quote' in text.lower():
                        stats['quotes'] = number
                        
        except Exception as e:
            print(f"Error extracting stats: {e}")
            
        return stats
    
    def extract_number_from_text(self, text):
        """テキストから数値を抽出（K, M対応）"""
        if not text:
            return 0
            
        # K, M等の単位を数値に変換
        text = text.upper().strip()
        multiplier = 1
        
        if 'K' in text:
            multiplier = 1000
            text = text.replace('K', '')
        elif 'M' in text:
            multiplier = 1000000
            text = text.replace('M', '')
            
        # 数値部分を抽出
        numbers = re.findall(r'[\d.]+', text)
        if numbers:
            try:
                return int(float(numbers[0]) * multiplier)
            except:
                pass
                
        return 0
    
    def is_reply(self, text):
        """テキストがリプライかどうか判定"""
        if not text:
            return False
            
        # @で始まるツイートをリプライとして判定
        return text.strip().startswith('@')
    
    def collect_all_replies(self):
        """全ユーザーのリプライを収集"""
        try:
            working_instance = self.find_working_instance()
        except Exception as e:
            print(f"No working nitter instances: {e}")
            return []
            
        all_replies = []
        
        for username in self.target_users:
            username = username.strip()
            if not username:
                continue
                
            print(f"Collecting replies from @{username}...")
            
            try:
                # タイムライン取得
                timeline_html = self.get_user_timeline(username, working_instance)
                
                # パース
                user_replies = self.parse_timeline(timeline_html, username)
                
                print(f"Found {len(user_replies)} replies from @{username}")
                all_replies.extend(user_replies)
                
                # レート制限対策
                time.sleep(random.uniform(5, 10))
                
            except Exception as e:
                print(f"Error collecting from @{username}: {e}")
                continue
                
        return all_replies
    
    def save_replies(self, new_replies):
        """リプライデータを保存"""
        if not new_replies:
            print("No new replies to save")
            return
            
        # 既存データを読み込み
        try:
            with open('replies.json', 'r', encoding='utf-8') as f:
                existing_replies = json.load(f)
        except FileNotFoundError:
            existing_replies = []
            
        # 重複除去（テキスト + ユーザー名で判定）
        existing_keys = {f"{r['username']}-{r['text'][:50]}" for r in existing_replies}
        unique_new_replies = []
        
        for reply in new_replies:
            key = f"{reply['username']}-{reply['text'][:50]}"
            if key not in existing_keys:
                unique_new_replies.append(reply)
                existing_keys.add(key)
        
        if unique_new_replies:
            # 新しいリプライを追加
            all_replies = existing_replies + unique_new_replies
            
            # 時間順でソート（新しいものが先頭）
            all_replies.sort(key=lambda x: x.get('collected_at', ''), reverse=True)
            
            # 最新1000件まで保持
            all_replies = all_replies[:1000]
            
            # 保存
            with open('replies.json', 'w', encoding='utf-8') as f:
                json.dump(all_replies, f, ensure_ascii=False, indent=2)
            
            # グループ化データも更新
            self.update_grouped_data(all_replies)
            
            print(f"Saved {len(unique_new_replies)} new replies")
            print(f"Total replies in database: {len(all_replies)}")
            
        else:
            print("No new unique replies found")
    
    def update_grouped_data(self, replies):
        """時間別グループ化データを更新"""
        from collections import defaultdict
        
        grouped = defaultdict(list)
        
        for reply in replies:
            try:
                # collected_atから日時を取得
                dt = datetime.fromisoformat(reply['collected_at'])
                # 1時間単位でグループ化
                hour_key = dt.strftime('%Y-%m-%d %H:00')
                grouped[hour_key].append(reply)
            except:
                # パースエラーの場合は"unknown"グループ
                grouped['unknown'].append(reply)
        
        # 時間順でソート
        sorted_grouped = dict(sorted(grouped.items(), reverse=True))
        
        with open('replies_grouped.json', 'w', encoding='utf-8') as f:
            json.dump(sorted_grouped, f, ensure_ascii=False, indent=2)

def main():
    print("Starting Twitter replies collection...")
    print(f"Target time: {datetime.now().isoformat()}")
    
    collector = NitterRepliesCollector()
    
    try:
        # リプライ収集
        new_replies = collector.collect_all_replies()
        
        # データ保存
        collector.save_replies(new_replies)
        
        print("Collection completed successfully!")
        
    except Exception as e:
        print(f"Collection failed: {e}")
        # GitHub Actionsでエラーを確認できるよう例外を再発生
        raise

if __name__ == "__main__":
    main()
