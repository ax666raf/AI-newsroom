# Amani's English News Collector — Setup Guide
## AI Newsroom Project | Data Collection Module

---

## 📁 Files Overview

| File | What it does |
|------|-------------|
| `sources.py` | Config: all source URLs, API keys, keyword list |
| `rss_collector.py` | Collects from 8 RSS feeds using feedparser |
| `api_collector.py` | Collects from NewsAPI.org and The Guardian API |
| `scraper.py` | Extracts full article text using newspaper3k |
| `main_collector.py` | Runs everything in sequence — this is what you execute daily |

---

## 🖥️ Step 1 — Install Python

Download Python 3.10 or higher from:
👉 https://www.python.org/downloads/

During installation on Windows: ✅ check "Add Python to PATH"

Verify it works:
```
python --version
```

---

## 📦 Step 2 — Install Required Libraries

Open your terminal (or VS Code terminal) and run:

```bash
pip install feedparser newspaper3k requests
```

If `newspaper3k` gives errors, also run:
```bash
pip install lxml[html_clean]
pip install nltk
```

---

## 🔑 Step 3 — Get Your API Keys

### NewsAPI.org (Free)
1. Go to 👉 https://newsapi.org/register
2. Sign up with your email
3. After confirming email, go to your account dashboard
4. Copy your **API Key** (looks like: `a3f9b2c1d4e5f6...`)
5. Open `sources.py` and replace:
   ```python
   "api_key": "YOUR_NEWSAPI_KEY_HERE"
   ```
   with:
   ```python
   "api_key": "your_actual_key_here"
   ```

> Free plan gives you **100 requests/day** and articles from the last month. That's plenty for our pipeline.

---

### The Guardian API (Free)
1. Go to 👉 https://open-platform.theguardian.com/access/
2. Click **"Register for a developer key"**
3. Fill in the form (use your student email, project = "academic research")
4. They email you the key within a few minutes
5. Open `sources.py` and replace:
   ```python
   "api_key": "YOUR_GUARDIAN_KEY_HERE"
   ```
   with your actual key

> Free plan gives you **500 requests/day** and full article text. Very generous.

---

## ▶️ Step 4 — Run the Collector

```bash
cd amani/
python main_collector.py
```

This will:
1. Pull from all 8 RSS feeds
2. Query NewsAPI and The Guardian
3. Scrape full text for each article
4. Save results to `english_articles_YYYY-MM-DD.json`

---

## 📤 Step 5 — Output Format

Every article saved looks like this:

```json
{
  "headline": "Algeria signs new gas deal with Italy",
  "url": "https://www.aljazeera.com/...",
  "source_name": "Al Jazeera English",
  "published_at": "2026-03-04T05:30:00",
  "full_text": "Algeria's state energy company Sonatrach...",
  "language": "en",
  "collected_by": "rss"
}
```

This format matches what **Achraf** needs for deduplication and database storage.

---

## 🔍 How the Algeria Filter Works

After collecting, every article is checked:
- Does the **title** contain "Algeria", "Algerian", "Algiers", "Oran", etc.?
- OR does the **body** contain any of those words?

If neither → the article is **discarded**. This is important for global sources like Al Jazeera or BBC that cover the whole world.

---

## ⚠️ Common Issues

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: feedparser` | Run `pip install feedparser` |
| `newspaper.article.ArticleException` | Normal — some sites block scrapers. Article keeps its RSS summary. |
| NewsAPI returns 0 results | Check your API key is correctly pasted in sources.py |
| RSS feed returns empty | Source might be temporarily down — check the URL in your browser |

---

## 🤝 Handoff to Teammates

- **Wanis** handles French RSS + Apify fallback for English sources that block scraping
- **Achraf** receives the JSON output and runs deduplication + database storage
- Your output file `english_articles_YYYY-MM-DD.json` is the bridge between your work and Achraf's

---

*Last updated: March 2026 — AI Newsroom Group Project*
