# callavoice.com SEO Research

Automated SEO intelligence for [callavoice.com](https://callavoice.com) using the [DataForSEO API](https://dataforseo.com).

## What it does

| Script | Endpoint | Schedule | Outputs |
|---|---|---|---|
| `competitor_discovery.py` | `dataforseo_labs/google/competitors_domain/live` | Mon 06:00 UTC | `competitors_<date>.csv/.json` |
| `keyword_analysis.py` | `ranked_keywords/live` + `keyword_ideas/live` | Mon 07:00 UTC | `keywords_ranked_<date>.csv/.json`, `keywords_ideas_<date>.csv/.json` |
| `backlink_analysis.py` | `backlinks/summary/live` + `backlinks/backlinks/live` | Mon 08:00 UTC | `backlinks_summary_<date>.json`, `backlinks_<date>.csv/.json` |

All outputs are committed back to `outputs/` by the workflow bot after each run.

## Setup

### 1. Add GitHub Secrets

In your repo: Settings → Secrets and variables → Actions:

| Secret | Value |
|---|---|
| `DATAFORSEO_LOGIN` | Your DataForSEO account email |
| `DATAFORSEO_PASSWORD` | Your DataForSEO API password |

### 2. Push to GitHub

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/<you>/seo-cav.git
git push -u origin main
```

### 3. Run manually (optional)

Trigger any workflow from the Actions tab using **workflow_dispatch**, or run locally:

```bash
export DATAFORSEO_LOGIN=your@email.com
export DATAFORSEO_PASSWORD=yourpassword
python scripts/competitor_discovery.py
python scripts/keyword_analysis.py
python scripts/backlink_analysis.py
```

## Configuration

All tunable settings are in [config.py](config.py):

- `COMPETITOR_LIMIT` / `COMPETITOR_MIN_INTERSECTIONS` — competitor discovery depth
- `KEYWORD_SEED_TERMS` — seed keywords for idea expansion
- `KEYWORD_MIN_VOLUME` / `KEYWORD_MAX_DIFFICULTY` — filters
- `BACKLINK_LIMIT` — max backlinks to pull per run

## Project structure

```
.
├── .github/workflows/
│   ├── competitor_discovery.yml
│   ├── keyword_analysis.yml
│   └── backlink_analysis.yml
├── scripts/
│   ├── competitor_discovery.py
│   ├── keyword_analysis.py
│   └── backlink_analysis.py
├── utils/
│   └── dataforseo_client.py   # shared HTTP client
├── outputs/                   # CSV + JSON results (committed by CI)
├── config.py                  # all settings
└── requirements.txt
```
