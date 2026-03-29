"""
Backlink Analysis
=================
Two-phase backlink research for callavoice.com:

  Phase 1 — Summary: high-level backlink profile metrics.
    Endpoint: backlinks/summary/live

  Phase 2 — Full backlink list: all discovered backlinks up to BACKLINK_LIMIT.
    Endpoint: backlinks/backlinks/live

Outputs:
  outputs/backlinks_summary_<date>.json
  outputs/backlinks_<date>.csv / .json
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

BACKLINKS_CSV_HEADERS = [
    "url_from",
    "domain_from",
    "url_to",
    "anchor",
    "dofollow",
    "domain_from_rank",
    "page_from_rank",
    "first_seen",
    "last_seen",
    "link_type",
    "broken",
]


# ---------------------------------------------------------------------------
# Phase 1: summary
# ---------------------------------------------------------------------------

def fetch_summary(client: DataForSEOClient) -> dict:
    logger.info("Fetching backlink summary for %s …", config.TARGET_DOMAIN)

    task = {
        "target": config.TARGET_DOMAIN,
        "include_subdomains": True,
    }

    results = client.post("backlinks/summary/live", [task])
    summary = results[0] if results else {}
    logger.info(
        "Summary: backlinks=%s, referring_domains=%s, rank=%s",
        summary.get("backlinks"),
        summary.get("referring_domains"),
        summary.get("rank"),
    )
    return summary


# ---------------------------------------------------------------------------
# Phase 2: full backlink list
# ---------------------------------------------------------------------------

def fetch_backlinks(client: DataForSEOClient) -> list[dict]:
    logger.info(
        "Fetching up to %d backlinks for %s …",
        config.BACKLINK_LIMIT,
        config.TARGET_DOMAIN,
    )

    base_task = {
        "target": config.TARGET_DOMAIN,
        "mode": "as_is",
        "include_subdomains": True,
        "include_indirect_links": True,
        "filters": [
            ["dofollow", "=", True]
        ],
        "order_by": ["domain_from_rank,desc"],
    }

    items = client.paginated_post(
        endpoint="backlinks/backlinks/live",
        base_task=base_task,
        total_limit=config.BACKLINK_LIMIT,
        page_size=100,
    )

    logger.info("Backlinks fetched: %d", len(items))
    return items


def flatten_backlink(item: dict) -> dict:
    return {
        "url_from": item.get("url_from", ""),
        "domain_from": item.get("domain_from", ""),
        "url_to": item.get("url_to", ""),
        "anchor": item.get("anchor", ""),
        "dofollow": item.get("dofollow", ""),
        "domain_from_rank": item.get("domain_from_rank", ""),
        "page_from_rank": item.get("page_from_rank", ""),
        "first_seen": item.get("first_seen", ""),
        "last_seen": item.get("last_seen", ""),
        "link_type": item.get("type", ""),
        "broken": item.get("broken", ""),
    }


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def save_summary(summary: dict, run_date: str) -> None:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    path = os.path.join(config.OUTPUT_DIR, f"backlinks_summary_{run_date}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    logger.info("Summary saved → %s", path)


def save_backlinks(items: list[dict], run_date: str) -> None:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    csv_path = os.path.join(config.OUTPUT_DIR, f"backlinks_{run_date}.csv")
    json_path = os.path.join(config.OUTPUT_DIR, f"backlinks_{run_date}.json")

    flat = [flatten_backlink(i) for i in items]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=BACKLINKS_CSV_HEADERS)
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

    summary = fetch_summary(client)
    save_summary(summary, run_date)

    items = fetch_backlinks(client)
    if items:
        save_backlinks(items, run_date)
    else:
        logger.warning("No backlinks returned — domain may be too new or have no links yet")

    logger.info("Done. backlinks=%d", len(items))


if __name__ == "__main__":
    main()
