"""Central settings for the Service Insights Agent.

Secrets (API keys) are NOT stored here. They come from environment
variables, which GitHub Codespaces fills from your Codespaces secrets.
"""
import os

# Where product and sales data come from:
#   "mock"    -> data/shop.json (works without Shopify)
#   "shopify" -> your Shopify dev store via the Admin API
DATA_SOURCE = os.environ.get("DATA_SOURCE", "mock")

# SQLite database file that stores all results
DB_PATH = os.environ.get("DB_PATH", "insights.db")

# Models: a small, cheap model for many tickets, a stronger one for analysis
CLASSIFY_MODEL = os.environ.get("CLASSIFY_MODEL", "claude-haiku-5-5")
ANALYZE_MODEL = os.environ.get("ANALYZE_MODEL", "claude-sonnet-5-5")

# USD per million tokens (input, output) for prompts under 100k tokens.
# Check these against Anthropic's pricing page before you report costs.
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
}

# Ticket topics the classifier may use
TOPICS = ["Passform", "Qualität", "Lieferung", "Farbe/Material", "Sonstiges"]

# A product/topic pair becomes a finding when BOTH thresholds are met
MIN_TICKETS = int(os.environ.get("MIN_TICKETS", "5"))
MIN_TICKETS_PER_100_SOLD = float(os.environ.get("MIN_TICKETS_PER_100_SOLD", "2.0"))

# Shopify Admin API version. Check shopify.dev for the current stable version.
SHOPIFY_API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2026-07")


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Cost of a call in US dollars, based on PRICES."""
    price_in, price_out = PRICES.get(model, (0.0, 0.0))
    return input_tokens / 1_000_000 * price_in + output_tokens / 1_000_000 * price_out
