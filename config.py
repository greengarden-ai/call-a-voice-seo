"""
Central configuration for callavoice.com SEO research.
All domain targets, API settings, and output paths live here.
"""

import os

# --- Target ---
TARGET_DOMAIN = "callavoice.com"
TARGET_COUNTRY = "US"
TARGET_LANGUAGE = "en"
TARGET_LOCATION_CODE = 2840  # United States

# --- DataForSEO API ---
DATAFORSEO_LOGIN = os.environ["DATAFORSEO_LOGIN"]
DATAFORSEO_PASSWORD = os.environ["DATAFORSEO_PASSWORD"]
DATAFORSEO_BASE_URL = "https://api.dataforseo.com/v3"

# --- Competitor discovery ---
COMPETITOR_LIMIT = 20          # max competitors to return
COMPETITOR_MIN_INTERSECTIONS = 1  # shared keyword threshold

# --- Keyword analysis ---
KEYWORD_SEED_TERMS = [
    "ai voice agent",
    "voice ai",
    "call automation",
    "ai phone agent",
    "automated calling",
    "ai call center",
    "voice bot",
]
KEYWORD_LIMIT = 200            # max keywords per seed
KEYWORD_MIN_VOLUME = 100       # monthly search volume floor
KEYWORD_MAX_DIFFICULTY = 80    # KD ceiling (0-100)

# --- Backlink analysis ---
BACKLINK_LIMIT = 500           # max backlinks to pull
BACKLINK_MIN_RANK = 0          # domain rank floor (0 = all)

# --- Outputs ---
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
