"""
Competitor Discovery
====================
Finds domains that compete with callavoice.com in Google organic search,
ranked by the number of shared ranking keywords.

DataForSEO endpoint used:
  dataforseo_labs/google/competitors_domain/live

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

# Make repo root importable when run as a script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from utils.dataforseo_client import DataForSEOClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Fields to keep from each competitor item
FIELDS = [
    "domain",
    "avg_position",
    "sum_position",
    "intersections",
    "full_domain_metrics",
]

CSV_HEADERS = [
    "domain",
    "avg_position",
    "sum_position",
    "intersections",
    "organic_etv",
    "organic_count",
    "organic_keywords_count",
]


def fetch_competitors(client: DataForSEOClient) -> list[dict]:
    logger.info("Fetching competitors for %s …", config.TARGET_DOMAIN)

    task = {
        "target": config.TARGET_DOMAIN,
        "location_code": config.TARGET_LOCATION_CODE,
        "language_code": config.TARGET_LANGUAGE,
        "filters": [
            ["intersections", ">", config.COMPETITOR_MIN_INTERSECTIONS]
        ],
        "order_by": ["intersections,desc"],
        "limit": config.COMPETITOR_LIMIT,
    }

    results = client.post("dataforseo_labs/google/competitors_domain/live", [task])
    items = DataForSEOClient._extract_items(results)
    logger.info("Received %d competitor entries", len(items))
    return items


def flatten_item(item: dict) -> dict:
    """Flatten nested full_domain_metrics into a single dict for CSV."""
    metrics = item.get("full_domain_metrics") or {}
    organic = metrics.get("organic") or {}
    return {
        "domain": item.get("domain", ""),
        "avg_position": item.get("avg_position", ""),
        "sum_position": item.get("sum_position", ""),
        "intersections": item.get("intersections", ""),
        "organic_etv": organic.get("etv", ""),
        "organic_count": organic.get("count", ""),
        "organic_keywords_count": organic.get("keywords_count", ""),
    }


def save_outputs(items: list[dict], run_date: str) -> None:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    csv_path = os.path.join(config.OUTPUT_DIR, f"competitors_{run_date}.csv")
    json_path = os.path.join(config.OUTPUT_DIR, f"competitors_{run_date}.json")

    # CSV
    flat = [flatten_item(i) for i in items]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(flat)
    logger.info("CSV saved → %s", csv_path)

    # JSON (full raw items for downstream use)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)
    logger.info("JSON saved → %s", json_path)


def main() -> None:
    run_date = date.today().isoformat()
    client = DataForSEOClient()

    items = fetch_competitors(client)

    if not items:
        logger.warning("No competitors returned — check domain / thresholds in config.py")
        sys.exit(0)

    save_outputs(items, run_date)
    logger.info("Done. %d competitors written for %s", len(items), run_date)


if __name__ == "__main__":
    main()
