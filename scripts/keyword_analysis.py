"""
Keyword Analysis
================
Two-phase keyword research:

  Phase 1 — Ranking keywords: what callavoice.com already ranks for.
    Endpoint: dataforseo_labs/google/ranked_keywords/live

  Phase 2 — Keyword ideas: expansion from seed terms in config.py.
    Endpoint: dataforseo_labs/google/keyword_ideas/live

Results are deduplicated, filtered by volume + difficulty, and saved.

Outputs:
  outputs/keywords_ranked_<date>.csv / .json
  outputs/keywords_ideas_<date>.csv  / .json
"""

import csv
import json
import logging
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from utils.dataforseo_client import DataForSEOClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

RANKED_CSV_HEADERS = [
    "keyword",
    "search_volume",
    "keyword_difficulty",
    "cpc",
    "competition",
    "rank_absolute",
    "rank_group",
    "url",
]

IDEAS_CSV_HEADERS = [
    "keyword",
    "search_volume",
    "keyword_difficulty",
    "cpc",
    "competition",
    "monthly_searches_avg",
]


# ---------------------------------------------------------------------------
# Phase 1: ranked keywords
# ---------------------------------------------------------------------------

def fetch_ranked_keywords(client: DataForSEOClient) -> list[dict]:
    logger.info("Fetching ranked keywords for %s …", config.TARGET_DOMAIN)

    task = {
        "target": config.TARGET_DOMAIN,
        "location_code": config.TARGET_LOCATION_CODE,
        "language_code": config.TARGET_LANGUAGE,
        "filters": [
            ["keyword_data.keyword_info.search_volume", ">", config.KEYWORD_MIN_VOLUME - 1]
        ],
        "order_by": ["keyword_data.keyword_info.search_volume,desc"],
        "limit": config.KEYWORD_LIMIT,
    }

    results = client.post("dataforseo_labs/google/ranked_keywords/live", [task])
    items = DataForSEOClient._extract_items(results)
    logger.info("Ranked keywords: %d items", len(items))
    return items


def flatten_ranked(item: dict) -> dict:
    kw_data = item.get("keyword_data") or {}
    kw_info = kw_data.get("keyword_info") or {}
    ranked_serp = item.get("ranked_serp_element") or {}
    serp_item = ranked_serp.get("serp_item") or {}

    return {
        "keyword": kw_data.get("keyword", ""),
        "search_volume": kw_info.get("search_volume", ""),
        "keyword_difficulty": kw_data.get("keyword_properties", {}).get("keyword_difficulty", ""),
        "cpc": kw_info.get("cpc", ""),
        "competition": kw_info.get("competition", ""),
        "rank_absolute": serp_item.get("rank_absolute", ""),
        "rank_group": serp_item.get("rank_group", ""),
        "url": serp_item.get("url", ""),
    }


# ---------------------------------------------------------------------------
# Phase 2: keyword ideas from seeds
# ---------------------------------------------------------------------------

def fetch_keyword_ideas(client: DataForSEOClient) -> list[dict]:
    logger.info("Fetching keyword ideas for %d seed terms …", len(config.KEYWORD_SEED_TERMS))

    all_items: list[dict] = []
    seen: set[str] = set()

    for seed in config.KEYWORD_SEED_TERMS:
        logger.info("  seed: %s", seed)
        task = {
            "keywords": [seed],
            "location_code": config.TARGET_LOCATION_CODE,
            "language_code": config.TARGET_LANGUAGE,
            "filters": [
                ["keyword_info.search_volume", ">", config.KEYWORD_MIN_VOLUME - 1],
                "and",
                ["keyword_properties.keyword_difficulty", "<", config.KEYWORD_MAX_DIFFICULTY + 1],
            ],
            "order_by": ["keyword_info.search_volume,desc"],
            "limit": config.KEYWORD_LIMIT,
        }

        try:
            results = client.post("dataforseo_labs/google/keyword_ideas/live", [task])
            items = DataForSEOClient._extract_items(results)
        except Exception as exc:
            logger.warning("Seed '%s' failed: %s", seed, exc)
            continue

        for item in items:
            kw = item.get("keyword", "")
            if kw and kw not in seen:
                seen.add(kw)
                all_items.append(item)

    logger.info("Keyword ideas (deduplicated): %d", len(all_items))
    return all_items


def flatten_idea(item: dict) -> dict:
    kw_info = item.get("keyword_info") or {}
    kw_props = item.get("keyword_properties") or {}
    monthly = kw_info.get("monthly_searches") or []
    avg_volume = (
        sum(m.get("search_volume", 0) for m in monthly) // len(monthly)
        if monthly else ""
    )

    return {
        "keyword": item.get("keyword", ""),
        "search_volume": kw_info.get("search_volume", ""),
        "keyword_difficulty": kw_props.get("keyword_difficulty", ""),
        "cpc": kw_info.get("cpc", ""),
        "competition": kw_info.get("competition", ""),
        "monthly_searches_avg": avg_volume,
    }


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def save_csv_json(
    items: list[dict],
    flat_fn,
    headers: list[str],
    base_name: str,
    run_date: str,
) -> None:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    csv_path = os.path.join(config.OUTPUT_DIR, f"{base_name}_{run_date}.csv")
    json_path = os.path.join(config.OUTPUT_DIR, f"{base_name}_{run_date}.json")

    flat = [flat_fn(i) for i in items]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(flat)
    logger.info("CSV saved → %s", csv_path)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)
    logger.info("JSON saved → %s", json_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    run_date = date.today().isoformat()
    client = DataForSEOClient()

    # Phase 1
    ranked = fetch_ranked_keywords(client)
    if ranked:
        save_csv_json(ranked, flatten_ranked, RANKED_CSV_HEADERS, "keywords_ranked", run_date)
    else:
        logger.warning("No ranked keywords found for %s", config.TARGET_DOMAIN)

    # Phase 2
    ideas = fetch_keyword_ideas(client)
    if ideas:
        save_csv_json(ideas, flatten_idea, IDEAS_CSV_HEADERS, "keywords_ideas", run_date)
    else:
        logger.warning("No keyword ideas returned")

    logger.info("Done. ranked=%d, ideas=%d", len(ranked), len(ideas))


if __name__ == "__main__":
    main()
