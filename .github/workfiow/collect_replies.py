name: Auto Collect Replies

on:
  schedule:
    - cron: '0 0,3,6,9,12,15 * * *'  # JSTで9時, 12時, 15時, 18時, 21時, 0時
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.11

      - name: Install dependencies
        run: pip install requests beautifulsoup4 python-dotenv

      - name: Run reply collector
        run: |
          python get_replies.py
          python generate_html.py

      - name: Commit and push updated index.html
        run: |
          git config --global user.name "github-actions"
          git config --global user.email "github-actions@github.com"
          git add replies.json index.html
          git commit -m "🤖 Auto update replies [skip ci]" || echo "No changes to commit"
          git push
