import requests
import re
import json

HTML_URL = "https://github.com/zedeus/nitter/wiki/Instances"
OUTPUT_FILE = "nitter_instances.json"

def fetch_instance_urls():
    print("🌐 Fetching instance list from HTML page...")
    res = requests.get(HTML_URL)
    if res.status_code != 200:
        raise Exception("Failed to fetch instance list")
    html = res.text
    urls = re.findall(r'https://[a-zA-Z0-9\.\-]*nitter[a-zA-Z0-9\.\-]*', html)
    return urls

def check_instance(url):
    try:
        res = requests.get(f"{url}/search?f=tweets&q=test", timeout=5)
        return res.status_code == 200
    except:
        return False

def main():
    raw_urls = fetch_instance_urls()
    print(f"🔍 Found {len(raw_urls)} URLs")

    working = []
    for url in raw_urls:
        print(f"🧪 Checking {url}")
        if check_instance(url):
            print(f"✅ OK: {url}")
            working.append(url)
        else:
            print(f"❌ NG: {url}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(working, f, indent=2, ensure_ascii=False)

    print(f"💾 Saved {len(working)} working instances to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
