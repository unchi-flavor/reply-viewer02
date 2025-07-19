name: Collect Replies at Specific Times

on:
  schedule:
    - cron: '0 21,0,3,6,9,12 * * *'  # JST: 6, 9, 12, 15, 18, 21時
  workflow_dispatch:

jobs:
  run-script:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.11

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          # or: pip install requests beautifulsoup4 python-dotenv

      - name: Run get_replies.py
        run: python get_replies.py
        env:
          TARGET_USERS: ${{ secrets.TARGET_USERS }}
          MAX_TWEETS: 50

      - name: Generate index.html
        run: python generate_html.py

      - name: Commit and push updated files
        run: |
          git config --global user.name 'github-actions'
          git config --global user.email 'github-actions@github.com'
          git add replies.json replies_grouped.json index.html
          git commit -m "Update replies and index.html [skip ci]" || echo "No changes to commit"
          git push
