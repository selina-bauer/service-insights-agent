"""One place to get product and sales data, from Shopify or from data/shop.json.

The rest of the code only uses the functions in this file, so switching
DATA_SOURCE between "mock" and "shopify" needs no other changes.
"""
import json
import re

from config import DATA_SOURCE

MOCK_PATH = "data/shop.json"


def _load_mock() -> dict:
    with open(MOCK_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_mock(data: dict) -> None:
    with open(MOCK_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def html_to_text(html: str) -> str:
    """Rough HTML-to-text conversion, good enough for prompts."""
    text = re.sub(r"<(br|/p|/li|/tr|/h\d)[^>]*>", "\n", html)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def list_products() -> list[dict]:
    """All products as {"id", "title", "description_html"}."""
    if DATA_SOURCE == "shopify":
        import shopify_client
        return shopify_client.list_products()
    return _load_mock()["products"]


def product_titles() -> list[str]:
    return [p["title"] for p in list_products()]


def get_product(title: str) -> dict | None:
    """Find a product by title (case-insensitive)."""
    for p in list_products():
        if p["title"].lower() == title.lower().strip():
            return p
    return None


def sales_by_product() -> dict[str, int]:
    if DATA_SOURCE == "shopify":
        import shopify_client
        try:
            return shopify_client.sales_by_product()
        except RuntimeError as error:
            print(f"Shopify orders not available ({error}). Using sales from data/shop.json.")
    return _load_mock()["sales"]


def update_description(product: dict, description_html: str) -> None:
    """Write a new description to Shopify, or to data/shop.json in mock mode."""
    if DATA_SOURCE == "shopify":
        import shopify_client
        shopify_client.update_description(product["id"], description_html)
        return
    data = _load_mock()
    for p in data["products"]:
        if p["id"] == product["id"]:
            p["description_html"] = description_html
    _save_mock(data)
