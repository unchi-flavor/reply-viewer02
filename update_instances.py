import requests
import re

RAW_URL = "https://raw.githubusercontent.com/zedeus/nitter/wiki/Instances.md"
OUTPUT_FILE = "nitter_instances.json"

def fetch_instance_urls():
    print("🌐 Fetching instance list...")
    res = requests.get(RAW_URL)
    if res.status_code != 200:
        raise Exception("Failed to fetch instance list")
    markdown = res.text
    urls = re.findall(r"https://[a-zA-Z0-9\.\-]+", markdown)
    return urls

def check_instance(url):
    try:
        test_url = f"{url}/search?f=tweets&q=test"
        res = requests.get(test_url, timeout=5)
        return res.status_code == 200
    except:
        return False

def main():
    raw_urls = fetch_instance_urls()
    print(f"🔍 {len(raw_urls)} instances found")

    working = []
    for url in raw_urls:
        print(f"🧪 Checking {url}")
        if check_instance(url):
            print(f"✅ OK: {url}")
            working.append(url)
        else:
            print(f"❌ NG: {url}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        import json
        json.dump(working, f, indent=2, ensure_ascii=False)

    print(f"💾 Saved {len(working)} working instances to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
