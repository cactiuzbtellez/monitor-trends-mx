name: Fetch Tendencias MX

on:
  schedule:
    - cron: "0 * * * *"   # Cada hora
  workflow_dispatch:

jobs:
  fetch:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Instalar dependencias
        run: pip install feedparser

      - name: Ejecutar fetch
        run: python scripts/fetch_trends.py

      - name: Commit trends.json
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/trends.json
          git diff --cached --quiet || git commit -m "chore: tendencias $(date -u +'%Y-%m-%d %H:%M UTC')"
          git push
