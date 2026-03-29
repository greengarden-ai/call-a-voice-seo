"""
Competitor Discovery
====================
Finds domains competing in Google organic search for callavoice.com's
target keyword space.

Strategy:
  1. Try domain-based: competitors_domain/live (works once callavoice.com
     has organic rankings).
  2. Fall back to keyword-based: serp_competitors/live using seed terms
     from config.KEYWORD_SEED_TERMS. Works even for brand-new domains.

Results are deduplicated and ranked by avg_position.

Outputs:
  outputs/competitors_<date>.csv
  outputs/competitors_<date>.json
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

CSV_HEADERS = [
    "domain",
    "avg_position",
    "median_position",
    "rating",
    "etv",
    "keywords_count",
    "source",
]


# ---------------------------------------------------------------------------
# Strategy 1: domain-based (requires callavoice.com to have rankings)
# ---------------------------------------------------------------------------

def fetch_domain_competitors(client: DataForSEOClient) -> list[dict]:
    logger.info("Trying domain-based competitor lookup for %s …", config.TARGET_DOMAIN)

    task = {
        "target": config.TARGET_DOMAIN,
        "location_code": config.TARGET_LOCATION_CODE,
        "language_code": config.TARGET_LANGUAGE,
        "filters": [
            ["intersections", ">=", config.COMPETITOR_MIN_INTERSECTIONS]
        ],
        "order_by": ["intersections,desc"],
        "limit": config.COMPETITOR_LIMIT,
    }

    try:
        results = client.post("dataforseo_labs/google/competitors_domain/live", [task])
        items = DataForSEOClient._extract_items(results)
    except Exception as exc:
        logger.warning("Domain-based lookup failed: %s", exc)
        return []

    logger.info("Domain-based: %d competitors", len(items))
    return items


def flatten_domain_item(item: dict) -> dict:
    metrics = item.get("full_domain_metrics") or {}
    organic = metrics.get("organic") or {}
    return {
        "domain": item.get("domain", ""),
        "avg_position": item.get("avg_position", ""),
        "median_position": "",
        "rating": "",
        "etv": organic.get("etv", ""),
        "keywords_count": organic.get("keywords_count", ""),
        "source": "domain",
    }


# ---------------------------------------------------------------------------
# Strategy 2: keyword-based (works for any domain)
# ---------------------------------------------------------------------------

def fetch_keyword_competitors(client: DataForSEOClient) -> list[dict]:
    logger.info(
        "Trying keyword-based competitor lookup with %d seeds …",
        len(config.KEYWORD_SEED_TERMS),
    )

    # SERP competitors takes a list of keywords and returns domains that rank
    task = {
        "keywords": config.KEYWORD_SEED_TERMS,
        "location_code": config.TARGET_LOCATION_CODE,
        "language_code": config.TARGET_LANGUAGE,
        "order_by": ["avg_position,asc"],
        "limit": config.COMPETITOR_LIMIT,
    }

    try:
        results = client.post("dataforseo_labs/google/serp_competitors/live", [task])
        items = DataForSEOClient._extract_items(results)
    except Exception as exc:
        logger.warning("Keyword-based lookup failed: %s", exc)
        return []

    # Exclude target domain from its own competitor list
    items = [i for i in items if i.get("domain") != config.TARGET_DOMAIN]
    logger.info("Keyword-based: %d competitors", len(items))
    return items


def flatten_keyword_item(item: dict) -> dict:
    return {
        "domain": item.get("domain", ""),
        "avg_position": item.get("avg_position", ""),
        "median_position": item.get("median_position", ""),
        "rating": item.get("competitor_metrics", {}).get("organic", {}).get("etv", ""),
        "etv": item.get("competitor_metrics", {}).get("organic", {}).get("etv", ""),
        "keywords_count": item.get("keywords_count", ""),
        "source": "keywords",
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def save_outputs(flat_items: list[dict], raw_items: list[dict], run_date: str) -> None:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    csv_path = os.path.join(config.OUTPUT_DIR, f"competitors_{run_date}.csv")
    json_path = os.path.join(config.OUTPUT_DIR, f"competitors_{run_date}.json")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(flat_items)
    logger.info("CSV saved → %s", csv_path)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(raw_items, f, indent=2)
    logger.info("JSON saved → %s", json_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    run_date = date.today().isoformat()
    client = DataForSEOClient()

    # Try domain-based first
    items = fetch_domain_competitors(client)
    flatten_fn = flatten_domain_item

    # Fall back to keyword-based if empty
    if not items:
        logger.info("No domain-based results — falling back to keyword-based lookup")
        items = fetch_keyword_competitors(client)
        flatten_fn = flatten_keyword_item

    if not items:
        logger.warning("No competitors found via either method")
        sys.exit(0)

    flat = [flatten_fn(i) for i in items]
    save_outputs(flat, items, run_date)
    logger.info("Done. %d competitors written for %s", len(items), run_date)


if __name__ == "__main__":
    main()
