name: Collect Replies at Specific Times

on:
  schedule:
    - cron: '0 21,0,3,6,9,12 * * *'  # JSTの6,9,12,15,18時に対応（UTCベース）
  workflow_dispatch:  # 手動実行も可能に

jobs:
  run-script:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.11

      - name: Install dependencies
        run: pip install requests

      - name: Run get_replies.py
        run: python get_replies.py
        env:
          BEARER_TOKEN: ${{ secrets.BEARER_TOKEN }}

      - name: Commit and push replies_grouped.json
        run: |
          git config --global user.name 'github-actions'
          git config --global user.email 'github-actions@github.com'
          git add replies_grouped.json
          git commit -m "Update replies_grouped.json"
          git push
        env:
          # GitHubトークンでpush許可
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
